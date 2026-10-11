"""Filename/URL classifier: resource type, level, session, timezone, year.

Pure function, no I/O. Used at index time; covered by unit tests.
"""
import re

RTYPES = [
    ("markscheme", r"mark[\s_-]?scheme|marking|_ms\b|ms_|markschem"),
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
    ("paper", r"paper|exam|past.?paper|question.?paper|tz[0123]|\bhl\b|\bsl\b"),
]

LEVEL_RE = re.compile(r"(?<![A-Za-z])(HL|SL|MYP|PYP|DP|CORE|TOK|EE)(?![A-Za-z])", re.I)
SESSION_RE = re.compile(r"(May|November)\s*(19|20\d{2})", re.I)
YEAR_RE = re.compile(r"(19|20)\d{2}")
TZ_RE = re.compile(r"TZ([0123])", re.I)


def classify(name="", url="", parent=""):
    blob = f"{name} {url} {parent}"
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
    s = SESSION_RE.search(blob)
    session = f"{s.group(1).capitalize()} {s.group(2)}" if s else ""
    y = YEAR_RE.search(blob)
    year = y.group(0) if y else ""
    t = TZ_RE.search(blob)
    return {"rtype": rtype, "level": level, "session": session,
            "year": year, "tz": ("TZ" + t.group(1) if t else "")}
