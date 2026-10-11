"""Unified search index: FTS5 over local files + remote catalog + link graph."""
import json
import re
import sqlite3
import time
from pathlib import Path

from .classify import classify

YEAR_RE = re.compile(r"(19|20)\d{2}")
SESSION_MONTH = {"may": "05", "november": "11", "may-2025": "05"}


def ts_of(url="", year="", session="", explicit=""):
    """Best-effort ISO date for sorting. Explicit > year+session > URL year."""
    if explicit and re.match(r"\d{4}-\d{2}", explicit):
        return explicit[:10]
    if re.fullmatch(r"\d{4}", str(year or "")):
        m = "01"
        for key, mon in SESSION_MONTH.items():
            if key in str(session or "").lower():
                m = mon
                break
        return f"{year}-{m}-01"
    m = YEAR_RE.search(f"{url}")
    return f"{m.group(0)}-01-01" if m else ""


def build(store_root, manifests_dir):
    db = sqlite3.connect(Path(store_root) / "index.sqlite")
    db.execute("CREATE TABLE IF NOT EXISTS remote_files (url TEXT PRIMARY KEY,"
               " source TEXT, name TEXT, size TEXT, year TEXT, session TEXT,"
               " parent TEXT, fetched_at TEXT, ts TEXT)")
    cols = [r[1] for r in db.execute("PRAGMA table_info(remote_files)")]
    if "ts" not in cols:
        db.execute("ALTER TABLE remote_files ADD COLUMN ts TEXT DEFAULT ''")
    db.execute("CREATE TABLE IF NOT EXISTS links (url TEXT PRIMARY KEY,"
               " host TEXT, platform TEXT, direct_file INTEGER)")

    def put(rows):
        db.executemany(
            "INSERT INTO remote_files(url,source,name,size,year,session,parent,"
            "fetched_at,ts) VALUES (?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(url) DO UPDATE SET ts=excluded.ts", rows)

    mdir = Path(manifests_dir)
    ib = mdir / "ibnotes_links.json"
    if ib.exists():
        db.executemany("INSERT OR IGNORE INTO links VALUES (?,?,?,?)",
                       [(l["url"], l["host"], l["platform"], int(l["direct_file"]))
                        for l in json.loads(ib.read_text())])
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for cat in sorted(mdir.glob("ibdocs_*.json")):
        put([(r["url"], "ibdocs", r["name"], r["size"], str(r.get("year", "")),
              r.get("session", ""), r.get("parent", ""),
              now, ts_of(r["url"], r.get("year"), r.get("session")))
             for r in json.loads(cat.read_text())])
    wp = mdir / "wp_media.json"
    if wp.exists():
        put([(r["url"], "brilliantlearning", r["name"], r.get("size", ""),
              r.get("year", ""), "", "", now,
              ts_of(r["url"], r.get("year"), explicit=r.get("ts", "")))
             for r in json.loads(wp.read_text()) if r.get("url")])
    for cat in sorted(mdir.glob("xtreme_*.json")):
        put([(r["url"], "xtreme", r["name"], "", "", "", r.get("dirpath", ""),
              now, ts_of(r["url"], explicit=r.get("ts", "")))
             for r in json.loads(cat.read_text())])
    for cat in sorted(mdir.glob("tfm_*.json")):
        put([(r["url"], r.get("source", "tfm"), r["name"], r.get("size", ""),
              "", "", r.get("parent", ""), now, ts_of(r["url"]))
             for r in json.loads(cat.read_text())])
    for cat in sorted(mdir.glob("dufs_*.json")):
        put([(r["url"], r.get("source", "dufs"), r["name"], r.get("size", ""),
              "", "", r.get("parent", ""), now,
              ts_of(r["url"], explicit=r.get("ts", "")))
             for r in json.loads(cat.read_text())])
    db.execute("DROP TABLE IF EXISTS fts")
    db.execute("CREATE VIRTUAL TABLE fts USING fts5(kind, title, url, source,"
               " subject, extra, ts, rtype, level, sess, yr, tz,"
               " tokenize='porter')")

    def cls(title, url, subject):
        c = classify(title, url, subject)
        return c["rtype"], c["level"], c["session"], c["year"], c["tz"]

    rows = []
    for title, url, source, subject, extra, ts in db.execute(
            "SELECT filename,url,source,subject,sha256,fetched_at FROM files"):
        c = classify(title, url, subject)
        rows.append(("file", title, url, source, subject, extra,
                     ts_of(url) or ts, c["rtype"], c["level"],
                     c["session"], c["year"], c["tz"]))
    for url, source, name, size, year, session, parent, _f, ts in db.execute(
            "SELECT url,source,name,size,year,session,parent,fetched_at,ts"
            " FROM remote_files"):
        subj = f"{year} {session} {parent}"
        c = classify(name, url, subj)
        rows.append(("remote", name, url, source, subj, "",
                     ts, c["rtype"], c["level"],
                     c["session"] or session, c["year"] or year, c["tz"]))
    for url, host, plat in db.execute("SELECT url,host,platform FROM links"):
        rows.append(("link", url, url, plat, host, "", "", "other", "", "", "", ""))
    db.executemany("INSERT INTO fts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    db.commit()
    n = db.execute("SELECT COUNT(*) FROM fts").fetchone()[0]
    db.close()
    return n


def prefix_query(q):
    """Every term becomes a prefix match: 'Histor' hits 'History'."""
    toks = re.findall(r"[A-Za-z0-9]+", q or "")
    return " ".join(t + "*" for t in toks) or '""'
