"""ibdocs.re catalog crawler (IB Docs 3 Team, no challenge, SSR HTML).

Routes: /past-papers/{year}/{session}[/{group}...]. Folder rows are
<a class="file-row" href="/IB PAST PAPERS - YEAR/...">; file rows carry
a size. Record-only by default; download only with explicit limit.
"""
import re
from urllib.parse import unquote, urljoin

import requests
from .. import config

BASE = "https://ibdocs.re"
ROW_RE = re.compile(
    r'<a href="([^"]+)" class="file-row">.*?title="([^"]+)".*?'
    r'<span class="file-size">([^<]*)</span>', re.S)


def list_page(url, session=None):
    s = session or requests.Session()
    s.headers.update(config.UA)
    html = s.get(url, timeout=30).text
    out = []
    for href, title, size in ROW_RE.findall(html):
        out.append({"url": urljoin(BASE, href), "name": unquote(title),
                   "size": size.strip(), "is_dir": size.strip() == "-"})
    return out


def crawl_session(year, session_slug, session=None, max_pages=200):
    """Breadth-first over one session subtree, e.g. (2025, may-2025)."""
    s = session or requests.Session()
    seen, queue = set(), [f"{BASE}/past-papers/{year}/{session_slug}"]
    recs = []
    while queue and len(seen) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        for row in list_page(url, s):
            rec = {**row, "year": year, "session": session_slug,
                   "parent": url, "source": "ibdocs"}
            recs.append(rec)
            if row["is_dir"]:
                queue.append(row["url"])
    return recs
