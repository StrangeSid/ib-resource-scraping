"""Phase: content-addressed store. Real files in tmp_path, no network."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ib_scrape.store import Store


def test_save_and_dedup(tmp_path):
    st = Store(tmp_path / "store")
    p1, new1 = st.save(b"hello", "t", "http://x/1", "a.pdf", mime="application/pdf")
    p2, new2 = st.save(b"hello", "t", "http://x/1", "a.pdf", mime="application/pdf")
    assert new1 and not new2 and p1 == p2
    assert Path(p1).read_bytes() == b"hello"


def test_manifest(tmp_path):
    st = Store(tmp_path / "store")
    st.save(b"abc", "wp", "http://x/2", "b.pdf")
    n = st.manifest(str(tmp_path / "m" / "index.json"))
    rows = json.loads((tmp_path / "m" / "index.json").read_text())
    assert n == 1 and rows[0]["filename"] == "b.pdf" and len(rows[0]["sha256"]) == 64
