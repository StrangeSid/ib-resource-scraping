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


def test_search_file_carries_sha(client):
    import sqlite3
    import api.main as M2
    sha = sqlite3.connect(M2.STORE / "index.sqlite").execute(
        "SELECT sha256 FROM files").fetchone()[0]
    hits = client.get("/search", params={"q": "grade", "kind": "file"}).json()["data"]
    assert hits and hits[0]["extra"] == sha


def test_search_prefix_and_sort(client):
    from ib_scrape.index_fts import prefix_query
    assert prefix_query("May 2026 Histor") == "May* 2026* Histor*"
    hits = client.get("/search", params={"q": "grad"}).json()["data"]
    assert hits and hits[0]["title"] == "grade-test"
    r = client.get("/search", params={"q": "grade", "sort": "recent"}).json()
    assert r["meta"]["sort"] == "recent" and r["meta"]["count"] >= 1
    bad = client.get("/search", params={"q": "grade", "sort": "nope"})
    assert bad.status_code == 422


def test_search_filters_and_facets(client):
    import sqlite3
    import api.main as M2
    db = sqlite3.connect(M2.STORE / "index.sqlite")
    db.execute("INSERT INTO remote_files VALUES (?,?,?,?,?,?,?,?,?)",
               ("http://x/hl-ms", "ibdocs:sub", "History HL TZ1 markscheme", "", "2025",
                "nov-2025", "", "2026-01-01", ""))
    db.execute("INSERT INTO remote_files VALUES (?,?,?,?,?,?,?,?,?)",
               ("http://x/bio-ms", "ibdocs", "Biology HL TZ2 markscheme", "", "2024",
                "may-2024", "", "2026-01-01", ""))
    db.execute("INSERT INTO remote_files VALUES (?,?,?,?,?,?,?,?,?)",
               ("http://x/bio-terms", "other", "Biology HL Command Terms", "", "2024",
                "may-2024", "", "2026-01-01", ""))
    db.commit()
    from ib_scrape import index_fts
    index_fts.build(M2.STORE, M2.MDIR)

    res = client.get("/search", params={"q": "history", "rtype": "markschemes"}).json()
    assert res["meta"]["total"] == 1
    assert res["data"] and all(h["rtype"] == "markscheme" for h in res["data"])

    hits = client.get("/search", params={"q": "history", "level": "hl"}).json()["data"]
    assert hits and all(h["level"] == "HL" for h in hits)

    hits = client.get("/search", params={"q": "history", "tz": "1", "session": "nov", "year": "2025"}).json()["data"]
    assert len(hits) == 1 and hits[0]["tz"] == "TZ1"

    hits = client.get("/search", params={"q": "history", "source": "ibdocs"}).json()["data"]
    assert len(hits) == 1 and hits[0]["source"] == "ibdocs:sub"

    hits = client.get("/search", params={"q": "history", "rtype": "paper"}).json()["data"]
    assert hits == []

    # Synonym expansion + no substring false positive on Command Terms
    bio_res = client.get("/search", params={"q": "bio hl ms"}).json()
    assert bio_res["meta"]["total"] == 1
    assert bio_res["data"][0]["title"] == "Biology HL TZ2 markscheme"

    # Pagination preserves total
    paged = client.get("/search", params={"q": "biology", "limit": 1, "offset": 1}).json()
    assert paged["meta"]["count"] == 1 and paged["meta"]["total"] == 2

    f = client.get("/facets", params={"q": "history", "source": "ibdocs", "tz": "1"}).json()["data"]
    assert any(o["value"] == "markscheme" for o in f["rtype"])
    assert any(o["value"] == "ibdocs:sub" for o in f["source"])
    fall = client.get("/facets").json()["data"]
    assert "yr" in fall and "level" in fall and "source" in fall


def test_ui_served():
    from fastapi.testclient import TestClient as TC
    import api.main as M2
    r = TC(M2.app).get("/")
    assert r.status_code == 200 and "<title>IB Index" in r.text


def test_recent_and_stats_indexed(client):
    r = client.get("/recent", params={"limit": 5}).json()
    assert r["meta"]["count"] == 1 and r["data"][0]["filename"] == "grade-test"
    assert client.get("/stats").json()["data"]["indexed"] == 1
