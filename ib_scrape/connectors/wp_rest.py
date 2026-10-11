"""brilliantlearning.in via open WP REST. Direct source_url download (no auth)."""
import requests
from .. import config


def iter_media(search=None, per_page=100, max_pages=100, session=None):
    s = session or requests.Session()
    s.headers.update(config.UA)
    page, total_pages = 1, 1
    while page <= min(total_pages, max_pages):
        r = s.get(config.WP_MEDIA, params={"per_page": per_page, "page": page,
                                            **({"search": search} if search else {})},
                  timeout=30)
        if r.status_code == 400:  # past end
            break
        r.raise_for_status()
        total_pages = int(r.headers.get("X-WP-TotalPages", 1))
        yield from r.json()
        page += 1


def catalog_item(item):
    """Lightweight record (no bytes) for the remote catalog."""
    return {"url": item.get("source_url") or "",
            "name": item.get("slug") or "",
            "size": str(item.get("filesize") or item.get("media_details", {})
                        .get("filesize", "")),
            "year": (item.get("date") or "")[:4],
            "ts": (item.get("date") or "")[:10],
            "session": "", "parent": "", "source": "brilliantlearning",
            "mime": item.get("mime_type", "")}


def download_item(item, store, session=None):
    url = item.get("source_url") or ""
    if not url:
        return None, False
    s = session or requests.Session()
    s.headers.update(config.UA)
    r = s.get(url, timeout=120)
    r.raise_for_status()
    return store.save(r.content, source="brilliantlearning",
                      url=url, filename=item.get("slug", "file"),
                      mime=item.get("mime_type", ""))
