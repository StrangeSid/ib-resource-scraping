"""Cloud catalog: read-only search over committed manifests, no sqlite.

Vercel serverless has no persistent disk, so the cloud API never touches
STORE/index.sqlite or blobs/. It loads manifests/*.json (committed, ~15M),
classifies in memory once per cold start (~1s for 53k rows), then serves
search/facets/stats/links/mirrors from that cache.

Local self-host keeps the sqlite+blobs path in api/main.py (CLOUD_MODE=0).
"""
import json
import os
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MDIR = Path(os.environ.get("MANIFESTS", ROOT / "manifests"))


def _load_json(name):
    p = MDIR / name
    if not p.exists():
        return []
    try:
        d = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return d if isinstance(d, list) else []


def _load_mirrors():
    p = MDIR / "mirrors.json"
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())["mirrors"]
    except (json.JSONDecodeError, KeyError, OSError):
        return []


@lru_cache(maxsize=1)
def records():
    """All searchable rows. Schema matches FTS output in api/main.py."""
    from ib_scrape.classify import classify
    from ib_scrape.index_fts import ts_of

    out = []

    # 31 local-file manifests -> kind=file (cloud has no bytes; download redirects)
    for r in _load_json("index.json"):
        sha = r.get("sha256", "")
        title = r.get("filename", "")
        url = r.get("url", "")
        c = classify(title, url, r.get("subject", ""))
        out.append({
            "kind": "file", "title": title, "url": url,
            "source": r.get("source", ""), "subject": r.get("subject", ""),
            "extra": sha, "ts": ts_of(url) or r.get("fetched_at", ""),
            "rtype": c["rtype"], "level": c["level"], "sess": c["session"],
            "yr": c["year"], "tz": c["tz"],
        })

    # remote catalogs -> kind=remote
    for name in sorted(p.name for p in MDIR.glob("*.json")):
        if name in ("index.json", "mirrors.json", "ibnotes_links.json"):
            continue
        if not (name.startswith(("ibdocs_", "xtreme_", "tfm_", "dufs_", "wp_"))):
            continue
        for r in _load_json(name):
            url = r.get("url", "")
            if not url:
                continue
            title = r.get("name", "") or url
            subj = " ".join(str(r.get(k, "")) for k in ("year", "session", "parent", "dirpath")).strip()
            c = classify(title, url, subj)
            ts = ts_of(url, str(r.get("year", "")), r.get("session", ""))
            out.append({
                "kind": "remote", "title": title, "url": url,
                "source": r.get("source", name.split("_")[0]),
                "subject": subj, "extra": "",
                "ts": ts,
                "rtype": c["rtype"], "level": c["level"],
                "sess": c["session"] or str(r.get("session", "")),
                "yr": c["year"] or str(r.get("year", "")),
                "tz": c["tz"],
            })

    # link graph -> kind=link
    for r in _load_json("ibnotes_links.json"):
        url = r.get("url", "")
        if not url:
            continue
        out.append({
            "kind": "link", "title": url, "url": url,
            "source": r.get("platform", ""), "subject": r.get("host", ""),
            "extra": "", "ts": "",
            "rtype": "other", "level": "", "sess": "", "yr": "", "tz": "",
        })

    for r in out:
        r["_hay"] = f"{r['title']} {r['url']} {r['source']} {r['subject']} {r['rtype']} {r['level']} {r['sess']} {r['yr']}".lower()
        r["_title"] = r["title"].lower()
    return out


def _tokens(q):
    return [t.lower() for t in re.findall(r"[A-Za-z0-9]+", q or "")]


def _filtered(q="", kind="", rtype="", level="", session="", year=""):
    toks = _tokens(q)
    rows = records()
    if kind:
        rows = [r for r in rows if r["kind"] == kind]
    if rtype:
        rows = [r for r in rows if r["rtype"] == rtype]
    if level:
        rows = [r for r in rows if r["level"] == level]
    if session:
        rows = [r for r in rows if session.lower() in r["sess"].lower()]
    if year:
        rows = [r for r in rows if year in r["yr"]]
    if toks:
        hit = []
        for r in rows:
            hay, title = r["_hay"], r["_title"]
            if all(t in hay for t in toks):
                score = sum(2 if t in title else 1 for t in toks)
                hit.append((score, r))
        rows = [r for _, r in sorted(hit, key=lambda x: -x[0])]
    return rows


def _public(r):
    return {k: r[k] for k in ("kind", "title", "url", "source", "subject",
                              "extra", "ts", "rtype", "level", "sess", "yr", "tz")}


def search(q, kind="", rtype="", level="", session="", year="",
           sort="rank", limit=20, offset=0):
    rows = _filtered(q, kind, rtype, level, session, year)
    if sort == "recent":
        rows = sorted(rows, key=lambda r: r["ts"], reverse=True)
    # rank order already scored; stable: recent ties broken by ts
    page = rows[offset:offset + limit]
    return [_public(r) for r in page]


def facets(q="", kind=""):
    rows = _filtered(q, kind)
    out = {}
    for col in ("rtype", "level", "sess", "yr", "tz", "kind"):
        counts = {}
        for r in rows:
            v = r[col]
            if v:
                counts[v] = counts.get(v, 0) + 1
        out[col] = [{"value": v, "count": n}
                    for v, n in sorted(counts.items(), key=lambda x: -x[1])[:25]]
    return out


def stats():
    recs = records()
    files = sum(1 for r in recs if r["kind"] == "file")
    remote = sum(1 for r in recs if r["kind"] == "remote")
    links = sum(1 for r in recs if r["kind"] == "link")
    by_src = {}
    for r in recs:
        if r["kind"] == "file":
            by_src[r["source"]] = by_src.get(r["source"], 0) + 1
    return {"files": files, "bytes": 0,
            "by_source": [{"source": k, "n": v} for k, v in sorted(by_src.items())],
            "remote_catalog": remote, "links": links,
            "indexed": len(recs)}


def recent(limit=20):
    recs = sorted(records(), key=lambda r: r["ts"], reverse=True)
    files = [r for r in recs if r["kind"] == "file"][:limit]
    return [{"sha256": r["extra"], "source": r["source"], "url": r["url"],
             "filename": r["title"], "size": 0, "fetched_at": r["ts"]}
            for r in files]


def links(q="", platform="", limit=20):
    rows = _load_json("ibnotes_links.json")
    out = [{"url": r["url"], "host": r.get("host", ""),
            "platform": r.get("platform", ""),
            "direct_file": r.get("direct_file", False)}
           for r in rows
           if q.lower() in r.get("url", "").lower()
           and platform.lower() in r.get("platform", "").lower()]
    return out[:limit]


def mirrors():
    return _load_mirrors()


def resource(sha):
    for r in _load_json("index.json"):
        if r.get("sha256") == sha:
            d = dict(r)
            d["local"] = False
            d["source_url"] = r.get("url", "")
            return d
    return None


def download_url(sha):
    r = resource(sha)
    return r["url"] if r else None


def clear_cache():
    records.cache_clear()
