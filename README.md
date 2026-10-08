# ib-resource-scraping

One searchable local compilation of IB resources from across the web —
past papers, markschemes, grade boundaries, question banks, notes —
instead of a dozen disconnected mirrors.

Research notes live in [`FINDINGS.md`](FINDINGS.md). History in [`CHANGELOG.md`](CHANGELOG.md).

## How it works

Connectors gather catalog records and files into a content-addressed store
(`store/blobs/` + `store/index.sqlite`, sha256-deduped). A FastAPI backend
serves structured search over everything indexed.

```
sources ──▶ connectors ──▶ store/ ──▶ FTS index ──▶ API (:8471)
  WP REST      wp_rest.py      blobs/      index_fts.py    /search
  ibdocs.re    ibdocs.py       index.sqlite  FTS5 porter   /resources/{sha}
  pirateib.sh  ibnotes.py      manifests/↗ committed       /download/{sha}
  mirrors API  mirror_api.py                               /mirrors /links
  git host     git_mirror.py                               /stats /recent
  TFM repos    tfm.py (needs clearance cookies)
```

> [!NOTE]
> `store/` is local-only (gitignored). `manifests/` (catalog JSON) is committed.

## Quickstart

```sh
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python scripts/gather.py --only mirrors,ibnotes --store store
./.venv/bin/python scripts/gather.py --only wp --search "grade boundaries" --limit 10
./.venv/bin/python scripts/gather.py --only ibdocs --ibdocs-year 2025 --ibdocs-session may-2025
./.venv/bin/python -m uvicorn api.main:app --port 8471
```

```sh
curl "localhost:8471/search?q=grade+boundaries"
curl "localhost:8471/search?q=physics&kind=remote"
curl localhost:8471/recent?limit=5
```

Cloudflare hosts (`repo.*`, `dl.*`, mirrors) need a manual solve first —
export cookies (Netscape format), then:

```sh
./.venv/bin/python scripts/gather.py --only tfm --tfm-host https://repo.pirateib.sh \
  --cookies cookies.txt --tfm-path "IB DOCUMENTS" --limit 20
```

## Tests

```sh
./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/python -m pytest tests/ -q
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md). License: GPLv3 — see [`LICENSE`](LICENSE).
