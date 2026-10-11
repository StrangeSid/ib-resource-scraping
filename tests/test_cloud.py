"""Phase: cloud catalog (Vercel). No sqlite, no blobs, no network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

import api.main as M
from api import cloud


def _cloud_client(monkeypatch):
    monkeypatch.setattr(M, "CLOUD_ENV", "1")
    return TestClient(M.app, follow_redirects=False)


def test_cloud_health_and_stats(monkeypatch):
    c = _cloud_client(monkeypatch)
    assert c.get("/health").json()["data"]["mode"] == "cloud"
    d = c.get("/stats").json()["data"]
    assert d["indexed"] > 50000 and d["remote_catalog"] > 50000
    assert d["links"] >= 600


def test_cloud_search_and_facets(monkeypatch):
    c = _cloud_client(monkeypatch)
    hits = c.get("/search", params={"q": "grade boundaries"}).json()
    assert hits["meta"]["count"] > 0
    assert hits["meta"]["mode"] == "cloud"
    f = c.get("/facets", params={"q": "physics"}).json()["data"]
    assert "rtype" in f and "yr" in f


def test_cloud_search_filters(monkeypatch):
    c = _cloud_client(monkeypatch)
    hits = c.get("/search", params={"q": "history", "rtype": "markscheme"}).json()["data"]
    assert hits and all(h["rtype"] == "markscheme" for h in hits)


def test_cloud_download_redirects(monkeypatch):
    import json
    c = _cloud_client(monkeypatch)
    sha = json.loads((cloud.MDIR / "index.json").read_text())[0]["sha256"]
    assert c.get(f"/resources/{sha}").json()["data"]["local"] is False
    r = c.get(f"/download/{sha}")
    assert r.status_code == 307 and r.headers["location"].startswith("http")
    assert c.get("/download/" + "0" * 64).status_code == 404


def test_cloud_refresh_blocked(monkeypatch):
    c = _cloud_client(monkeypatch)
    assert c.get("/mirrors", params={"refresh": "true"}).status_code == 403
    assert c.get("/mirrors").status_code == 200
