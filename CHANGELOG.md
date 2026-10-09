# Changelog

All notable changes, backdated to the commit that introduced them.
Dates are commit dates (`git log --format="%ad" --date=short`).

## Unreleased

- Dropped `ibdocs_2025.json` (60/60 URLs inside `ibdocs_all.json`), purged pycache.

## 2026-10-09 — Tests to 29 green (`6261052`)

- Gaps filled: xtreme containment/max-pages/search/download, drive
  confirm-token download, TFM download.

## 2026-10-09 — ibdocs sweep log, village throttle note (`82366fb`)

- Village host throttled (~1.5 KB/s, 880K per 10 min) — clone infeasible now; retry later.

## 2026-10-09 — ibdocs full catalog (`60a669a`)

- ibdocs full sweep 2010–2026 (`--ibdocs-all`): 622 catalog records, FTS 5750.

## 2026-10-09 — Robustness + policy (`56fea6c`)

- `mirror_api.snapshot` retries with backoff + v2 fallback; mirror API flapping
  (connection resets) — cached snapshot preserved on failure.
- Bytes policy: catalog-first, proof-scale bytes only.

## 2026-10-09 — Cleanup round 1 (`814557c`)

- Cleanup: compacted manifests (−49k lines), dead-code purge, sanitize pass.

## 2026-10-09 — MCP server + 21 tests (`de83dc1`)

- MCP server (`mcp_server.py`, stdio): search/resource/stats/mirrors/links tools
  over the same index. Pinned `mcp<2` (v2 renamed FastMCP, breaks API).
- Village re-clone throttled (host slow, tmp purged) — decrypt probe deferred.

## 2026-10-08 — WP catalog, Drive connector, decrypt probe (`6b8c2a1`)

- `gather --only wp --wp-index-only`: 4504-record WP catalog without bytes (FTS 5188).
- `drive.py`: folder/file ID parse, export URLs, API-key listing, confirm-token download.
- Village probe: payloads decrypted in-page by bundled CryptoJS; key derived via
  `atob()` at call site — needs runtime hook to dump plaintext (next).

## 2026-10-08 — Docs, license, `/recent`, TFM wiring (`e5a64f1`)

- `GET /recent` (latest local files), `stats.indexed` total, `gather --only tfm`
  with `--cookies/--tfm-host/--tfm-path`, fixed TFM `?p=` subpath parsing.
- `LICENSE` (GPLv3), `CONTRIBUTING.md`, README refresh (create-readme skill).

## 2026-10-08 — Tests: 15 pytest covering store, connectors, FTS index, API (`921ba07`)

- Added `tests/`: `test_store`, `test_connectors` (mocked HTTP), `test_index`, `test_api` (TestClient).
- Added `requirements-dev.txt` (`pytest`, `httpx`).

## 2026-10-08 — FINDINGS §15: wider hunt + API v1 notes (`8579076`)

- Documented ibdocs.re catalog, new mirror suffixes, Dojo archive tree, API v1 endpoints.

## 2026-10-08 — Backend API v1 (`eee84b2`)

- Added `api/main.py` (FastAPI): `/health`, `/stats`, `/search` (FTS5), `/resources/{sha}`,
  `/download/{sha}`, `/mirrors`, `/links`. Envelope `{status, data, meta}`.
- Added `ib_scrape/connectors/ibdocs.py` + `ib_scrape/index_fts.py`; `gather.py` gains
  `--only ibdocs` and rebuilds the FTS index on every run.
- Proof: 60 may-2025 records indexed; 684 FTS rows; all endpoints curl-verified.

## 2026-10-08 — Gather pipeline + proof run (`3c1c920`)

- Added `ib_scrape/` (config, store, 4 connectors), `scripts/gather.py`, manifests.
- Proof: 7 mirrors snapshotted, 623 ibnotes links, 4 WP PDFs downloaded with sha256 dedup.

## 2026-10-08 — FINDINGS: selenium trials, WP REST bypass (`836ffd0`)

- Selenium 4.50.0 trials (headless/stealth/headed) all stuck on Cloudflare challenge.
- WP REST `source_url` leaks direct PDF URLs; `_pda` returns 200 to plain curl.

## 2026-10-08 — FINDINGS: tmp clone analysis, browser probe, mirror API (`663ba56`)

- All 8 pirateIB git repos cloned; TFM v2.5.3 `?p=` pattern; village AES payloads;
  pestle 498 MiB QB JSON; live mirror API `/api/v3/mirrors`.

## 2026-10-08 — Initial research (`98c2fad`)

- `FINDINGS.md`: surveyed 14 URLs across pirateIB, ibresources.cc, brilliantlearning.in.
