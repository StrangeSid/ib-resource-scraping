"""MCP server: IB resource search for agents. Stdio transport.

Run: ./.venv/bin/python mcp_server.py
Claude Desktop / Cursor / OpenCode: point an MCP stdio entry at this file.
Tools mirror the HTTP API over the hosted index (default: https://ib-scrape.sidevv.xyz)
or local index (STORE/index.sqlite).
"""
import json
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent
PUBLIC_API_URL = "https://ib-scrape.sidevv.xyz"


def _store():
    return Path(os.environ.get("STORE", ROOT / "store"))


def _mdir():
    return Path(os.environ.get("MANIFESTS", ROOT / "manifests"))


def _db():
    con = sqlite3.connect(_store() / "index.sqlite")
    con.row_factory = sqlite3.Row
    return con


def _remote_base():
    """Return remote base URL if remote mode is active, else None."""
    base = os.environ.get("IB_API_BASE")
    if base is not None:
        stripped = base.strip().rstrip("/")
        return stripped if stripped else None
    # Auto-fallback: if local SQLite doesn't exist, connect to hosted public API
    if not (_store() / "index.sqlite").is_file():
        return PUBLIC_API_URL
    return None


def _http_get(path: str, params: dict | None = None):
    base = _remote_base()
    if not base:
        return None
    qs = ("?" + urllib.parse.urlencode({k: v for k, v in params.items() if v != "" and v is not None})) if params else ""
    url = f"{base}{path}{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": "ib-mcp/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"error": "not found"}
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def _sqlite_where(q: str = "", kind: str = "", rtype: str = "", level: str = "",
                  year: str = "", session: str = "", tz: str = "",
                  source: str = "", *, require_q: bool = False) -> tuple[str, list]:
    """Build parameterized SQLite FTS WHERE clause + args matching api/main.py."""
    from ib_scrape.search_util import (
        fts_query, norm_level, norm_rtype, norm_session, norm_tz, norm_year,
    )

    cond: list[str] = []
    args: list = []
    if require_q or q.strip():
        cond.append("fts MATCH ?")
        args.append(fts_query(q))
    if kind.strip():
        cond.append("kind=?")
        args.append(kind.strip().lower())
    rt = norm_rtype(rtype)
    if rt:
        cond.append("rtype=?")
        args.append(rt)
    lv = norm_level(level)
    if lv:
        cond.append("UPPER(level)=?")
        args.append(lv)
    sess = norm_session(session)
    if sess:
        cond.append("LOWER(sess) LIKE ?")
        args.append(f"%{sess}%")
    yr = norm_year(year)
    if yr:
        cond.append("yr=?")
        args.append(yr)
    tz_norm = norm_tz(tz)
    if tz_norm:
        cond.append("UPPER(tz)=?")
        args.append(tz_norm)
    src = source.strip().lower()
    if src:
        cond.append("(LOWER(source)=? OR LOWER(source) LIKE ?)")
        args.extend([src, f"{src}:%"])
    return (" AND ".join(cond) or "1=1"), args


def search(q: str, kind: str = "", limit: int = 20, rtype: str = "",
           level: str = "", year: str = "", session: str = "",
           tz: str = "", source: str = "") -> list:
    """Full-text search. kind: file|remote|link|all(empty). Supports facet filters."""
    if _remote_base():
        res = _http_get("/search", {
            "q": q, "kind": kind, "limit": limit,
            "rtype": rtype, "level": level, "year": year, "session": session,
            "tz": tz, "source": source,
        })
        return res if isinstance(res, list) else []
    from ib_scrape.search_util import FTS_BM25_SQL
    con = _db()
    where, args = _sqlite_where(
        q, kind, rtype, level, year, session, tz, source, require_q=True
    )
    sql = ("SELECT kind,title,url,source,subject,ts,rtype,level,sess,yr,tz"
           f" FROM fts WHERE {where} ORDER BY {FTS_BM25_SQL} LIMIT ?")
    try:
        return [dict(r) for r in con.execute(sql, args + [limit])]
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()


def resource(sha256: str) -> dict:
    """One resource record by sha256."""
    if _remote_base():
        res = _http_get(f"/resources/{sha256}")
        if isinstance(res, dict) and "error" not in res:
            return res
        return {"error": "unknown sha256"}
    r = _db().execute("SELECT * FROM files WHERE sha256=?", (sha256,)).fetchone()
    return dict(r) if r else {"error": "unknown sha256"}


def download_url(sha256: str) -> dict:
    """Get the download / direct redirect URL for a resource."""
    base = _remote_base() or PUBLIC_API_URL
    return {"sha256": sha256, "url": f"{base}/download/{sha256}"}


def stats() -> dict:
    """Index totals."""
    if _remote_base():
        res = _http_get("/stats")
        return res if isinstance(res, dict) else {"files": 0}
    con = _db()
    try:
        f = con.execute("SELECT COUNT(*),COALESCE(SUM(size),0) FROM files").fetchone()
        return {"files": f[0], "bytes": f[1],
                "remote": con.execute("SELECT COUNT(*) FROM remote_files").fetchone()[0],
                "links": con.execute("SELECT COUNT(*) FROM links").fetchone()[0]}
    except sqlite3.OperationalError:
        return {"files": 0}


def mirrors(refresh: bool = False) -> list:
    """Mirror snapshot (ibresources API cache)."""
    if _remote_base():
        res = _http_get("/mirrors", {"refresh": "true"} if refresh else None)
        return res if isinstance(res, list) else []
    f = _mdir() / "mirrors.json"
    return json.loads(f.read_text())["mirrors"] if f.exists() else []


def links(q: str = "", platform: str = "", limit: int = 20) -> list:
    """Search the ibnotes outbound-link graph."""
    if _remote_base():
        res = _http_get("/links", {"q": q, "platform": platform, "limit": limit})
        return res if isinstance(res, list) else []
    try:
        return [dict(r) for r in _db().execute(
            "SELECT url,host,platform FROM links WHERE url LIKE ?"
            " AND platform LIKE ? LIMIT ?", (f"%{q}%", f"%{platform}%", limit))]
    except sqlite3.OperationalError:
        return []


def facets(q: str = "", kind: str = "", rtype: str = "", level: str = "",
           year: str = "", session: str = "", tz: str = "",
           source: str = "") -> dict:
    """Breakdown by resource type, level, session, timezone, year, kind, and source."""
    if _remote_base():
        res = _http_get("/facets", {
            "q": q, "kind": kind, "rtype": rtype, "level": level,
            "year": year, "session": session, "tz": tz, "source": source,
        })
        return res if isinstance(res, dict) else {}
    con = _db()
    where, args = _sqlite_where(q, kind, rtype, level, year, session, tz, source)
    out = {}
    try:
        for col in ("rtype", "level", "sess", "yr", "tz", "kind", "source"):
            out[col] = [{"value": v or "—", "count": n} for v, n in con.execute(
                f"SELECT {col},COUNT(*) FROM fts WHERE {where} AND {col}!=''"
                f" GROUP BY {col} ORDER BY 2 DESC LIMIT 25", args)]
    except sqlite3.OperationalError:
        return {}
    finally:
        con.close()
    return out


mcp = FastMCP("ib-resources")
for _fn in (search, resource, download_url, stats, mirrors, links, facets):
    mcp.tool()(_fn)

if __name__ == "__main__":
    mcp.run()
