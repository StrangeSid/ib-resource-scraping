"""Tests for scripts/pull.py pulling resources from remote API."""
import io
import json
import urllib.error
from unittest.mock import patch, MagicMock

from ib_scrape.store import Store
from scripts import pull


def test_pull_sha(tmp_path):
    store = Store(tmp_path / "store")
    sha = "testsha256" * 4

    meta_payload = {
        "status": "ok",
        "data": {
            "sha256": sha,
            "filename": "physics_hl_p1.pdf",
            "source": "brilliantlearning",
            "url": "https://example.com/physics.pdf",
            "subject": "Physics",
            "level": "HL",
            "rtype": "paper",
        },
    }
    file_bytes = b"%PDF-1.4 test fake content"

    def fake_urlopen(req, timeout=15):
        url = req.full_url
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        if f"/resources/{sha}" in url:
            mock_resp.read.return_value = json.dumps(meta_payload).encode("utf-8")
            return mock_resp
        if f"/download/{sha}" in url:
            mock_resp.read.return_value = file_bytes
            return mock_resp
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b""))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        ok = pull.pull_sha("https://mock-api.local", sha, store)
        assert ok is True

    # Verify stored in sqlite and blob
    row = store.db.execute("SELECT * FROM files WHERE filename=?", ("physics_hl_p1.pdf",)).fetchone()
    assert row is not None
    assert row[3] == "physics_hl_p1.pdf"
    assert row[7] == "Physics"


def test_pull_search_dry_run(tmp_path, capsys):
    store = Store(tmp_path / "store")
    search_payload = {
        "status": "ok",
        "data": [
            {
                "title": "Math HL Paper 1 May 2024.pdf",
                "kind": "remote",
                "rtype": "paper",
                "level": "HL",
                "url": "https://example.com/math.pdf",
            }
        ],
    }

    def fake_urlopen(req, timeout=15):
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = json.dumps(search_payload).encode("utf-8")
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        count = pull.pull_search("https://mock-api.local", "Math HL", store, dry_run=True)
        assert count == 1

    captured = capsys.readouterr()
    assert "Math HL Paper 1 May 2024.pdf" in captured.out
    assert "Dry run mode" in captured.out


def test_pull_search_download(tmp_path):
    store = Store(tmp_path / "store")
    search_payload = {
        "status": "ok",
        "data": [
            {
                "title": "Chemistry SL Paper 2.pdf",
                "kind": "remote",
                "rtype": "paper",
                "level": "SL",
                "url": "https://example.com/chem.pdf",
                "subject": "Chemistry",
            }
        ],
    }

    def fake_urlopen(req, timeout=15):
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        if "/search" in req.full_url:
            mock_resp.read.return_value = json.dumps(search_payload).encode("utf-8")
            return mock_resp
        if "https://example.com/chem.pdf" in req.full_url:
            mock_resp.read.return_value = b"%PDF chemistry file bytes"
            return mock_resp
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, io.BytesIO(b""))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        count = pull.pull_search("https://mock-api.local", "Chemistry", store)
        assert count == 1

    row = store.db.execute("SELECT * FROM files WHERE filename=?", ("Chemistry SL Paper 2.pdf",)).fetchone()
    assert row is not None
    assert row[3] == "Chemistry SL Paper 2.pdf"
