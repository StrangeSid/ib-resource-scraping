"""Mirror discovery via ibresources.cc JSON API (v3, fallback v2)."""
import requests
from .. import config


def snapshot(session=None):
    s = session or requests.Session()
    s.headers.update(config.UA)
    for url in (config.MIRROR_API_V3, config.MIRROR_API_V2):
        r = s.get(url, timeout=30)
        if r.status_code == 200:
            data = r.json()
            data["_api"] = url
            return data
    raise RuntimeError("mirror API unreachable")
