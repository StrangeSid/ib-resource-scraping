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
    assert {"search", "resource", "stats", "mirrors", "links"} <= names
    assert len(hits) == 1 and hits[0]["title"] == "biology-notes"
