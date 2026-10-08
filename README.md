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
python scripts/gather.py --only ibdocs --ibdocs-year 2025 --ibdocs-session may-2025
```

## API (backend first; UI + MCP later)

```sh
uvicorn api.main:app --port 8471
curl "localhost:8471/search?q=grade+boundaries"
curl "localhost:8471/search?q=physics&kind=remote"
curl localhost:8471/stats
curl "localhost:8471/links?platform=google_drive"
curl localhost:8471/mirrors
```

Structured JSON everywhere: `{status, data, meta}`.

Cloudflare hosts (`repo.*`, `dl.*`, mirrors) need clearance cookies first:
solve once in a normal browser, export cookies (Netscape format),
then `python scripts/gather.py --only tfm --cookies cookies.txt`.
