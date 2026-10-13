# DOCS.md — ib-resource-scraping documentation

## 1. What this is

Defragmented compilation of International Baccalaureate (IB) resources
(past papers, markschemes, grade boundaries, question banks, subject notes, textbooks)
gathered from pirateIB/IBDocs mirrors, XtremePapers, WordPress sites, and curated link graphs.

- **Centralized Public Index:** Hosted and continuously maintained at `https://ib-scrape.sidevv.xyz`.
- **Personal Local Storage:** Local instances point to the public index for metadata while downloading and storing personal files locally in content-addressed storage.
- **Agentic Access:** FastMCP stdio server and OpenCode/Claude agent skills point directly to the index.

## 2. Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │  Hosted Public Index / Catalog               │
                    │  https://ib-scrape.sidevv.xyz (Vercel)       │
                    │  • Read-only search & facets over manifests  │
                    │  • Direct 307 redirects to upstream files    │
                    └──────────────────────┬───────────────────────┘
                                           │
           ┌───────────────────────────────┼──────────────────────────────┐
           ▼                               ▼                              ▼
┌──────────────────────┐        ┌──────────────────────┐       ┌──────────────────────┐
│  AI Agents (MCP)     │        │  Local Storage CLI   │       │  Local Self-Host     │
│  mcp_server.py       │        │  scripts/pull.py     │       │  api/main.py (:8471) │
│  • search, facets    │        │  • pulls files by    │       │  • SQLite + FTS5     │
│  • resources, links  │        │    SHA or search     │       │  • blobs/ storage    │
│  • download URLs     │        │  • dedups into blobs │       │  • optional mirror   │
└──────────────────────┘        └──────────────────────┘       └──────────────────────┘
```

- **Content Addressing:** SHA-256 content address for local binary blobs (`store/blobs/ab/cd/<sha>-<filename>`).
- **Catalog Dedup:** Canonical URL primary keys for remote catalog entries.
- **Classification Engine:** `ib_scrape/classify.py` detects resource type (`rtype`), difficulty level (`level`), examination session (`sess`), year (`yr`), and timezone (`tz`).

## 3. Public API reference (`https://ib-scrape.sidevv.xyz`)

All responses adhere to the standard JSON envelope: `{status, data, meta}`.

| Route | Method | Query Parameters | Description |
|---|---|---|---|
| `/health` | `GET` | — | Liveness check, mode (`cloud` vs `local`), indexed status |
| `/stats` | `GET` | — | File count, storage bytes, source breakdown, remote catalog count |
| `/search` | `GET` | `q` (min 2), `kind`, `rtype`, `level`, `session`, `year`, `sort`, `limit`, `offset` | Ranked full-text search across 53,000+ resources |
| `/facets` | `GET` | `q`, `kind` | Resource aggregation counts for `rtype`, `level`, `sess`, `yr`, `tz` |
| `/resources/{sha}` | `GET` | — | Metadata record for a specific resource SHA-256 |
| `/download/{sha}` | `GET` | — | HTTP 307 redirect to source file (cloud mode) or binary stream (local) |
| `/mirrors` | `GET` | `refresh=true` | Status and uptime metrics across mirror hosts |
| `/links` | `GET` | `q`, `platform`, `limit` | Curated outbound link graph (Google Drive, MEGA, etc.) |
| `/recent` | `GET` | `limit` | Most recently indexed resource entries |

### Search filters:
- `kind`: `remote` (upstream file), `file` (indexed blob), `link` (external repository/drive)
- `rtype`: `paper`, `markscheme`, `textbook`, `notes`, `syllabus`, `boundaries`, `specimen`, `exemplar`, `report`
- `level`: `HL`, `SL`, `MYP`, `CORE`
- `session`: `may`, `november`
- `sort`: `rank` (FTS relevancy) or `recent` (chronological)

## 4. MCP Server (`mcp_server.py`)

Stdio transport for Claude Desktop, Cursor, OpenCode, and Windsurf.

- **Hosted Remote Mode (default when local DB absent):** Queries `https://ib-scrape.sidevv.xyz` via lightweight stdlib HTTP requests. Zero local files or database required.
- **Local SQLite Mode:** Operates on local `STORE/index.sqlite` when present.
- **Configuration Override:** Set `IB_API_BASE` in the environment to point MCP to any custom instance.

Exposed Tools:
1. `search(q, kind, limit, rtype, level, year, session)`: Multi-facet full-text search.
2. `facets(q, kind)`: Get counts by resource type and syllabus level.
3. `resource(sha256)`: Retrieve metadata for a resource.
4. `download_url(sha256)`: Get the download/redirect URL for retrieving files.
5. `stats()`: Catalog size and source counts.
6. `mirrors(refresh)`: Mirror availability status.
7. `links(q, platform, limit)`: Query outbound cloud storage links.

## 5. Local storage & pull CLI (`scripts/pull.py`)

Save files from the public index into personal local storage:

```sh
# Pull by SHA-256:
python scripts/pull.py --sha a877c616794ed4e8979adb32e5be3520815f637418b66edb1f2eebc73cb18c69

# Search and download matching files into local store:
python scripts/pull.py --search "Physics HL Paper 1" --limit 5

# Preview matches without downloading:
python scripts/pull.py --search "Chemistry May 2024" --dry-run
```

Files are verified by content hash and saved to `store/blobs/<h[:2]>/<h[2:4]>/<h>-<filename>`.

## 6. Cloudflare bypass & connector chain

For scraping protected mirrors directly (`scripts/gather.py`):
1. **Binding:** `cf_clearance` cookies + User-Agent + TLS fingerprint matching.
2. **Harvest:** `uc_harvest.harvest()` launches headless SeleniumBase UC to clear Turnstile / managed challenges.
3. **Replay:** `cffi_session()` impersonates Chrome TLS profile via `curl_cffi` using harvested credentials.
4. **Crawl:** `tfm.py` parses TinyFileManager directories; `dufs.py` queries `?json` API on Dufs hosts.

## 7. Testing standards

- Run test suite: `pytest tests/ -q` (55 passing tests).
- Mock all HTTP interactions (`unittest.mock.patch` / `MagicMock`).
- No live network calls allowed in unit tests.
- tmp directories used for filesystem isolation.
