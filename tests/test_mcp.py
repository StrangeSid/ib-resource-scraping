"""Phase: MCP tools. Plain function calls, no server run."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mcp_server as M
from ib_scrape.store import Store
from ib_scrape import index_fts


def _seed(tmp_path, monkeypatch):
    store = tmp_path / "store"
    mdir = tmp_path / "manifests"
    mdir.mkdir()
    st = Store(store)
    st.save(b"bio stuff", "wp", "http://x/b", "biology-notes")
    (mdir / "mirrors.json").write_text(json.dumps(
        {"mirrors": [{"name": "m1", "url": "https://x", "status": "online"}]}))
    index_fts.build(store, mdir)
    monkeypatch.setenv("STORE", str(store))
    monkeypatch.setenv("MANIFESTS", str(mdir))


def test_mcp_search_and_resource(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    hits = M.search("biology")
    assert len(hits) == 1 and hits[0]["title"] == "biology-notes"
    import sqlite3
    sha = sqlite3.connect(tmp_path / "store" / "index.sqlite").execute(
        "SELECT sha256 FROM files").fetchone()[0]
    assert M.resource(sha)["filename"] == "biology-notes"
    assert "error" in M.resource("0" * 64)


def test_mcp_stats_mirrors_links(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    assert M.stats()["files"] == 1
    assert M.mirrors()[0]["name"] == "m1"
    assert M.links() == []


def test_mcp_stdio_transport(tmp_path, monkeypatch):
    import os
    import subprocess
    import time
    _seed(tmp_path, monkeypatch)
    root = Path(__file__).resolve().parent.parent
    env = dict(os.environ, STORE=str(tmp_path / "store"),
               MANIFESTS=str(tmp_path / "manifests"))
    p = subprocess.Popen(
        [sys.executable, "mcp_server.py"], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, bufsize=1, cwd=root, env=env)
    try:
        def rpc(method, params=None, i=1):
            msg = {"jsonrpc": "2.0", "id": i, "method": method}
            if params is not None:
                msg["params"] = params
            p.stdin.write(json.dumps(msg) + "\n")
            p.stdin.flush()
            deadline = time.time() + 30
            while time.time() < deadline:
                line = p.stdout.readline().strip()
                if line.startswith("{"):
                    return json.loads(line)

        rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                           "clientInfo": {"name": "t", "version": "1"}}, 1)
        p.stdin.write(json.dumps({"jsonrpc": "2.0",
                                  "method": "notifications/initialized"}) + "\n")
        p.stdin.flush()
        names = {t["name"] for t in
                 rpc("tools/list", {}, 2)["result"]["tools"]}
        raw = json.loads(rpc(
            "tools/call", {"name": "search", "arguments": {"q": "biology"}},
            3)["result"]["content"][0]["text"])
        # FastMCP unwraps single-item lists over the wire
        hits = raw if isinstance(raw, list) else [raw]
    finally:
        p.kill()
    assert {"search", "resource", "download_url", "stats", "mirrors", "links", "facets"} <= names
    assert len(hits) == 1 and hits[0]["title"] == "biology-notes"


def test_mcp_remote_mode(monkeypatch):
    import io
    import urllib.error
    from unittest.mock import patch, MagicMock

    monkeypatch.setenv("IB_API_BASE", "https://mock-api.local")
    mock_responses = {
        "/search": {"status": "ok", "data": [{"title": "Remote Bio", "url": "http://x"}]},
        "/resources/abc": {"status": "ok", "data": {"sha256": "abc", "filename": "bio.pdf"}},
        "/stats": {"status": "ok", "data": {"files": 42}},
        "/mirrors": {"status": "ok", "data": [{"name": "mock-mirror"}]},
        "/links": {"status": "ok", "data": [{"url": "http://gdrive"}]},
        "/facets": {"status": "ok", "data": {"rtype": [{"value": "paper", "count": 10}]}},
    }

    def fake_urlopen(req, timeout=15):
        url = req.full_url
        for path, data in mock_responses.items():
            if path in url:
                resp = MagicMock()
                resp.__enter__.return_value = resp
                resp.read.return_value = json.dumps(data).encode("utf-8")
                return resp
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b""))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        assert M.search("bio")[0]["title"] == "Remote Bio"
        assert M.resource("abc")["filename"] == "bio.pdf"
        assert M.stats()["files"] == 42
        assert M.mirrors()[0]["name"] == "mock-mirror"
        assert M.links()[0]["url"] == "http://gdrive"
        assert M.facets()["rtype"][0]["count"] == 10
        assert M.download_url("abc")["url"] == "https://mock-api.local/download/abc"
