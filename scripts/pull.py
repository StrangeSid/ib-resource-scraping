"""CLI: pull resources from public/remote IB API into local store.

Usage:
  # Pull a single file by sha256 into local store/
  python scripts/pull.py --sha a877c616794ed4e8979adb32e5be3520815f637418b66edb1f2eebc73cb18c69

  # Search hosted API and pull matching resources into personal local store:
  python scripts/pull.py --search "Grade Boundaries" --limit 5

  # Search without downloading (dry run):
  python scripts/pull.py --search "Physics HL May 2024" --dry-run

  # Pull from a custom self-hosted or staging instance:
  python scripts/pull.py --api http://localhost:8471 --search "Math"
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ib_scrape.store import Store

DEFAULT_API = "https://ib-scrape.sidevv.xyz"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "ib-pull/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_bytes(url: str, user_agent: str = "Mozilla/5.0") -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def pull_sha(api: str, sha: str, store: Store) -> bool:
    print(f"Fetching metadata for {sha[:12]}...")
    try:
        meta_res = fetch_json(f"{api}/resources/{sha}")
        item = meta_res.get("data", {})
    except Exception as e:
        print(f"Error fetching metadata: {e}")
        item = {}

    filename = item.get("filename") or f"{sha}.pdf"
    source = item.get("source", "remote-api")
    url = item.get("url") or f"{api}/download/{sha}"
    subject = item.get("subject", "")
    level = item.get("level", "")
    rtype = item.get("rtype", "")

    dl_url = f"{api}/download/{sha}"
    print(f"Downloading from {dl_url}...")
    try:
        data = download_bytes(dl_url)
    except Exception as e:
        print(f"Download failed: {e}")
        return False

    blob_path, is_new = store.save(
        data,
        source=source,
        url=url,
        filename=filename,
        subject=subject,
        level=level,
        rtype=rtype,
    )
    status = "new" if is_new else "exists"
    print(f"[{status}] saved {len(data)} bytes -> {blob_path}")
    return True


def pull_search(api: str, query: str, store: Store, limit: int = 5,
                rtype: str = "", level: str = "", dry_run: bool = False) -> int:
    params = {"q": query, "limit": limit}
    if rtype:
        params["rtype"] = rtype
    if level:
        params["level"] = level
    qs = urllib.parse.urlencode(params)
    search_url = f"{api}/search?{qs}"
    print(f"Searching {api} for: '{query}'...")
    try:
        res = fetch_json(search_url)
        hits = res.get("data", [])
    except Exception as e:
        print(f"Search request failed: {e}")
        return 0

    if not hits:
        print("No resources found matching query.")
        return 0

    print(f"Found {len(hits)} results:")
    for i, h in enumerate(hits, 1):
        title = h.get("title", "untitled")
        kind = h.get("kind", "")
        h_rtype = h.get("rtype", "")
        h_level = h.get("level", "")
        tags = " ".join(filter(None, [h_rtype, h_level]))
        tag_str = f" [{tags}]" if tags else ""
        print(f"  {i}. {title}{tag_str} ({kind})")

    if dry_run:
        print("\nDry run mode; skipped downloads.")
        return len(hits)

    saved = 0
    for i, h in enumerate(hits, 1):
        url = h.get("url", "")
        title = h.get("title", f"resource-{i}")
        if not url:
            continue
        print(f"\n[{i}/{len(hits)}] Downloading {title}...")
        try:
            data = download_bytes(url)
            blob_path, is_new = store.save(
                data,
                source=h.get("source", "search"),
                url=url,
                filename=title,
                subject=h.get("subject", ""),
                level=h.get("level", ""),
                rtype=h.get("rtype", ""),
            )
            saved += 1
            print(f"  -> saved {len(data)} bytes to {blob_path}")
        except Exception as e:
            print(f"  -> download error: {e}")

    print(f"\nDone: {saved}/{len(hits)} downloaded to {store.root}")
    return saved


def main():
    parser = argparse.ArgumentParser(description="Pull IB resources from public index into local store")
    parser.add_argument("--api", default=os.environ.get("IB_API_BASE", DEFAULT_API),
                        help=f"IB API base URL (default: {DEFAULT_API})")
    parser.add_argument("--store", default="store", help="Local store directory (default: store)")
    parser.add_argument("--sha", default="", help="Resource sha256 to pull")
    parser.add_argument("--search", default="", help="Search query to pull matching resources")
    parser.add_argument("--limit", type=int, default=5, help="Max items to download when searching (default: 5)")
    parser.add_argument("--rtype", default="", help="Filter search by resource type (paper, markscheme, etc.)")
    parser.add_argument("--level", default="", help="Filter search by level (HL, SL, etc.)")
    parser.add_argument("--dry-run", action="store_true", help="Search and list without downloading")

    args = parser.parse_args()
    api = args.api.rstrip("/")
    store = Store(args.store)

    if args.sha:
        pull_sha(api, args.sha, store)
    elif args.search:
        pull_search(api, args.search, store, limit=args.limit,
                    rtype=args.rtype, level=args.level, dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
