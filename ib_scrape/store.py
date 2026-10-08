"""Content-addressed local store + sqlite index. Dedup by sha256."""
import hashlib
import json
import sqlite3
import time
from pathlib import Path


class Store:
    def __init__(self, root):
        self.root = Path(root)
        (self.root / "blobs").mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / "index.sqlite")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS files (sha256 TEXT PRIMARY KEY, source TEXT,"
            " url TEXT, filename TEXT, size INTEGER, mime TEXT, fetched_at TEXT,"
            " subject TEXT, level TEXT, rtype TEXT)")

    def save(self, data: bytes, source: str, url: str, filename: str,
             mime: str = "", subject: str = "", level: str = "", rtype: str = ""):
        h = hashlib.sha256(data).hexdigest()
        blob = self.root / "blobs" / h[:2] / h[2:4] / (h + "-" + filename)
        new = not blob.exists()
        if new:
            blob.parent.mkdir(parents=True, exist_ok=True)
            blob.write_bytes(data)
        self.db.execute(
            "INSERT OR IGNORE INTO files VALUES (?,?,?,?,?,?,?,?,?,?)",
            (h, source, url, filename, len(data), mime,
             time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             subject, level, rtype))
        self.db.commit()
        return str(blob), new

    def manifest(self, path):
        rows = self.db.execute("SELECT * FROM files ORDER BY fetched_at").fetchall()
        cols = [d[0] for d in self.db.execute("SELECT * FROM files LIMIT 0").description]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(
            [dict(zip(cols, r)) for r in rows], indent=1))
        return len(rows)
