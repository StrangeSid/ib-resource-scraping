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
    assert hits["meta"]["total"] >= hits["meta"]["count"]
    assert hits["meta"]["mode"] == "cloud"
    f = c.get("/facets", params={"q": "physics"}).json()["data"]
    assert "rtype" in f and "yr" in f and "source" in f


def test_cloud_search_filters(monkeypatch):
    c = _cloud_client(monkeypatch)
    hits = c.get("/search", params={"q": "history", "rtype": "markschemes", "level": "hl"}).json()["data"]
    assert hits and all(h["rtype"] == "markscheme" and h["level"] == "HL" for h in hits)

    bio = c.get("/search", params={"q": "bio hl ms"}).json()["data"]
    assert bio and all("command terms" not in h["title"].lower() for h in bio)
    assert any(h["rtype"] == "markscheme" and h["level"] == "HL" for h in bio)

    phys = c.get("/search", params={"q": "physics paper 2 tz1"}).json()["data"]
    assert phys
    assert "paper_2" in phys[0]["title"].lower() or "paper 2" in phys[0]["title"].lower()

    f = c.get("/facets", params={"q": "physics", "tz": "1", "level": "hl"}).json()["data"]
    assert all(o["value"] == "TZ1" for o in f["tz"])


def test_cloud_synthetic_index_filters_and_ts(tmp_path, monkeypatch):
    import json
    mdir = tmp_path / "manifests"
    mdir.mkdir()
    (mdir / "index.json").write_text(json.dumps([
        {
            "sha256": "a" * 64,
            "filename": "Biology%20HL%20&amp;%20Command%20Terms.pdf",
            "url": "https://x/bio-terms.pdf",
            "source": "ibdocs",
            "subject": "Biology",
            "fetched_at": "2026-01-01T00:00:00Z",
        },
        {
            "sha256": "b" * 64,
            "filename": "Biology_HL_markscheme_N24.pdf",
            "url": "https://x/bio-ms.pdf",
            "source": "ibdocs:mirror1",
            "subject": "Biology",
            "fetched_at": "2026-01-01T00:00:00Z",
        },
    ]))
    (mdir / "wp_media.json").write_text(json.dumps([
        {
            "url": "https://x/wp-content/uploads/2026/10/M25-Physics-HL-TZ1-P2.pdf",
            "name": "M25-Physics-HL-TZ1-P2.pdf",
            "year": "2026",
            "ts": "2026-10-28",
            "source": "brilliantlearning",
        },
        {
            "url": "https://x/wp-content/uploads/2026/10/Physics-Paper-2-TZ1-2024.pdf",
            "name": "Physics Paper 2 TZ1 2024",
            "year": "2024",
            "ts": "2024-05-01",
            "source": "brilliantlearning",
        },
        {
            "url": "https://x/wp-content/uploads/2026/10/Physics-Paper-1-TZ1-2026.pdf",
            "name": "Physics Paper 1 TZ1 2026",
            "year": "2026",
            "ts": "2026-10-28",
            "source": "brilliantlearning",
        },
        {
            "url": "https://x/wp-content/uploads/2026/10/General-Notes.pdf",
            "name": "General-Notes.pdf",
            "ts": "2026-10-28",
            "source": "brilliantlearning",
        },
    ]))
    (mdir / "mirrors.json").write_text(json.dumps({"mirrors": []}))

    monkeypatch.setattr(cloud, "MDIR", mdir)
    cloud.clear_cache()
    try:
        # Clean text + no substring false positive on Command Terms for 'ms'
        bio_hits, total = cloud.search_with_total("bio hl ms")
        assert total == 1
        assert bio_hits[0]["title"] == "Biology_HL_markscheme_N24.pdf"

        # M25 prefers session/year timestamp over upload ts; General-Notes keeps upload ts
        m25 = cloud.search("M25 Physics")[0]
        assert m25["ts"] == "2025-05-01"
        assert m25["yr"] == "2025" and m25["sess"] == "May 2025"
        notes = cloud.search("General Notes")[0]
        assert notes["ts"] == "2026-10-28"

        # Exact token '2' beats prefix '2026' on Paper 1 2026
        phys = cloud.search("physics paper 2 tz1")
        assert phys[0]["title"] == "Physics Paper 2 TZ1 2024"

        # Exact year (not substring), normalized tz, session, rtype, level, source prefix
        assert cloud.search("biology", year="202") == []
        assert len(cloud.search("biology", year="2024", session="nov",
                                rtype="markschemes", level="hl")) == 1
        assert len(cloud.search("biology", source="ibdocs")) == 2
        assert len(cloud.search("physics", tz="1")) == 3

        f = cloud.facets(source="ibdocs")
        assert "source" in f and f["kind"][0]["value"] == "file"
    finally:
        cloud.clear_cache()


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
