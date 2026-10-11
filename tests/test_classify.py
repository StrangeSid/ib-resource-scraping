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
