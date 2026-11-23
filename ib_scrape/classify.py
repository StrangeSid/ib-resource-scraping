"""Filename/URL classifier: resource type, level, session, timezone, year.

Pure function, no I/O. Used at index time; covered by unit tests.
"""
import re

from .search_util import clean_text

RTYPES = [
    ("markscheme", r"mark[\s_-]?scheme|marking|(?<![a-z0-9])ms(?![a-z0-9])|ms_|_ms\b|markschem"),
    ("specimen", r"specimen"),
    ("questionbank", r"questionbank|\bqb\b|question.?bank"),
    ("boundary", r"boundar|grade.?bound|grade.?descriptor"),
    ("syllabus", r"syllabus|subject.?guide|guide"),
    ("textbook", r"textbook|pearson|hodder|oxford|cambridge|book"),
    ("notes", r"notes?|cheatsheet|revision|study|summary|booklet(?!.*formula)"),
    ("formula", r"formula|data.?booklet"),
    ("exemplar", r"exemplar|\bia\b|\bee\b|tok|coursework|prescribed|assignment"),
    ("report", r"examiner.?report|subject.?report"),
    ("predicted", r"predict"),
    ("audio", r"audio|\.mp3|\.ogg|\.wav|\.m4a"),
    ("paper", r"paper|exam|past.?paper|question.?paper|(?<![a-z0-9])p[123][ab]?(?![a-z0-9])|tz[0123ab]|\bhl\b|\bsl\b"),
]

LEVEL_RE = re.compile(r"(?<![A-Za-z])(HL|SL|MYP|PYP|DP|CORE|TOK|EE)(?![A-Za-z])", re.I)
SESSION_RE = re.compile(
    r"(?<![A-Za-z0-9])(May|November|Nov)\s*[-_/]?\s*((?:19|20)\d{2})(?![A-Za-z0-9])",
    re.I,
)
SHORT_SESSION_RE = re.compile(
    r"(?<![A-Za-z0-9])([mn])((?:19|20)\d{2}|[0-3]\d)(?![A-Za-z0-9])",
    re.I,
)
YEAR_RE = re.compile(r"(?<![0-9])(?:19|20)\d{2}(?![0-9])")
TZ_RE = re.compile(r"(?<![A-Za-z0-9])TZ([0123AB])(?![A-Za-z0-9])", re.I)


def _extract_session_year(*sources: str) -> tuple[str, str]:
    """Extract (session, year) checking sources in priority order."""
    for src in sources:
        if not src:
            continue
        s = SESSION_RE.search(src)
        if s:
            mon = "November" if s.group(1).lower().startswith("nov") else "May"
            yr = s.group(2)
            return f"{mon} {yr}", yr
        m = SHORT_SESSION_RE.search(src)
        if m:
            mon = "May" if m.group(1).lower() == "m" else "November"
            raw_y = m.group(2)
            yr = raw_y if len(raw_y) == 4 else f"20{raw_y}"
            return f"{mon} {yr}", yr
    for src in sources:
        if not src:
            continue
        y = YEAR_RE.search(src)
        if y:
            return "", y.group(0)
    return "", ""


def classify(name="", url="", parent=""):
    name_c = clean_text(name)
    url_c = clean_text(url)
    parent_c = clean_text(parent)
    blob = f"{name_c} {url_c} {parent_c}"
    low = blob.lower()
    rtype = "other"
    for tag, pat in RTYPES:
        if re.search(pat, low):
            rtype = tag
            break
    m = LEVEL_RE.search(blob)
    level = m.group(1).upper() if m else ""
    if not level:
        if "myp" in low:
            level = "MYP"
        elif "pyp" in low:
            level = "PYP"
    session, year = _extract_session_year(name_c, parent_c, url_c)
    t = TZ_RE.search(blob)
    return {"rtype": rtype, "level": level, "session": session,
            "year": year, "tz": ("TZ" + t.group(1).upper() if t else "")}
