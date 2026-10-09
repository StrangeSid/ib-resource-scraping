# DOCS.md — ib-resource-scraping documentation

## 1. What this is

Defragmented local compilation of IB resources (past papers, markschemes,
grade boundaries, question banks, notes) gathered from pirateIB/IBDocs
mirrors, XtremePapers, WordPress sites, and curated link graphs.
Read path: FastAPI (`:8471`) or MCP stdio. Research log: `FINDINGS.md`.

## 2. Architecture

```
sources ──▶ connectors (ib_scrape/connectors/) ──▶ store/
  WP REST        wp_rest.py      blobs/<sha256[:2]/[2:4]/<sha>-<name>
  ibdocs.re      ibdocs.py       index.sqlite (files, remote_files, links, fts)
  pirateib.sh    ibnotes.py      manifests/*.json (committed catalogs)
  mirror API     mirror_api.py
  git host       git_mirror.py
  TFM repos      tfm.py (+ uc_harvest.py clearance)
  Drive          drive.py (DRIVE_API_KEY)
  XtremePapers   xtreme.py
  Dufs hosts     dufs.py (+ uc_harvest.py clearance)
```

Dedup: sha256 content address for bytes; URL primary key for catalog rows.
FTS5 (porter) over all three tables, rebuilt by every `gather` run.

## 3. API reference (`api/main.py`)

Envelope `{status, data, meta}` on every route.

| Route | Params | Notes |
|---|---|---|
| `GET /health` | — | store path + indexed flag |
| `GET /stats` | — | files, bytes, by_source, remote_catalog, links, indexed |
| `GET /search` | `q` (min 2), `kind=file\|remote\|link`, `limit`, `offset` | FTS rank order |
| `GET /resources/{sha}` | — | record + `local` bool |
| `GET /download/{sha}` | — | bytes if local; 404 + `X-Source-URL` if remote-only |
| `GET /mirrors` | `refresh` | cached snapshot or live re-poll |
| `GET /links` | `q`, `platform`, `limit` | ibnotes graph |
| `GET /recent` | `limit` | latest local files |

## 4. MCP server (`mcp_server.py`)

Stdio. Tools `search`, `resource`, `stats`, `mirrors`, `links` over same
index. `STORE`/`MANIFESTS` env overrides. Pinned `mcp<2` (v2 drops FastMCP).

## 5. Cloudflare chain (repo.*/dl.*/mirrors)

Binding = cookies + UA + TLS triple. `requests` alone always 403.
`uc_harvest.harvest()` (SeleniumBase UC headless) solves the managed
challenge; `cffi_session()` replays with chrome TLS impersonation
(`curl_cffi`). TFMClient must NOT overwrite the injected session UA
(regression tested). Clearance is short-lived: harvest, then crawl at once.

## 6. Source notes

- **TFM** (`repo.*`, TinyFileManager 2.5.3): `?p=` paths, row parser
  (`list_full`: dirs/files/sizes/direct links). Title-less dir rows exist.
- **Dufs** (`dl.*`): `?json` per directory
  (`paths: [{path_type, name, mtime, size}]`); `?zip` archives per dir.
- **XtremePapers** (fdscript): needs browser header set; `+`/space
  normalization; root containment (CAIE escape); direct `IB/**/*.pdf` hrefs.
- **WP** (brilliantlearning.in): open `/wp-json/wp/v2/media`; `source_url`
  works directly incl. `_pda` paths. `--wp-index-only` for catalogs.
- **ibdocs.re**: SSR `a.file-row` rows; 404-tolerant session sweep.
- **Village**: AES-encrypted `*.questionData.js`, atob-derived key — needs
  runtime hook (deferred, host throttled).
- **Gated**: RevisionHub (Clerk), RevisionDojo PRO (account), Drive folders
  (API key), Turnstile widgets (manual solve).

## 7. Testing

`requirements-dev.txt` + `pytest tests/ -q`. No live network in tests:
HTTP mocked (`MagicMock` sessions), TestClient for API, tmp stores.
Rules in `CONTRIBUTING.md`.

## 8. Troubleshooting

| Symptom | Cause → fix |
|---|---|
| 403 on CF hosts | stale clearance → re-harvest right before crawl |
| `challenge held` | UC failed this round → retry (flaky), wait, retry |
| UC `SB` import error | `pip install seleniumbase` (trial-only) |
| cffi 403 | UA overwritten or impersonation mismatch → keep harvested UA |
| FTS count off | rebuild: any `gather` run calls `index_fts.build` |
