"""Dufs file-server connector (dl.pirateib.sh + siblings).

Dufs renders listings client-side but serves `?json` per directory:
{href, paths: [{path_type: Dir|File|..., name, mtime(ms), size}]}.
Needs cleared session (UC harvest + curl_cffi) on CF hosts.
"""
from urllib.parse import quote, urljoin

from .. import config


def _s(session):
    import requests
    s = session or requests.Session()
    if session is None:
        s.headers.update(config.UA)
    return s


def list_json(host, path, session):
    url = host.rstrip("/") + "/" + quote(path.strip("/")) if path.strip("/") else host.rstrip("/") + "/"
    r = session.get(url, params={"json": ""}, timeout=60)
    if r.status_code == 403:
        raise RuntimeError(f"403 on {host} — clearance missing/expired")
    r.raise_for_status()
    d = r.json()
    out = []
    for p in d.get("paths", []):
        ts = ""
        if p.get("mtime"):
            import time as _t
            ts = _t.strftime("%Y-%m-%d", _t.gmtime(p["mtime"] / 1000))
        out.append({"name": p["name"], "is_dir": p["path_type"].endswith("Dir"),
                    "size": p.get("size", 0), "ts": ts,
                    "url": urljoin(host.rstrip("/") + "/",
                                   quote((path.strip("/") + "/" + p["name"]).strip("/")))})
    return out


def crawl(host, root="", session=None, max_pages=500, store=None, dl_limit=0, log=print):
    s = _s(session)
    seen, queue, recs = {root}, [root], []
    n_dl = 0
    while queue and len(seen) <= max_pages:
        path = queue.pop(0)
        try:
            rows = list_json(host, path, s)
        except Exception as e:
            log(f"skip {path}: {str(e)[:80]}")
            continue
        n_f = n_d = 0
        for row in rows:
            sub = (path.strip("/") + "/" + row["name"]).strip("/")
            recs.append({"url": row["url"], "name": row["name"],
                         "size": str(row["size"]), "parent": path,
                         "ts": row.get("ts", ""),
                         "source": "dufs:" + host})
            if row["is_dir"]:
                if sub not in seen:
                    seen.add(sub)
                    queue.append(sub)
                n_d += 1
            elif store is not None and n_dl < dl_limit:
                try:
                    r = s.get(row["url"], timeout=300)
                    r.raise_for_status()
                    store.save(r.content, source="dufs:" + host, url=row["url"],
                               filename=row["name"])
                    n_dl += 1
                except Exception as e:
                    log(f"skip dl {row['name']}: {str(e)[:80]}")
                n_f += 1
        log(f"{path or '/'}: {n_d} dirs {n_f} files")
    return recs


def crawl_uc(host, root="", max_pages=500, log=print, manifest=None):
    """Catalog-only BFS inside a real UC browser.

    For hosts that RST curl_cffi (arrib.cc, dynamicrepo.sbs) but serve
    ?json to the solved browser. Record-only: no byte downloads.
    """
    import json as _json
    import time as _time
    from seleniumbase import SB
    recs = []
    with SB(uc=True, headless=True) as sb:
        sb.open(host.rstrip("/") + "/")
        sb.sleep(20)
        seen, queue = {root}, [root]
        while queue and len(seen) <= max_pages:
            path = queue.pop(0)
            url = host.rstrip("/") + ("/" + quote(path.strip("/"))
                                      if path.strip("/") else "/") + "?json"
            try:
                sb.open(url)
                sb.sleep(2)
                d, _ = _json.JSONDecoder().raw_decode(sb.get_text("body").strip())
            except Exception as e:
                log(f"skip {path}: {str(e)[:80]}")
                continue
            n_d = 0
            for p in d.get("paths", []):
                sub = (path.strip("/") + "/" + p["name"]).strip("/")
                is_dir = p["path_type"].endswith("Dir")
                ts = ""
                if p.get("mtime"):
                    ts = _time.strftime("%Y-%m-%d", _time.gmtime(p["mtime"] / 1000))
                recs.append({"url": host.rstrip("/") + "/" + quote(sub),
                             "name": p["name"], "size": str(p.get("size", 0)),
                             "parent": path, "ts": ts, "source": "dufs:" + host})
                if is_dir:
                    if sub not in seen:
                        seen.add(sub)
                        queue.append(sub)
                    n_d += 1
            log(f"{path or '/'}: {n_d} dirs")
            if manifest and len(seen) % 50 == 0:
                _json.dump(recs, open(manifest, "w"))
                log(f"flushed {len(recs)} to {manifest}")
    if manifest:
        _json.dump(recs, open(manifest, "w"))
    return recs
