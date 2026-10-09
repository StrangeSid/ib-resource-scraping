"""TinyFileManager (?p=) crawler. Needs clearance cookies for CF hosts.

Two ways in: --cookies (Netscape jar from manual solve) or --uc-harvest
(SeleniumBase UC headless auto-solve, proven vs repo.pirateib.sh).
Without valid cookies list() gets HTTP 403.
"""
import http.cookiejar as cj
import re
from urllib.parse import unquote_plus
import requests
from .. import config

ROW_RE = re.compile(r"<tr.*?</tr>", re.S)
HREF_RE = re.compile(r'<a href="(\?p=[^"]+)"[^>]*title="([^"]+)"')
TEXT_RE = re.compile(r"<a[^>]*>(.*?)</a>", re.S)
SIZE_RE = re.compile(r'data-order="b-(\d+)"')
DIRECT_RE = re.compile(r'title="Direct link" href="([^"]+)"')
TAG_RE = re.compile(r"<[^>]+>")


class TFMClient:
    def __init__(self, host, cookie_file=None, cookie_dict=None, session=None):
        self.host = host.rstrip("/")
        self.s = session
        if self.s is None:
            self.s = requests.Session()
            self.s.headers.update(config.UA)
        if cookie_dict:
            self.s.cookies.update(cookie_dict)
        if cookie_file:
            jar = cj.MozillaCookieJar(cookie_file)
            jar.load(ignore_discard=True, ignore_expires=True)
            self.s.cookies.update({c.name: c.value for c in jar})

    def list_full(self, path=""):
        """Row-level listing: [{name, path, is_dir, size, direct}]."""
        r = self.s.get(self.host + "/index.php", params={"p": path}, timeout=60)
        if r.status_code == 403:
            raise RuntimeError(f"403 on {self.host} — clearance cookies missing/expired")
        r.raise_for_status()
        out = []
        for row in ROW_RE.findall(r.text):
            if "?p=" not in row or "..</a>" in row:
                continue
            m = HREF_RE.search(row)
            if not m:
                continue
            href, title = m.groups()
            base = href.split("&")[0][3:]  # ?p=<path>, drop &view/&dl
            name = title.strip() or TAG_RE.sub("", TEXT_RE.search(row).group(1)).strip()
            size = SIZE_RE.search(row)
            dm = DIRECT_RE.search(row)
            out.append({"name": name, "path": unquote_plus(base),
                        "is_dir": "fa-folder" in row,
                        "size": int(size.group(1)) if size else 0,
                        "direct": dm.group(1) if dm else ""})
        return out

    def list(self, path=""):
        r = self.s.get(self.host + "/index.php", params={"p": path}, timeout=60)
        if r.status_code == 403:
            raise RuntimeError(f"403 on {self.host} — clearance cookies missing/expired")
        r.raise_for_status()
        # TFM addresses paths as ?p=<path> links + hidden <input name="p">
        subs = set(re.findall(r"[?&]p=([^\"'&]+)", r.text))
        subs.update(re.findall(r'name="p"\s+value="([^"]+)"', r.text))
        return sorted(subs)

    def download(self, remote_path, store, filename=None):
        r = self.s.get(self.host + "/" + remote_path.lstrip("/"), timeout=300)
        r.raise_for_status()
        name = filename or remote_path.rsplit("/", 1)[-1]
        return store.save(r.content, source="tfm:" + self.host,
                          url=self.host + "/" + remote_path, filename=name)

    def download_url(self, url, store, filename, subject=""):
        r = self.s.get(url, timeout=300)
        r.raise_for_status()
        return store.save(r.content, source="tfm:" + self.host,
                          url=url, filename=filename, subject=subject)

    def crawl(self, root="", store=None, max_pages=200, dl_limit=0, log=print):
        """BFS dirs; catalog everything; download files up to dl_limit."""
        seen, queue, recs = {root}, [root], []
        n_dl = 0
        while queue and len(seen) <= max_pages:
            path = queue.pop(0)
            try:
                rows = self.list_full(path)
            except Exception as e:
                log(f"skip {path}: {str(e)[:80]}")
                continue
            n_f = n_d = 0
            for row in rows:
                recs.append({"url": row["direct"] or self.host + "/index.php?p=" + row["path"],
                             "name": row["name"], "size": str(row["size"]),
                             "parent": path, "source": "tfm:" + self.host})
                if row["is_dir"]:
                    if row["path"] not in seen:
                        seen.add(row["path"])
                        queue.append(row["path"])
                    n_d += 1
                elif store is not None and n_dl < dl_limit and row["direct"]:
                    try:
                        self.download_url(row["direct"], store, row["name"])
                        n_dl += 1
                    except Exception as e:
                        log(f"skip dl {row['name']}: {str(e)[:80]}")
                    n_f += 1
            log(f"{path}: {n_d} dirs {n_f} files")
        return recs
