"""Shared search text cleaning, query synonym expansion, and filter normalizers."""
import html
import re
from urllib.parse import unquote

SYNONYMS: dict[str, tuple[str | tuple[str, ...], ...]] = {
    # Subjects
    "bio": ("biology",),
    "chem": ("chemistry",),
    "phys": ("physics",),
    "math": ("mathematics", "maths"),
    "maths": ("mathematics", "math"),
    "econ": ("economics",),
    "psych": ("psychology",),
    "geo": ("geography",),
    "hist": ("history",),
    "cs": (("computer", "science"),),
    "ess": ("environmental",),
    "bm": ("business",),
    "tok": (("theory", "of", "knowledge"),),
    # Types / terms
    "ms": ("markscheme", ("mark", "scheme")),
    "gb": (("grade", "boundaries"),),
    "qb": ("questionbank", ("question", "bank")),
    "p1": (("paper", "1"),),
    "p2": (("paper", "2"),),
    "p3": (("paper", "3"),),
    "p1a": (("paper", "1a"),),
    "p1b": (("paper", "1b"),),
}

for _y in range(5, 30):
    _yr = f"20{_y:02d}"
    SYNONYMS[f"m{_y:02d}"] = (("may", _yr),)
    SYNONYMS[f"n{_y:02d}"] = (("november", _yr),)
    SYNONYMS[f"m{_yr}"] = (("may", _yr),)
    SYNONYMS[f"n{_yr}"] = (("november", _yr),)

RTYPE_ALIASES = {
    "boundaries": "boundary",
    "markschemes": "markscheme",
    "papers": "paper",
    "textbooks": "textbook",
    "syllabi": "syllabus",
    "specimens": "specimen",
    "exemplars": "exemplar",
    "reports": "report",
    "questionbanks": "questionbank",
    "notes": "notes",
}

# Weights for: kind, title, url, source, subject, extra, ts, rtype, level, sess, yr, tz
FTS_BM25_SQL = "bm25(fts, 0.2, 10.0, 1.0, 0.5, 4.0, 0.0, 0.0, 2.0, 2.0, 2.0, 2.0, 1.5)"


def clean_text(s: str) -> str:
    """Decode URL-encoding and HTML entities, collapse whitespace, keep _ and -."""
    raw = "" if s is None else str(s)
    return re.sub(r"\s+", " ", html.unescape(unquote(raw))).strip()


def tokenize(q: str) -> list[str]:
    """Extract lowercase alphanumeric tokens for safe FTS5 querying."""
    return re.findall(r"[a-z0-9]+", (q or "").lower())


def expand_terms(q: str) -> list[list[tuple[str, ...]]]:
    """Expand each token in q to deduplicated tuple-of-token alternatives."""
    out: list[list[tuple[str, ...]]] = []
    for tok in tokenize(q):
        alts: list[tuple[str, ...]] = [(tok,)]
        for alt in SYNONYMS.get(tok, ()):
            tup = (alt,) if isinstance(alt, str) else tuple(alt)
            if tup not in alts:
                alts.append(tup)
        out.append(alts)
    return out


def norm_rtype(v: str) -> str:
    """Normalize resource type filter value using plural/alias mapping."""
    s = (v or "").strip().lower()
    return RTYPE_ALIASES.get(s, s)


def norm_level(v: str) -> str:
    """Normalize level filter value to uppercase."""
    return (v or "").strip().upper()


def norm_session(v: str) -> str:
    """Normalize session filter value to lowercase, expanding 'nov' to 'november'."""
    s = (v or "").strip().lower()
    return "november" if s == "nov" else re.sub(r"^nov\b", "november", s)


def norm_year(v: str) -> str:
    """Normalize year filter value."""
    return ("" if v is None else str(v)).strip()


def norm_tz(v: str) -> str:
    """Normalize timezone filter value (e.g. '1' -> 'TZ1', 'a' -> 'TZA')."""
    s = (v or "").strip().upper()
    return f"TZ{s}" if len(s) == 1 and s in "0123AB" else s


def is_prefix_token(tok: str) -> bool:
    """Short numeric tokens (e.g. paper '1', '2', '3') match exact, not '2025'."""
    return not (tok.isdigit() and len(tok) < 4)


def fts_query(q: str) -> str:
    """Build a safe FTS5 MATCH query string with prefix matching and synonyms."""
    def fmt(t: str) -> str:
        return f"{t}*" if is_prefix_token(t) else t

    groups: list[str] = []
    for alts in expand_terms(q):
        rendered = [
            fmt(alt[0]) if len(alt) == 1 else "(" + " ".join(fmt(t) for t in alt) + ")"
            for alt in alts
        ]
        groups.append(rendered[0] if len(rendered) == 1 else "(" + " OR ".join(rendered) + ")")
    # SQLite FTS5 requires explicit AND between parenthesized OR groups.
    return " AND ".join(groups) or '""'
