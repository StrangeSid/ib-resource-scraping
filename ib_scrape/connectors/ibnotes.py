"""pirateib.sh/ibnotes link-graph: extract + classify outbound links.

Google Drive/Docs/Notion/Quizlet need per-platform handlers (stage 2);
direct file URLs (.pdf/.zip/...) download immediately."""
import re
from collections import Counter
from urllib.parse import urlparse

import requests
from .. import config

PLATFORM = [("google_docs", "docs.google.com"), ("google_drive", "drive.google.com"),
            ("quizlet", "quizlet.com"), ("youtube", "youtube.com"),
            ("youtube_short", "youtu.be"), ("notion", "notion.site"),
            ("spotify", "open.spotify.com"), ("ibo", "ibpublishing.ibo.org"),
            ("pirateib_repo", "repo.pirateib.sh"), ("dl", "dl.pirateib.sh")]
FILE_RE = re.compile(r"\.(pdf|zip|rar|7z|docx?|pptx?|xlsx?|mp3|mp4)(\?|#|$)", re.I)


def extract(session=None):
    s = session or requests.Session()
    s.headers.update(config.UA)
    html = s.get(config.IBNOTES_URL, timeout=30).text
    hrefs = re.findall(r'href="([^"#]+)"', html)
    ext = [h for h in hrefs if h.startswith("http")]
    out = []
    for h in ext:
        host = urlparse(h).netloc
        plat = next((n for n, d in PLATFORM if d in host), "other")
        out.append({"url": h, "host": host, "platform": plat,
                    "direct_file": bool(FILE_RE.search(h))})
    return out


def census(links):
    c = Counter((l["platform"], l["direct_file"]) for l in links)
    return [{"platform": p, "direct_file": d, "count": n} for (p, d), n in c.most_common()]
