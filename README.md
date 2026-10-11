# ib-resource-scraping

One searchable local index of IB resources from across the web —
past papers, markschemes, grade boundaries, question banks, notes —
instead of a dozen disconnected mirrors.

> [!NOTE]
> Catalog-first: metadata for everything, bytes on demand or proof-scale.
> `store/` stays local (gitignored); `manifests/` catalogs are committed.

## Sources

| Source | Connector | Access |
|---|---|---|
| pirateIB repo (`repo.*`, TinyFileManager) | `tfm.py` + `uc_harvest.py` | UC auto-solve, then plain crawl |
| IBDocs repo (`dl.*`, Dufs) | `dufs.py` | Same UC chain, `?json` API |
| XtremePapers (fdscript) | `xtreme.py` | Open, direct PDF links |
| ibdocs.re catalog | `ibdocs.py` | Open, SSR rows |
| brilliantlearning.in | `wp_rest.py` | Open WP REST (incl. `_pda` URLs) |
| pirateib.sh/ibnotes | `ibnotes.py` | Open link graph (623 links) |
| Mirror health | `mirror_api.py` | Open JSON API |
| Google Drive | `drive.py` | `DRIVE_API_KEY` |
| pirateIB git | `git_mirror.py` | Open clone |

Research log: [`FINDINGS.md`](FINDINGS.md) · Agent skill: [`skill/SKILL.md`](skill/SKILL.md) ·
Full docs: [`DOCS.md`](DOCS.md) · History: [`CHANGELOG.md`](CHANGELOG.md)

## Quickstart

```sh
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

Gather catalogs (no bytes):

```sh
./.venv/bin/python scripts/gather.py --only mirrors,ibnotes --store store
./.venv/bin/python scripts/gather.py --only wp --wp-index-only
./.venv/bin/python scripts/gather.py --only ibdocs --ibdocs-all
./.venv/bin/python scripts/gather.py --only xtreme --xtreme-root "./IB/" --xtreme-max 3000
./.venv/bin/python scripts/gather.py --only dufs --uc-harvest --dufs-host https://dl.pirateib.sh
```

Download proof-scale bytes:

```sh
./.venv/bin/python scripts/gather.py --only wp --search "grade boundaries" --limit 10
```

Cloudflare hosts (auto-solve needs trial-only `seleniumbase` + `curl_cffi`):

```sh
./.venv/bin/python scripts/gather.py --only tfm --uc-harvest \
  --tfm-host https://repo.pirateib.sh --tfm-crawl --limit 0
# or manual solve + exported cookies
./.venv/bin/python scripts/gather.py --only tfm --tfm-host https://repo.pirateib.sh \
  --cookies cookies.txt --tfm-path "IB DOCUMENTS"
```

## API

```sh
./.venv/bin/python -m uvicorn api.main:app --port 8471
./.venv/bin/python mcp_server.py   # stdio, for agents
```

| Route | Example |
|---|---|
| `GET /search?q=&kind=` | `curl "localhost:8471/search?q=grade+boundaries"` |
| `GET /resources/{sha}` | record + `local` flag |
| `GET /download/{sha}` | bytes, or 404 + `X-Source-URL` |
| `GET /mirrors` | `?refresh=true` to re-poll |
| `GET /links?q=&platform=` | ibnotes graph |
| `GET /stats`, `/recent`, `/health` | index totals, latest, liveness |

Every response: `{status, data, meta}`.

## Tests

```sh
./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/python -m pytest tests/ -q   # 49 green, no live network
```

## Deploy

```sh
docker build -t ib-resources . && docker compose up -d   # :8471
kubectl apply -f k8s/app.yaml                             # cluster
PROJECT=myproj ./scripts/deploy_gcloud.sh                 # Cloud Run
```

Static UI anywhere (Vercel: `ui/` as root): point it at an API with
`?api=https://your-api` once (saved to localStorage).

See [`CONTRIBUTING.md`](CONTRIBUTING.md). License: GPLv3 — see [`LICENSE`](LICENSE).
