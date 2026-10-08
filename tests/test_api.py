"""Phase: API endpoints. TestClient vs tmp store, no network."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

import api.main as M
from ib_scrape.store import Store
from ib_scrape import index_fts


@pytest.fixture()
def client(tmp_path, monkeypatch):
    store = tmp_path / "store"
    mdir = tmp_path / "manifests"
    mdir.mkdir()
    st = Store(store)
    st.save(b"pdf-bytes", "wp", "http://x/g", "grade-test")
    (mdir / "mirrors.json").write_text(json.dumps(
        {"mirrors": [{"name": "m1", "url": "https://x", "status": "online"}]}))
    index_fts.build(store, mdir)
    monkeypatch.setattr(M, "STORE", store)
    monkeypatch.setattr(M, "MDIR", mdir)
    return TestClient(M.app)


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_stats(client):
    d = client.get("/stats").json()["data"]
    assert d["files"] == 1 and d["links"] == 0


def test_search_and_resource_and_download(client):
    import sqlite3
    import api.main as M2
    hits = client.get("/search", params={"q": "grade"}).json()
    assert hits["meta"]["count"] == 1
    sha = sqlite3.connect(M2.STORE / "index.sqlite").execute(
        "SELECT sha256 FROM files").fetchone()[0]
    det = client.get(f"/resources/{sha}").json()["data"]
    assert det["filename"] == "grade-test" and det["local"] is True
    dl = client.get(f"/download/{sha}")
    assert dl.status_code == 200 and dl.content == b"pdf-bytes"


def test_404s(client):
    assert client.get("/resources/" + "0" * 64).status_code == 404
    assert client.get("/download/" + "0" * 64).status_code == 404


def test_mirrors_and_links(client):
    assert client.get("/mirrors").json()["data"][0]["name"] == "m1"
    assert client.get("/links").json()["data"] == []
