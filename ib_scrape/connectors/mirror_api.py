"""Mirror discovery via ibresources.cc JSON API (v3, fallback v2)."""
import time

import requests
from .. import config


def snapshot(session=None, retries=3):
    s = session or requests.Session()
    s.headers.update(config.UA)
    last = None
    for url in (config.MIRROR_API_V3, config.MIRROR_API_V2):
        for attempt in range(retries):
            try:
                r = s.get(url, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    data["_api"] = url
                    return data
                last = RuntimeError(f"{url} -> {r.status_code}")
                break  # non-200 is stable, try next API version
            except Exception as e:
                last = e
                time.sleep(2 ** attempt)
    raise RuntimeError(f"mirror API unreachable: {last}")
