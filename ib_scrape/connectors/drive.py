"""Google Drive: folder listing (needs DRIVE_API_KEY) + direct export download.

ibnotes holds ~89 Drive folder links; without a key they stay record-only.
Set DRIVE_API_KEY env (free GCP key, Drive v3 files.list scope) to enumerate.
"""
import os
import re
import requests
from .. import config

FOLDER_RE = re.compile(r"/folders/([A-Za-z0-9_-]+)")
FILE_RE = re.compile(r"/file/d/([A-Za-z0-9_-]+)")


def folder_id(url):
    m = FOLDER_RE.search(url or "")
    return m.group(1) if m else None


def file_id(url):
    m = FILE_RE.search(url or "")
    return m.group(1) if m else None


def export_url(fid):
    return f"https://drive.google.com/uc?export=download&id={fid}"


def list_folder(folder_id, api_key=None, session=None):
    key = api_key or os.environ.get("DRIVE_API_KEY")
    if not key:
        raise RuntimeError("DRIVE_API_KEY missing — folder stays record-only")
    s = session or requests.Session()
    s.headers.update(config.UA)
    r = s.get("https://www.googleapis.com/drive/v3/files",
              params={"q": f"'{folder_id}' in parents and trashed=false",
                      "fields": "files(id,name,mimeType,size)",
                      "pageSize": 1000, "key": key}, timeout=30)
    r.raise_for_status()
    return r.json().get("files", [])


def download_file(fid, store, session=None, subject=""):
    s = session or requests.Session()
    s.headers.update(config.UA)
    r = s.get(export_url(fid), timeout=300)
    # large-file virus-scan interstitial: follow confirm token
    if "text/html" in r.headers.get("Content-Type", ""):
        m = re.search(r"confirm=([0-9A-Za-z_]+)", r.text)
        if not m:
            raise RuntimeError("drive confirm interstitial (private/quota?)")
        r = s.get(export_url(fid), params={"confirm": m.group(1)}, timeout=300)
        r.raise_for_status()
    name = r.headers.get("Content-Disposition", fid)
    m = re.search(r'filename="?([^";]+)', name)
    return store.save(r.content, source="google_drive",
                      url=export_url(fid), filename=m.group(1) if m else fid,
                      mime=r.headers.get("Content-Type", ""), subject=subject)
