"""CLI: gather IB resources into the defragmented store."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from ib_scrape import config
from ib_scrape.store import Store
from ib_scrape.connectors import mirror_api, wp_rest, ibnotes, git_mirror


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="store")
    ap.add_argument("--only", default="mirrors,ibnotes,wp",
                    help="comma list: mirrors,ibnotes,wp,git")
    ap.add_argument("--search", default=None, help="WP media search term")
    ap.add_argument("--limit", type=int, default=10, help="max WP downloads")
    ap.add_argument("--manifests", default="manifests")
    args = ap.parse_args()

    store = Store(args.store)
    only = set(args.only.split(","))
    s = requests.Session()
    mdir = Path(args.manifests)
    mdir.mkdir(exist_ok=True)

    if "mirrors" in only:
        snap = mirror_api.snapshot(s)
        (mdir / "mirrors.json").write_text(json.dumps(snap, indent=1))
        print("mirrors:", len(snap["mirrors"]))

    if "ibnotes" in only:
        links = ibnotes.extract(s)
        (mdir / "ibnotes_links.json").write_text(json.dumps(links, indent=1))
        print("ibnotes links:", len(links))

    if "wp" in only:
        n = 0
        for item in wp_rest.iter_media(search=args.search, session=s):
            if n >= args.limit:
                break
            try:
                path, new = wp_rest.download_item(item, store, s)
            except Exception as e:
                print("skip", item.get("slug"), str(e)[:100])
                continue
            n += 1
            print(("new " if new else "dup "), item.get("slug"), path)
        print("wp downloaded:", n)

    if "git" in only:
        print(git_mirror.mirror(Path(args.store) / "git"))

    print("manifest rows:", store.manifest(str(mdir / "index.json")))


if __name__ == "__main__":
    main()
