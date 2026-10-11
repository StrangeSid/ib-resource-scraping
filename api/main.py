"""Local IB resource API. Structured JSON. Read-only v1.

Run: uvicorn api.main:app --port 8471  (from repo root, STORE env optional)
Future: frontend UI, MCP/skill wrapper (see FINDINGS.md).
"""
import json
import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent.parent
STORE = Path(os.environ.get("STORE", ROOT / "store"))
MDIR = Path(os.environ.get("MANIFESTS", ROOT / "manifests"))

app = FastAPI(title="ib-resources", version="0.5.0")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET"],
    max_age=86400,
)


def db():
    con = sqlite3.connect(STORE / "index.sqlite")
    con.row_factory = sqlite3.Row
    return con


def ok(data, **meta):
    return {"status": "ok", "data": data, "meta": meta}


@app.get("/health")
def health():
    return ok({"store": str(STORE), "indexed": (STORE / "index.sqlite").exists()})


@app.get("/stats")
def stats():
    con = db()
    try:
        files = con.execute("SELECT COUNT(*), COALESCE(SUM(size),0) FROM files").fetchone()
        by_src = [dict(r) for r in con.execute(
            "SELECT source, COUNT(*) n FROM files GROUP BY source")]
        remote = con.execute("SELECT COUNT(*) FROM remote_files").fetchone()[0]
        links = con.execute("SELECT COUNT(*) FROM links").fetchone()[0]
    except sqlite3.OperationalError:
        return ok({"files": 0, "bytes": 0})
    return ok({"files": files[0], "bytes": files[1], "by_source": by_src,
               "remote_catalog": remote, "links": links,
               "indexed": files[0] + remote + links})


@app.get("/recent")
def recent(limit: int = 20):
    con = db()
    try:
        rows = [dict(r) for r in con.execute(
            "SELECT sha256,source,url,filename,size,fetched_at FROM files"
            " ORDER BY fetched_at DESC LIMIT ?", (limit,))]
    except sqlite3.OperationalError:
        rows = []
    return ok(rows, limit=limit, count=len(rows))


@app.get("/search")
def search(q: str = Query(..., min_length=2),
           kind: str = Query("", pattern="^(file|remote|link|)$"),
           sort: str = Query("rank", pattern="^(rank|recent)$"),
           rtype: str = "", level: str = "", session: str = "", year: str = "",
           limit: int = 20, offset: int = 0):
    from ib_scrape.index_fts import prefix_query
    con = db()
    order = "rank" if sort == "rank" else "ts DESC, rank"
    cond, args = ["fts MATCH ?"], [prefix_query(q)]
    for col, val in (("kind", kind), ("rtype", rtype), ("level", level),
                     ("sess", session), ("yr", year)):
        if val:
            cond.append(f"{col}=?")
            args.append(val)
    sql = ("SELECT kind,title,url,source,subject,extra,ts,rtype,level,sess,yr,tz,"
           " rank FROM fts WHERE " + " AND ".join(cond)
           + f" ORDER BY {order} LIMIT ? OFFSET ?")
    try:
        rows = [dict(r) for r in con.execute(sql, args + [limit, offset])]
    except sqlite3.OperationalError:
        rows = []
    return ok(rows, query=q, kind=kind or "all", sort=sort,
              limit=limit, offset=offset, count=len(rows))


@app.get("/facets")
def facets(q: str = Query("", max_length=200),
           kind: str = Query("", pattern="^(file|remote|link|)$")):
    from ib_scrape.index_fts import prefix_query
    con = db()
    base, args = "1=1", []
    if q.strip():
        base, args = "fts MATCH ?", [prefix_query(q)]
    if kind:
        base += " AND kind=?"
        args.append(kind)
    out = {}
    try:
        for col in ("rtype", "level", "sess", "yr", "tz", "kind"):
            out[col] = [{"value": v or "—", "count": n} for v, n in con.execute(
                f"SELECT {col},COUNT(*) FROM fts WHERE {base} AND {col}!=''"
                f" GROUP BY {col} ORDER BY 2 DESC LIMIT 25", args)]
    except sqlite3.OperationalError:
        pass
    return ok(out, query=q, kind=kind or "all")


@app.get("/resources/{sha}")
def resource(sha: str):
    con = db()
    r = con.execute("SELECT * FROM files WHERE sha256=?", (sha,)).fetchone()
    if not r:
        raise HTTPException(404, "unknown sha256")
    d = dict(r)
    d["local"] = blob_path(d["sha256"]) is not None
    return ok(d)


@app.get("/download/{sha}")
def download(sha: str):
    con = db()
    r = con.execute("SELECT * FROM files WHERE sha256=?", (sha,)).fetchone()
    if not r:
        raise HTTPException(404, "unknown sha256")
    p = blob_path(r["sha256"])
    if not p:
        raise HTTPException(404, "not downloaded locally",
                            headers={"X-Source-URL": r["url"]})
    return FileResponse(p, filename=r["filename"])


def blob_path(sha):
    hits = sorted((STORE / "blobs" / sha[:2] / sha[2:4]).glob(sha + "-*"))
    return str(hits[0]) if hits else None


@app.get("/mirrors")
def mirrors(refresh: bool = False):
    f = MDIR / "mirrors.json"
    if refresh:
        from ib_scrape.connectors import mirror_api
        import requests
        snap = mirror_api.snapshot(requests.Session())
        f.write_text(json.dumps(snap, indent=1))
        return ok(snap["mirrors"], refreshed=True, api=snap.get("_api"))
    if not f.exists():
        raise HTTPException(404, "no mirror snapshot; use ?refresh=true")
    return ok(json.loads(f.read_text())["mirrors"], refreshed=False)


@app.get("/links")
def links(q: str = "", platform: str = "", limit: int = 20):
    con = db()
    try:
        rows = [dict(r) for r in con.execute(
            "SELECT url,host,platform,direct_file FROM links"
            " WHERE url LIKE ? AND platform LIKE ? LIMIT ?",
            (f"%{q}%", f"%{platform}%", limit))]
    except sqlite3.OperationalError:
        rows = []
    return ok(rows, query=q, platform=platform or "all", count=len(rows))


ui_dir = ROOT / "ui"
if ui_dir.is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=ui_dir, html=True), name="ui")
