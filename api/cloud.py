"""Cloud catalog: read-only search over committed manifests, no sqlite.

Vercel serverless has no persistent disk, so the cloud API never touches
STORE/index.sqlite or blobs/. It loads manifests/*.json (committed, ~15M),
classifies in memory once per cold start (~1s for 53k rows), then serves
search/facets/stats/links/mirrors from that cache.

Local self-host keeps the sqlite+blobs path in api/main.py (CLOUD_MODE=0).
"""
import json
import math
import os
from bisect import bisect_left
from functools import lru_cache
from pathlib import Path

from ib_scrape.search_util import (
    clean_text,
    expand_terms,
    is_prefix_token,
    norm_level,
    norm_rtype,
    norm_session,
    norm_tz,
    norm_year,
    tokenize,
)

ROOT = Path(__file__).resolve().parent.parent
MDIR = Path(os.environ.get("MANIFESTS", ROOT / "manifests"))

_KIND_TIE = {"file": 0.02, "remote": 0.01, "link": 0.0}
_PUBLIC_KEYS = (
    "kind", "title", "url", "source", "subject",
    "extra", "ts", "rtype", "level", "sess", "yr", "tz",
)


def _load_json(name):
    p = MDIR / name
    if not p.exists():
        return []
    try:
        d = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return d if isinstance(d, list) else []


def _load_mirrors():
    p = MDIR / "mirrors.json"
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())["mirrors"]
    except (json.JSONDecodeError, KeyError, OSError):
        return []


@lru_cache(maxsize=1)
def records():
    """All searchable rows. Schema matches FTS output in api/main.py."""
    from ib_scrape.classify import classify
    from ib_scrape.index_fts import ts_of

    out = []

    # 31 local-file manifests -> kind=file (cloud has no bytes; download redirects)
    for r in _load_json("index.json"):
        sha = r.get("sha256", "")
        title = clean_text(r.get("filename", ""))
        url = r.get("url", "")
        subj = clean_text(r.get("subject", ""))
        c = classify(title, url, subj)
        fallback_ts = r.get("ts", "") or r.get("fetched_at", "")
        row_ts = (
            ts_of(url, c["year"], c["session"])
            if (c["year"] and c["session"])
            else (ts_of(url, c["year"]) or fallback_ts)
        )
        out.append({
            "kind": "file", "title": title, "url": url,
            "source": r.get("source", ""), "subject": subj,
            "extra": sha, "ts": row_ts,
            "rtype": c["rtype"], "level": c["level"], "sess": c["session"],
            "yr": c["year"], "tz": c["tz"],
        })

    # remote catalogs -> kind=remote
    for name in sorted(p.name for p in MDIR.glob("*.json")):
        if name in ("index.json", "mirrors.json", "ibnotes_links.json"):
            continue
        if not (name.startswith(("ibdocs_", "xtreme_", "tfm_", "dufs_", "wp_"))):
            continue
        for r in _load_json(name):
            url = r.get("url", "")
            if not url:
                continue
            title = clean_text(r.get("name", "") or url)
            raw_subj = " ".join(
                str(r.get(k, "")) for k in ("year", "session", "parent", "dirpath")
            ).strip()
            subj = clean_text(raw_subj)
            c = classify(title, url, subj)
            yr = c["year"] or str(r.get("year", ""))
            sess = c["session"] or str(r.get("session", ""))
            fallback_ts = r.get("ts", "") or r.get("fetched_at", "")
            row_ts = (
                ts_of(url, c["year"], c["session"])
                if (c["year"] and c["session"])
                else (ts_of(url, yr, sess, explicit=fallback_ts) or fallback_ts)
            )
            out.append({
                "kind": "remote", "title": title, "url": url,
                "source": r.get("source", name.split("_")[0]),
                "subject": subj, "extra": "",
                "ts": row_ts,
                "rtype": c["rtype"], "level": c["level"],
                "sess": sess,
                "yr": yr,
                "tz": c["tz"],
            })

    # link graph -> kind=link
    for r in _load_json("ibnotes_links.json"):
        url = r.get("url", "")
        if not url:
            continue
        out.append({
            "kind": "link", "title": clean_text(url), "url": url,
            "source": r.get("platform", ""), "subject": clean_text(r.get("host", "")),
            "extra": "", "ts": "",
            "rtype": "other", "level": "", "sess": "", "yr": "", "tz": "",
        })

    return out


def _tf(tokens: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    return counts


@lru_cache(maxsize=1)
def _index() -> dict:
    """Build cached inverted index + per-field TF/IDF stats over records()."""
    rows = records()
    n = len(rows)
    postings_lists: dict[str, list[int]] = {}
    title_tf: list[dict[str, int]] = []
    subj_tf: list[dict[str, int]] = []
    meta_tf: list[dict[str, int]] = []
    url_tf: list[dict[str, int]] = []
    title_len: list[int] = []

    for idx, r in enumerate(rows):
        t_toks = tokenize(r["title"])
        s_toks = tokenize(r["subject"])
        m_toks = tokenize(" ".join((
            r["rtype"], r["level"], r["sess"], r["yr"], r["tz"], r["source"],
        )))
        u_toks = tokenize(r["url"])

        t_map = _tf(t_toks)
        s_map = _tf(s_toks)
        m_map = _tf(m_toks)
        u_map = _tf(u_toks)

        title_tf.append(t_map)
        subj_tf.append(s_map)
        meta_tf.append(m_map)
        url_tf.append(u_map)
        title_len.append(len(t_toks))

        for tok in set(t_map) | set(s_map) | set(m_map) | set(u_map):
            lst = postings_lists.get(tok)
            if lst is None:
                postings_lists[tok] = [idx]
            else:
                lst.append(idx)

    postings = {tok: tuple(ids) for tok, ids in postings_lists.items()}
    sorted_vocab = sorted(postings)
    avg_title_len = (sum(title_len) / n) if n else 1.0
    if avg_title_len <= 0.0:
        avg_title_len = 1.0
    idf = {
        tok: math.log((n - len(ids) + 0.5) / (len(ids) + 0.5) + 1.0)
        for tok, ids in postings.items()
    }
    return {
        "postings": postings,
        "sorted_vocab": sorted_vocab,
        "title_tf": title_tf,
        "subj_tf": subj_tf,
        "meta_tf": meta_tf,
        "url_tf": url_tf,
        "title_len": title_len,
        "avg_title_len": avg_title_len,
        "idf": idf,
    }


def _vocab_matches(sorted_vocab: list[str], prefix: str) -> list[str]:
    """Return matching vocabulary tokens (exact only for short digits, prefix otherwise)."""
    i = bisect_left(sorted_vocab, prefix)
    n = len(sorted_vocab)
    if not is_prefix_token(prefix):
        return [prefix] if i < n and sorted_vocab[i] == prefix else []
    out: list[str] = []
    while i < n and sorted_vocab[i].startswith(prefix):
        out.append(sorted_vocab[i])
        i += 1
    return out


def _score_token(tok: str, vocabs: list[str], idx: int, index: dict) -> float:
    """BM25-style weighted field score for one query token on row idx."""
    t_m = index["title_tf"][idx]
    s_m = index["subj_tf"][idx]
    m_m = index["meta_tf"][idx]
    u_m = index["url_tf"][idx]
    norm = 0.25 + 0.75 * (index["title_len"][idx] / index["avg_title_len"])
    idf = index["idf"]
    allow_prefix = is_prefix_token(tok)
    base_idf_cap = idf.get(tok)
    if base_idf_cap is None and vocabs:
        base_idf_cap = min(idf[v] for v in vocabs)

    if len(vocabs) <= 16:
        candidates = vocabs
    elif not allow_prefix:
        candidates = [tok] if tok in t_m or tok in s_m or tok in m_m or tok in u_m else []
    else:
        candidates = [
            v for v in (t_m.keys() | s_m.keys() | m_m.keys() | u_m.keys())
            if v.startswith(tok)
        ]

    best = 0.0
    for v in candidates:
        fscore = 0.0
        tf = t_m.get(v, 0)
        if tf:
            fscore += 10.0 * (tf * 2.2) / (tf + 1.2 * norm)
        tf = s_m.get(v, 0)
        if tf:
            fscore += 4.0 * (tf * 2.2) / (tf + 1.2)
        tf = m_m.get(v, 0)
        if tf:
            fscore += 2.0 * (tf * 2.2) / (tf + 1.2)
        tf = u_m.get(v, 0)
        if tf:
            fscore += 1.0 * (tf * 2.2) / (tf + 1.2)
        if fscore > 0.0:
            mult = 1.0 if v == tok else 0.65
            # Cap prefix-match IDF so rare prefix compounds do not outscore common exact matches.
            v_idf = min(idf[v], base_idf_cap) if base_idf_cap is not None else idf[v]
            sc = mult * v_idf * fscore
            if sc > best:
                best = sc
    return best


def _all_in_field(alt: tuple[str, ...], field_map: dict[str, int]) -> bool:
    return all(
        (t in field_map if not is_prefix_token(t) else any(k.startswith(t) for k in field_map))
        for t in alt
    )


def _matches_filters(
    r: dict, kind: str, rtype: str, level: str,
    session: str, year: str, tz: str, source: str,
) -> bool:
    if kind and r["kind"] != kind:
        return False
    if rtype and r["rtype"] != rtype:
        return False
    if level and r["level"].upper() != level:
        return False
    if session and session not in r["sess"].lower():
        return False
    if year and r["yr"] != year:
        return False
    if tz and r["tz"].upper() != tz:
        return False
    if source:
        rs = r["source"].lower()
        if rs != source and not rs.startswith(source + ":"):
            return False
    return True


def _filtered(q="", kind="", rtype="", level="", session="", year="",
              tz="", source=""):
    rows = records()
    k = kind.strip().lower()
    rt = norm_rtype(rtype)
    lv = norm_level(level)
    sess = norm_session(session)
    yr = norm_year(year)
    tz_norm = norm_tz(tz)
    src = source.strip().lower()
    has_filters = any((k, rt, lv, sess, yr, tz_norm, src))

    if not q.strip():
        if not has_filters:
            return list(rows)
        return [r for r in rows if _matches_filters(r, k, rt, lv, sess, yr, tz_norm, src)]

    groups = expand_terms(q)
    if not groups:
        return []

    index = _index()
    postings = index["postings"]
    sorted_vocab = index["sorted_vocab"]
    tok_vocabs: dict[str, list[str]] = {}
    tok_rows: dict[str, set[int]] = {}

    for alts in groups:
        for alt in alts:
            for t in alt:
                if t not in tok_vocabs:
                    vs = _vocab_matches(sorted_vocab, t)
                    tok_vocabs[t] = vs
                    rs: set[int] = set()
                    for v in vs:
                        rs.update(postings[v])
                    tok_rows[t] = rs

    group_sets: list[set[int]] = []
    for alts in groups:
        grp_rows: set[int] = set()
        for alt in alts:
            if len(alt) == 1:
                grp_rows.update(tok_rows[alt[0]])
            else:
                ordered = sorted((tok_rows[t] for t in alt), key=len)
                inter = set(ordered[0]) if ordered[0] else set()
                for rset in ordered[1:]:
                    if not inter:
                        break
                    inter &= rset
                if inter:
                    grp_rows.update(inter)
        if not grp_rows:
            return []
        group_sets.append(grp_rows)

    group_sets.sort(key=len)
    cand = set(group_sets[0])
    for gs in group_sets[1:]:
        cand &= gs
        if not cand:
            return []

    title_tf = index["title_tf"]
    subj_tf = index["subj_tf"]
    scored: list[tuple[float, str, int]] = []
    for idx in cand:
        r = rows[idx]
        if has_filters and not _matches_filters(r, k, rt, lv, sess, yr, tz_norm, src):
            continue
        total = 0.0
        for alts in groups:
            best_alt = 0.0
            for alt in alts:
                if len(alt) == 1:
                    s = _score_token(alt[0], tok_vocabs[alt[0]], idx, index)
                else:
                    parts = [_score_token(t, tok_vocabs[t], idx, index) for t in alt]
                    if all(p > 0.0 for p in parts):
                        s = sum(parts)
                        if _all_in_field(alt, title_tf[idx]):
                            s *= 1.35
                        elif _all_in_field(alt, subj_tf[idx]):
                            s *= 1.2
                    else:
                        s = 0.0
                if s > best_alt:
                    best_alt = s
            total += best_alt
        score = round(total + _KIND_TIE.get(r["kind"], 0.0), 6)
        scored.append((score, r["ts"], idx))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [rows[idx] for _, _, idx in scored]


def _public(r):
    return {k: r[k] for k in _PUBLIC_KEYS}


def search_with_total(q, kind="", rtype="", level="", session="", year="",
                      tz="", source="", sort="rank", limit=20, offset=0) -> tuple[list[dict], int]:
    """Search cloud catalog and return (page_rows, total_matches)."""
    rows = _filtered(q, kind, rtype, level, session, year, tz, source)
    if sort == "recent":
        rows = sorted(rows, key=lambda r: r["ts"], reverse=True)
    total = len(rows)
    page = rows[offset:offset + limit]
    return [_public(r) for r in page], total


def search(q, kind="", rtype="", level="", session="", year="",
           tz="", source="", sort="rank", limit=20, offset=0):
    return search_with_total(
        q, kind, rtype, level, session, year, tz, source, sort, limit, offset
    )[0]


def facets(q="", kind="", rtype="", level="", session="", year="",
           tz="", source=""):
    rows = _filtered(q, kind, rtype, level, session, year, tz, source)
    out = {}
    for col in ("rtype", "level", "sess", "yr", "tz", "kind", "source"):
        counts = {}
        for r in rows:
            v = r[col]
            if v:
                counts[v] = counts.get(v, 0) + 1
        out[col] = [{"value": v, "count": n}
                    for v, n in sorted(counts.items(), key=lambda x: -x[1])[:25]]
    return out


def stats():
    recs = records()
    files = sum(1 for r in recs if r["kind"] == "file")
    remote = sum(1 for r in recs if r["kind"] == "remote")
    links = sum(1 for r in recs if r["kind"] == "link")
    by_src = {}
    for r in recs:
        if r["kind"] == "file":
            by_src[r["source"]] = by_src.get(r["source"], 0) + 1
    return {"files": files, "bytes": 0,
            "by_source": [{"source": k, "n": v} for k, v in sorted(by_src.items())],
            "remote_catalog": remote, "links": links,
            "indexed": len(recs)}


def recent(limit=20):
    recs = sorted(records(), key=lambda r: r["ts"], reverse=True)
    files = [r for r in recs if r["kind"] == "file"][:limit]
    return [{"sha256": r["extra"], "source": r["source"], "url": r["url"],
             "filename": r["title"], "size": 0, "fetched_at": r["ts"]}
            for r in files]


def links(q="", platform="", limit=20):
    rows = _load_json("ibnotes_links.json")
    out = [{"url": r["url"], "host": r.get("host", ""),
            "platform": r.get("platform", ""),
            "direct_file": r.get("direct_file", False)}
           for r in rows
           if q.lower() in r.get("url", "").lower()
           and platform.lower() in r.get("platform", "").lower()]
    return out[:limit]


def mirrors():
    return _load_mirrors()


def resource(sha):
    for r in _load_json("index.json"):
        if r.get("sha256") == sha:
            d = dict(r)
            d["local"] = False
            d["source_url"] = r.get("url", "")
            return d
    return None


def download_url(sha):
    r = resource(sha)
    return r["url"] if r else None


def clear_cache():
    _index.cache_clear()
    records.cache_clear()
