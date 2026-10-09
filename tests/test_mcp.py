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
