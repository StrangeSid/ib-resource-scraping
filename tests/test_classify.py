"""Phase: classifier. Pure function, no I/O."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ib_scrape.classify import classify


def test_markscheme():
    c = classify("Mathematics_paper_1_TZ1_HL_markscheme.pdf")
    assert (c["rtype"], c["level"], c["tz"]) == ("markscheme", "HL", "TZ1")
    assert c["year"] == ""


def test_paper_session():
    c = classify("History_paper_1", "https://x/IB/2025 Examination Session/May 2025/paper.pdf")
    assert c["rtype"] == "paper" and c["session"] == "May 2025" and c["year"] == "2025"


def test_boundary_notes_textbook():
    assert classify("May 2026 Grade Boundaries.pdf")["rtype"] == "boundary"
    assert classify("Bio - Option D", "https://x/notes/bio")["rtype"] == "notes"
    assert classify("PEARSON Biology HL", "")["rtype"] == "textbook"
    assert classify("May 2025 Examination Session/audio/file.mp3")["rtype"] == "audio"


def test_levels_programs():
    assert classify("Physics SL Paper 2")["level"] == "SL"
    assert classify("MYP Grade Boundaries")["level"] == "MYP"
    assert classify("TOK Exhibition A")["level"] == "TOK"
    assert classify("random file xyz")["rtype"] == "other"


def test_short_markscheme_and_paper_codes():
    c1 = classify("n22-biology-hl-p1-ms.pdf")
    assert c1["rtype"] == "markscheme"
    assert c1["level"] == "HL"
    assert c1["session"] == "November 2022"
    assert c1["year"] == "2022"

    c2 = classify("m26-physics_paper_1a_tz1_sl_markscheme.pdf")
    assert (c2["rtype"], c2["level"], c2["tz"]) == ("markscheme", "SL", "TZ1")
    assert (c2["session"], c2["year"]) == ("May 2026", "2026")

    assert classify("chem-sl-p1a.pdf")["rtype"] == "paper"
    assert classify("math-hl-p1b.pdf")["rtype"] == "paper"
    assert classify("econ-p3.pdf")["rtype"] == "paper"


def test_session_codes_and_priority():
    c_m2026 = classify("m2026-history-hl.pdf")
    assert (c_m2026["session"], c_m2026["year"]) == ("May 2026", "2026")

    c_nov = classify("Nov-2023 Economics HL.pdf")
    assert (c_nov["session"], c_nov["year"]) == ("November 2023", "2023")

    c_prio = classify(
        "M25-Computer-Science-SL.pdf",
        "https://example.com/wp-content/uploads/2026/10/M25-Computer-Science-SL.pdf",
    )
    assert c_prio["session"] == "May 2025"
    assert c_prio["year"] == "2025"


def test_timezone_tza_tzb_and_clean_text():
    assert classify("biology-tza-p1.pdf")["tz"] == "TZA"
    assert classify("biology_TZB_p2.pdf")["tz"] == "TZB"
    assert classify("physics_tz0.pdf")["tz"] == "TZ0"
    assert classify("timezone_guide.pdf")["tz"] == ""
    assert classify("paper_tz10.pdf")["tz"] == ""

    c = classify("May%202025%20Physics%20&amp;%20Math%20HL_ms.pdf")
    assert c["rtype"] == "markscheme"
    assert c["level"] == "HL"
    assert (c["session"], c["year"]) == ("May 2025", "2025")
