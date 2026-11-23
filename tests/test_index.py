"""Phase: FTS index over files + remote + links."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ib_scrape.store import Store
from ib_scrape import index_fts
from ib_scrape.search_util import (
    FTS_BM25_SQL,
    SYNONYMS,
    clean_text,
    expand_terms,
    fts_query,
    norm_level,
    norm_rtype,
    norm_session,
    norm_tz,
    norm_year,
    tokenize,
)


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


def test_clean_text_and_tokenize():
    assert clean_text("  May%202025%20&amp;%20Biology  ") == "May 2025 & Biology"
    assert clean_text("Mathematics_paper_1_TZ1_HL_markscheme.pdf") == "Mathematics_paper_1_TZ1_HL_markscheme.pdf"
    assert clean_text("grade-test") == "grade-test"
    assert clean_text("") == ""
    assert tokenize("Bio HL P1-MS!") == ["bio", "hl", "p1", "ms"]


def test_synonyms_expand_terms_and_fts_query():
    assert SYNONYMS["m24"] == (("may", "2024"),)
    assert SYNONYMS["n22"] == (("november", "2022"),)
    assert SYNONYMS["m2025"] == (("may", "2025"),)
    assert SYNONYMS["n2005"] == (("november", "2005"),)

    exp_bio = expand_terms("bio")
    assert exp_bio == [[("bio",), ("biology",)]]
    exp_ms = expand_terms("ms")
    assert exp_ms == [[("ms",), ("markscheme",), ("mark", "scheme")]]
    exp_cs = expand_terms("cs")
    assert exp_cs == [[("cs",), ("computer", "science")]]

    assert fts_query("") == '""'
    assert fts_query("   ") == '""'
    assert fts_query("physics") == "physics*"
    assert fts_query("bio") == "(bio* OR biology*)"
    assert fts_query("ms") == "(ms* OR markscheme* OR (mark* scheme*))"
    assert fts_query("m24 cs") == "(m24* OR (may* 2024*)) AND (cs* OR (computer* science*))"
    assert fts_query("physics paper 2") == "physics* AND paper* AND 2"
    assert index_fts.prefix_query("May 2026 Histor") == "May* 2026* Histor*"


def test_filter_normalizers():
    assert norm_rtype("markschemes") == "markscheme"
    assert norm_rtype("Boundaries") == "boundary"
    assert norm_rtype("papers") == "paper"
    assert norm_rtype("notes") == "notes"
    assert norm_level(" hl ") == "HL"
    assert norm_session(" Nov ") == "november"
    assert norm_session("Nov 2022") == "november 2022"
    assert norm_year(" 2025 ") == "2025"
    assert norm_tz("1") == "TZ1"
    assert norm_tz("a") == "TZA"
    assert norm_tz("tz2") == "TZ2"
    assert norm_tz("") == ""


def test_ts_of_and_cleaned_build_with_bm25_ranking(tmp_path):
    import sqlite3

    assert index_fts.ts_of(session="May 2025") == "2025-05-01"
    assert index_fts.ts_of(session="November 2022") == "2022-11-01"

    store = tmp_path / "store"
    mdir = tmp_path / "manifests"
    mdir.mkdir()
    st = Store(store)
    st.save(b"bio data", "wp", "http://x/bio", "Biology%20HL%20&amp;%20Notes")

    (mdir / "wp_media.json").write_text(json.dumps([
        {
            "url": "https://example.com/wp-content/uploads/2026/10/M25-Computer-Science-SL-P1.pdf",
            "name": "M25-Computer-Science-SL-P1.pdf",
            "ts": "",
        },
        {
            "url": "https://example.com/biology-archive/random-file.pdf",
            "name": "Random Resource",
            "ts": "",
        },
    ]))

    index_fts.build(store, mdir)
    db = sqlite3.connect(store / "index.sqlite")

    # Cleaned title in fts
    cleaned_row = db.execute(
        "SELECT title FROM fts WHERE kind='file'"
    ).fetchone()
    assert cleaned_row == ("Biology HL & Notes",)

    # M25 name beats upload URL 2026 for ts
    m25_row = db.execute(
        "SELECT ts, sess, yr FROM fts WHERE title='M25-Computer-Science-SL-P1.pdf'"
    ).fetchone()
    assert m25_row == ("2025-05-01", "May 2025", "2025")

    # Synonym query against SQLite FTS5
    cs_hits = db.execute(
        f"SELECT title FROM fts WHERE fts MATCH ? ORDER BY {FTS_BM25_SQL}",
        (fts_query("cs m25"),),
    ).fetchall()
    assert cs_hits == [("M25-Computer-Science-SL-P1.pdf",)]

    # Weighted BM25 ranks title hit above URL-only hit
    bio_hits = db.execute(
        f"SELECT title FROM fts WHERE fts MATCH ? ORDER BY {FTS_BM25_SQL}",
        (fts_query("bio"),),
    ).fetchall()
    assert bio_hits[0][0] == "Biology HL & Notes"
    assert ("Random Resource",) in bio_hits
