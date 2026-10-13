# SKILL.md — ib-resources agent skill

Use when finding, downloading, or organizing International Baccalaureate (IB) resources
(past papers, markschemes, grade boundaries, question banks, subject notes, textbooks),
or querying the unified IB resource index.

Public hosted endpoint: `https://ib-scrape.sidevv.xyz` (zero local setup needed).
Local self-hosted fallback: `http://localhost:8471`.

## Quick routes (HTTP API)

Default base URL: `https://ib-scrape.sidevv.xyz` (or `localhost:8471` locally).

| Need | Command |
|---|---|
| Search resources | `curl "https://ib-scrape.sidevv.xyz/search?q=physics&rtype=paper&level=hl&limit=10"` |
| Resource breakdown (facets) | `curl "https://ib-scrape.sidevv.xyz/facets?q=math"` |
| Resource metadata | `curl "https://ib-scrape.sidevv.xyz/resources/<sha256>"` |
| Download file (follows 307 redirect) | `curl -L "https://ib-scrape.sidevv.xyz/download/<sha256>" -o resource.pdf` |
| Mirrors status & uptime | `curl "https://ib-scrape.sidevv.xyz/mirrors"` |
| Curated link graph (Google Drive / MEGA) | `curl "https://ib-scrape.sidevv.xyz/links?q=drive&platform=google_drive"` |
| Index totals & recent items | `curl "https://ib-scrape.sidevv.xyz/stats"`, `curl "https://ib-scrape.sidevv.xyz/recent"` |
| Health check | `curl "https://ib-scrape.sidevv.xyz/health"` |

All API responses follow the envelope schema: `{status, data, meta}`.
Resource kinds: `remote` (cataloged upstream), `file` (indexed blob), `link` (curated link graph).
Available facets / filters:
- `rtype`: `paper`, `markscheme`, `textbook`, `notes`, `syllabus`, `boundaries`, `specimen`, `exemplar`, `report`
- `level`: `HL`, `SL`, `MYP`, `CORE`
- `session`: `may`, `november`
- `year`: e.g. `2024`, `2023`, `2018`

## Agentic use: MCP server

Run stdio MCP server directly (connects to hosted public API by default):
```sh
IB_API_BASE=https://ib-scrape.sidevv.xyz python mcp_server.py
```

Tools exposed:
- `search(q, kind="", limit=20, rtype="", level="", year="", session="")`
- `facets(q="", kind="")`
- `resource(sha256)`
- `download_url(sha256)`
- `stats()`
- `mirrors(refresh=False)`
- `links(q="", platform="", limit=20)`

## Local caching & personal store

Pull files from public index into personal local `store/` via CLI:

```sh
# Search and pull top matching files to personal store:
python scripts/pull.py --search "Physics HL Paper 1 May 2024" --limit 3

# Pull single file by SHA:
python scripts/pull.py --sha <sha256>

# Dry run search without downloading:
python scripts/pull.py --search "Grade Boundaries" --dry-run
```

## Running local instance

```sh
# Start local API on port 8471
./.venv/bin/python -m uvicorn api.main:app --port 8471

# Local web UI pointing to hosted API or local server
open ui/index.html   # append ?api=https://ib-scrape.sidevv.xyz
```

## Policies

- **Catalog-first:** index metadata for everything, stream/fetch bytes on demand.
- **Store stays local:** `store/blobs/` is gitignored. Committed catalogs live in `manifests/`.
- **Offline test suite:** every connector and endpoint must have mock-backed unit tests.
