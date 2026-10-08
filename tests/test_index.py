"""Phase: FTS index over files + remote + links."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ib_scrape.store import Store
from ib_scrape import index_fts


def _seed(root: Path):
    st = Store(root / "store")
    st.save(b"physics data", "wp", "http://x/p", "physics-notes")
    m = root / "manifests"
    m.mkdir()
    (m / "ibnotes_links.json").write_text(json.dumps(
        [{"url": "https://drive.google.com/x", "host": "drive.google.com",
          "platform": "google_drive", "direct_file": False}]))
    (m / "ibdocs_2025.json").write_text(json.dumps(
        [{"url": "http://ibdocs.re/Y", "name": "May 2025 Mathematics",
          "size": "-", "year": 2025, "session": "may-2025", "parent": "p"}]))
    return root / "store", m


def test_build_counts(tmp_path):
    store, mdir = _seed(tmp_path)
    n = index_fts.build(store, mdir)
    assert n == 3


def test_fts_search(tmp_path):
    import sqlite3
    store, mdir = _seed(tmp_path)
    index_fts.build(store, mdir)
    db = sqlite3.connect(store / "index.sqlite")
    hits = db.execute("SELECT kind,title FROM fts WHERE fts MATCH 'physics'").fetchall()
    assert ("file", "physics-notes") in hits
    hits = db.execute("SELECT kind FROM fts WHERE fts MATCH 'mathematics'").fetchall()
    assert ("remote",) in hits
