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

**Cloud (search + direct downloads, e.g. `ib-scrape.sidevv.xyz`):**
API runs in cloud catalog mode — read-only search over committed
`manifests/`, downloads 307-redirect to source hosts. No disk, no keys.

```sh
# from repo root (FastAPI preset auto-detects api/index.py)
vercel --prod
# dashboard: Settings → Domains → add ib-scrape.sidevv.xyz
# DNS: CNAME ib-scrape -> cname.vercel-dns.com
```

Same domain serves UI (`/`) + API (`/search`, `/stats`, …).
`CLOUD_MODE=1` forces cloud; `CLOUD_MODE=0` forces local.
`GET /mirrors?refresh=true` is 403 in cloud (self-host for live polling).

**Self-host (your own searchable downloads):** clone, gather bytes, serve.

```sh
git clone https://github.com/StrangeSid/ib-resource-scraping && cd ib-resource-scraping
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python scripts/gather.py --only mirrors,ibnotes --store store
./.venv/bin/python scripts/gather.py --only wp --search "grade boundaries" --limit 10
CLOUD_MODE=0 ./.venv/bin/python -m uvicorn api.main:app --port 8471
# UI: open http://localhost:8471/ , or point the cloud UI at it once with ?api=http://localhost:8471
```

Docker / k8s / Cloud Run (local-mode images, persistent disk):

```sh
docker build -t ib-resources . && docker compose up -d   # :8471
kubectl apply -f k8s/app.yaml                             # cluster
PROJECT=myproj ./scripts/deploy_gcloud.sh                 # Cloud Run
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md). License: GPLv3 — see [`LICENSE`](LICENSE).
