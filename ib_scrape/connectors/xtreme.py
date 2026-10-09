"""papers.xtremepape.rs (fdscript browser, no challenge).

Folders: index.php?dirpath=./IB/...&order=N
Files: direct relative hrefs IB/.../*.pdf (papers + markschemes, TZ/HL/SL).
Server-side search: index.php?dirpath=...&search=term
"""
import re
from urllib.parse import unquote, unquote_plus, urljoin

import requests
from .. import config

BASE = "https://papers.xtremepape.rs/"
DIR_RE = re.compile(r'href="(index\.php\?dirpath=([^"&]+)[^"]*)"[^>]*>\[?([^<\]]+)')
FILE_RE = re.compile(r'href="((?:IB|CAIE|Edexcel)/[^"]+\.(?:pdf|zip|rar|mp3|mp4))"', re.I)


def _s(session=None):
    s = session or requests.Session()
    if not session:
        s.headers.update(config.BROWSER)
    return s


def list_dir(dirpath, session=None):
    s = _s(session)
    r = s.get(BASE + "index.php",
              params={"dirpath": unquote_plus(dirpath), "order": 0},
              timeout=30)
    r.raise_for_status()
    html = r.text
    dirs = [{"url": urljoin(BASE, h.replace("&amp;", "&")),
             "dirpath": unquote(dp), "name": unquote(name.strip("[]"))}
            for h, dp, name in DIR_RE.findall(html)]
    files = [{"url": urljoin(BASE, unquote(h)), "name": h.rsplit("/", 1)[-1]}
             for h in FILE_RE.findall(html)]
    return dirs, files


def search(dirpath, term, session=None):
    s = _s(session)
    r = s.get(BASE + "index.php",
              params={"dirpath": dirpath, "search": term}, timeout=30)
    r.raise_for_status()
    return [{"url": urljoin(BASE, unquote(h)), "name": h.rsplit("/", 1)[-1]}
            for h in FILE_RE.findall(r.text)]


def crawl(root="./IB/", session=None, max_pages=500, log=print):
    s = _s(session)
    seen, queue, recs = set(), [unquote_plus(root)], []
    while queue and len(seen) < max_pages:
        dp = queue.pop(0)
        norm = unquote_plus(dp)
        if norm in seen:
            continue
        seen.add(norm)
        try:
            dirs, files = list_dir(dp, s)
        except Exception as e:
            log(f"skip {dp}: {str(e)[:80]}")
            continue
        for f in files:
            recs.append({**f, "dirpath": dp, "source": "xtreme"})
        for d in dirs:
            if unquote_plus(d["dirpath"]).startswith(unquote_plus(root)):
                queue.append(unquote_plus(d["dirpath"]))
        log(f"{dp}: {len(dirs)} dirs {len(files)} files")
    return recs


def download(file_url, store, session=None):
    s = _s(session)
    r = s.get(file_url, timeout=300)
    r.raise_for_status()
    name = unquote(file_url.rsplit("/", 1)[-1])
    return store.save(r.content, source="xtreme", url=file_url, filename=name)
