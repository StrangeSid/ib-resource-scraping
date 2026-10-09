"""MCP server: IB resource search for agents. Stdio transport.

Run: ./.venv/bin/python mcp_server.py
Claude Desktop / opencode: point an MCP stdio entry at this file.
Tools mirror the HTTP API (api/main.py) over the same index.
"""
import json
import os
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent


def _store():
    return Path(os.environ.get("STORE", ROOT / "store"))


def _mdir():
    return Path(os.environ.get("MANIFESTS", ROOT / "manifests"))


def _db():
    con = sqlite3.connect(_store() / "index.sqlite")
    con.row_factory = sqlite3.Row
    return con


def search(q: str, kind: str = "", limit: int = 20) -> list:
    """Full-text search. kind: file|remote|link|all(empty)."""
    con = _db()
    sql = ("SELECT kind,title,url,source,subject FROM fts WHERE fts MATCH ?"
           + (" AND kind=?" if kind else "")
           + " ORDER BY rank LIMIT ?")
    try:
        return [dict(r) for r in
                con.execute(sql, ([q] + ([kind] if kind else []) + [limit]))]
    except sqlite3.OperationalError:
        return []


def resource(sha256: str) -> dict:
    """One local file record by sha256."""
    r = _db().execute("SELECT * FROM files WHERE sha256=?", (sha256,)).fetchone()
    return dict(r) if r else {"error": "unknown sha256"}


def stats() -> dict:
    """Index totals."""
    con = _db()
    try:
        f = con.execute("SELECT COUNT(*),COALESCE(SUM(size),0) FROM files").fetchone()
        return {"files": f[0], "bytes": f[1],
                "remote": con.execute("SELECT COUNT(*) FROM remote_files").fetchone()[0],
                "links": con.execute("SELECT COUNT(*) FROM links").fetchone()[0]}
    except sqlite3.OperationalError:
        return {"files": 0}


def mirrors() -> list:
    """Mirror snapshot (ibresources API cache)."""
    f = _mdir() / "mirrors.json"
    return json.loads(f.read_text())["mirrors"] if f.exists() else []


def links(q: str = "", platform: str = "", limit: int = 20) -> list:
    """Search the ibnotes outbound-link graph."""
    try:
        return [dict(r) for r in _db().execute(
            "SELECT url,host,platform FROM links WHERE url LIKE ?"
            " AND platform LIKE ? LIMIT ?", (f"%{q}%", f"%{platform}%", limit))]
    except sqlite3.OperationalError:
        return []


mcp = FastMCP("ib-resources")
for _fn in (search, resource, stats, mirrors, links):
    mcp.tool()(_fn)

if __name__ == "__main__":
    mcp.run()
