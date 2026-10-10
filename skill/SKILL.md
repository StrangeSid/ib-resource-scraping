# SKILL.md — ib-resources agent skill

Use when the user asks to find, download, or organize IB resources
(past papers, markschemes, grade boundaries, question banks, notes),
or to operate the ib-resource-scraping repo.

## Quick routes

| Need | Command |
|---|---|
| Search index | `curl "localhost:8471/search?q=<terms>&kind=file\|remote\|link"` |
| Record detail | `curl localhost:8471/resources/<sha256>` |
| Download bytes | `curl localhost:8471/download/<sha256> -o file` |
| Mirrors health | `curl localhost:8471/mirrors` (`?refresh=true` to re-poll) |
| Link graph | `curl "localhost:8471/links?q=&platform=google_drive"` |
| Stats/recent | `curl localhost:8471/stats`, `curl localhost:8471/recent` |

Start API: `./.venv/bin/python -m uvicorn api.main:app --port 8471` (repo root).
All responses: `{status, data, meta}`. Kinds: `file` (local bytes),
`remote` (cataloged, fetch on demand), `link` (ibnotes graph).

## Gather (catalog-first; bytes only with explicit `--limit`)

```sh
./.venv/bin/python scripts/gather.py --only wp --wp-index-only
./.venv/bin/python scripts/gather.py --only ibdocs --ibdocs-all
./.venv/bin/python scripts/gather.py --only xtreme --xtreme-root "./IB/" --xtreme-max 3000
./.venv/bin/python scripts/gather.py --only tfm --uc-harvest --tfm-crawl --limit 0   # catalog only
./.venv/bin/python scripts/gather.py --only dufs --uc-harvest --dufs-host https://dl.pirateib.sh
```

Cloudflare chain: UC harvest → curl_cffi chrome-TLS → crawl.
Trial-only deps (`seleniumbase`, `curl_cffi`) live in `.venv`, NOT requirements.
MCP alternative: `./.venv/bin/python mcp_server.py` (stdio; tools mirror the API).
Wire it with `mcp.example.json` (copy + fix paths). Note: single search hits
arrive unwrapped (object, not one-item array).

## Policies (hard)

- Catalog-first. Proof-scale bytes only. No bulk binary crawls without sign-off.
- `store/` never committed. `manifests/` always committed with code.
- New connector → mocked-HTTP tests. New endpoint → TestClient test.
- Research notes → FINDINGS.md. History → CHANGELOG.md (backdated).
