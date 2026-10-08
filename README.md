# ib-resource-scraping

Defragmented local compilation of IB resources from across the web.
Research in `FINDINGS.md`. Code here applies it.

## Layout

- `ib_scrape/` — connectors + content-addressed store
- `scripts/gather.py` — CLI entry
- `manifests/` — committed JSON (what exists, where, hashes)
- `store/` — local only (gitignored): `blobs/` + `index.sqlite`

## Use

```sh
pip install -r requirements.txt
python scripts/gather.py --only mirrors,ibnotes --store store
python scripts/gather.py --only wp --search "grade boundaries" --limit 10
python scripts/gather.py --only wp --limit 50   # bulk media crawl
```

Cloudflare hosts (`repo.*`, `dl.*`, mirrors) need clearance cookies first:
solve once in a normal browser, export cookies (Netscape format),
then `python scripts/gather.py --only tfm --cookies cookies.txt`.
