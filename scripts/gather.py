"""CLI: gather IB resources into the defragmented store."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from ib_scrape.store import Store
from ib_scrape import index_fts
from ib_scrape.connectors import mirror_api, wp_rest, ibnotes, git_mirror, ibdocs, tfm, xtreme


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="store")
    ap.add_argument("--only", default="mirrors,ibnotes,wp",
                    help="comma list: mirrors,ibnotes,wp,git,ibdocs")
    ap.add_argument("--search", default=None, help="WP media search term")
    ap.add_argument("--limit", type=int, default=10, help="max WP downloads")
    ap.add_argument("--ibdocs-year", default="2025")
    ap.add_argument("--ibdocs-session", default="may-2025")
    ap.add_argument("--ibdocs-all", action="store_true")
    ap.add_argument("--xtreme-root", default="./IB/")
    ap.add_argument("--xtreme-max", type=int, default=500)
    ap.add_argument("--cookies", default=None, help="Netscape cookie jar for TFM hosts")
    ap.add_argument("--tfm-host", default="https://repo.pirateib.sh")
    ap.add_argument("--tfm-path", default="")
    ap.add_argument("--wp-index-only", action="store_true",
                    help="catalog WP media without downloading bytes")
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
        if args.wp_index_only:
            recs = [wp_rest.catalog_item(i)
                    for i in wp_rest.iter_media(search=args.search, session=s)]
            (mdir / "wp_media.json").write_text(json.dumps(recs, indent=1))
            print("wp catalog:", len(recs))
        else:
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

    if "ibdocs" in only:
        if args.ibdocs_all:
            recs = ibdocs.crawl_all(session=s)
            (mdir / "ibdocs_all.json").write_text(json.dumps(recs, indent=1))
        else:
            recs = ibdocs.crawl_session(args.ibdocs_year, args.ibdocs_session, s)
            (mdir / f"ibdocs_{args.ibdocs_year}.json").write_text(json.dumps(recs, indent=1))
        print("ibdocs records:", len(recs))

    if "tfm" in only:
        client = tfm.TFMClient(args.tfm_host, args.cookies)
        for sub in client.list(args.tfm_path):
            print("tfm:", sub)

    if "xtreme" in only:
        recs = xtreme.crawl(args.xtreme_root, s, max_pages=args.xtreme_max)
        safe = "".join(c if c.isalnum() else "_" for c in args.xtreme_root).strip("_") or "IB"
        (mdir / f"xtreme_{safe}.json").write_text(json.dumps(recs))
        print("xtreme records:", len(recs))

    print("manifest rows:", store.manifest(str(mdir / "index.json")))
    print("fts rows:", index_fts.build(args.store, args.manifests))


if __name__ == "__main__":
    main()
