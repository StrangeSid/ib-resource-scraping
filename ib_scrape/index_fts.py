"""Unified search index: FTS5 over local files + remote catalog + link graph."""
import json
import sqlite3
from pathlib import Path


def build(store_root, manifests_dir):
    db = sqlite3.connect(Path(store_root) / "index.sqlite")
    db.execute("CREATE TABLE IF NOT EXISTS remote_files (url TEXT PRIMARY KEY,"
               " source TEXT, name TEXT, size TEXT, year TEXT, session TEXT,"
               " parent TEXT, fetched_at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS links (url TEXT PRIMARY KEY,"
               " host TEXT, platform TEXT, direct_file INTEGER)")
    # ingest manifests
    mdir = Path(manifests_dir)
    ib = mdir / "ibnotes_links.json"
    if ib.exists():
        db.executemany("INSERT OR IGNORE INTO links VALUES (?,?,?,?)",
                       [(l["url"], l["host"], l["platform"], int(l["direct_file"]))
                        for l in json.loads(ib.read_text())])
    import time
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for cat in sorted(mdir.glob("ibdocs_*.json")):
        db.executemany(
            "INSERT OR IGNORE INTO remote_files VALUES (?,?,?,?,?,?,?,?)",
            [(r["url"], "ibdocs", r["name"], r["size"], str(r.get("year", "")),
              r.get("session", ""), r.get("parent", ""), now)
             for r in json.loads(cat.read_text())])
    db.execute("DROP TABLE IF EXISTS fts")
    db.execute("CREATE VIRTUAL TABLE fts USING fts5(kind, title, url, source,"
               " subject, extra, tokenize='porter')")
    db.execute("INSERT INTO fts(kind,title,url,source,subject,extra)"
               " SELECT 'file',filename,url,source,subject,rtype FROM files")
    db.execute("INSERT INTO fts(kind,title,url,source,subject,extra)"
               " SELECT 'remote',name,url,source,year||' '||session,''"
               " FROM remote_files")
    db.execute("INSERT INTO fts(kind,title,url,source,subject,extra)"
               " SELECT 'link',url,url,platform,host,'' FROM links")
    db.commit()
    n = db.execute("SELECT COUNT(*) FROM fts").fetchone()[0]
    db.close()
    return n
