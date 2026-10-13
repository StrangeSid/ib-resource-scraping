# ib-resource-scraping

One searchable index of **53,000+ IB resources** across the web — past papers, markschemes, grade boundaries, question banks, textbooks, and notes — instead of a dozen disconnected mirrors.

Hosted live index: **[https://ib-scrape.sidevv.xyz](https://ib-scrape.sidevv.xyz)**  
Web interface: **[https://ib-scrape.sidevv.xyz/](https://ib-scrape.sidevv.xyz/)**

> [!TIP]
> **Catalog-first architecture**: `ib-scrape.sidevv.xyz` serves as the public, maintained central index. AI agents and local instances can query the index freely, while file downloads stream on-demand or save into your personal local storage.

---

## 🚀 Public Hosted API

The API is deployed and ready to query with zero local setup:

**Base URL:** `https://ib-scrape.sidevv.xyz`

### Quick API Routes

| Endpoint | Method | Params | Description |
|---|---|---|---|
| `/search` | `GET` | `q`, `rtype`, `level`, `session`, `year`, `limit` | Ranked full-text search across 53k+ resources |
| `/facets` | `GET` | `q`, `kind` | Resource aggregation counts (types, levels, sessions) |
| `/resources/{sha}` | `GET` | — | Metadata record for a specific resource SHA-256 |
| `/download/{sha}` | `GET` | — | HTTP 307 redirect straight to upstream file host |
| `/stats` | `GET` | — | Catalog size, source counts, and index health |
| `/mirrors` | `GET` | `refresh=true` | Mirror liveness and uptime status |
| `/links` | `GET` | `q`, `platform`, `limit` | Outbound Google Drive / MEGA resource graph |
| `/recent` | `GET` | `limit` | Most recently indexed items |
| `/health` | `GET` | — | Service status and runtime mode |

### Example Queries

```sh
# 1. Search for physics past papers (HL)
curl "https://ib-scrape.sidevv.xyz/search?q=physics&rtype=paper&level=hl&limit=5"

# 2. Inspect available resource types and levels for mathematics
curl "https://ib-scrape.sidevv.xyz/facets?q=mathematics"

# 3. Get resource metadata
curl "https://ib-scrape.sidevv.xyz/resources/a877c616794ed4e8979adb32e5be3520815f637418b66edb1f2eebc73cb18c69"

# 4. Download file (follows HTTP 307 redirect directly to mirror)
curl -L "https://ib-scrape.sidevv.xyz/download/a877c616794ed4e8979adb32e5be3520815f637418b66edb1f2eebc73cb18c69" -o boundaries.pdf

# 5. Check mirror statuses
curl "https://ib-scrape.sidevv.xyz/mirrors"
```

All responses follow the JSON envelope: `{"status": "ok", "data": ..., "meta": ...}`.

---

## 🤖 Agentic Use: MCP Server & Skill

The hosted API is designed directly for AI coding assistants and agents (Claude Desktop, Cursor, OpenCode, Windsurf, Claude Code).

### 1. Install Agent Skill (OpenCode / Claude)

Install the skill with one command:

```sh
mkdir -p ~/.config/opencode/skills/ib-resources
curl -sSL https://raw.githubusercontent.com/StrangeSid/ib-resource-scraping/master/skill/SKILL.md \
  -o ~/.config/opencode/skills/ib-resources/SKILL.md
```

The skill gives agents instant access to search syntax, filter facets, and download shortcuts.

### 2. Configure MCP Server

The MCP server connects to `https://ib-scrape.sidevv.xyz` by default without requiring any local database files.

#### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "ib-resources": {
      "command": "python3",
      "args": ["/path/to/ib-resource-scraping/mcp_server.py"],
      "env": {
        "IB_API_BASE": "https://ib-scrape.sidevv.xyz"
      }
    }
  }
}
```

#### OpenCode (`opencode.json` / `~/.config/opencode/opencode.json`)

```json
{
  "mcpServers": {
    "ib-resources": {
      "command": "python3",
      "args": ["/path/to/ib-resource-scraping/mcp_server.py"],
      "env": {
        "IB_API_BASE": "https://ib-scrape.sidevv.xyz"
      }
    }
  }
}
```

#### Cursor (`.cursor/mcp.json` or Settings → MCP)

Add new stdio command:
- **Command:** `python3`
- **Args:** `/path/to/ib-resource-scraping/mcp_server.py`
- **Env:** `IB_API_BASE=https://ib-scrape.sidevv.xyz`

#### Claude Code CLI

```sh
claude mcp add ib-resources -- python3 /path/to/ib-resource-scraping/mcp_server.py
```

### MCP Tools Available

- `search(q, rtype, level, year, session, limit)` — Full-text search over papers, markschemes, and notes.
- `facets(q, kind)` — Breakdown of resource counts across types and syllabus levels.
- `resource(sha256)` — Retrieve metadata by SHA-256 hash.
- `download_url(sha256)` — Get the direct download URL for a file.
- `mirrors(refresh)` — Check health and uptime of IB mirrors.
- `links(q, platform, limit)` — Search curated Google Drive / MEGA links.
- `stats()` — Check index counts and source totals.

---

## 💾 Personal Downloads & Local Instances

You can use the public API as your index while saving downloads into your personal local storage.

### Pull files to local store (`scripts/pull.py`)

```sh
# Search hosted API and download top matches to your personal local store:
python scripts/pull.py --search "Physics HL Paper 1 May 2024" --limit 3

# Pull single file by SHA:
python scripts/pull.py --sha a877c616794ed4e8979adb32e5be3520815f637418b66edb1f2eebc73cb18c69

# Search without downloading (dry run):
python scripts/pull.py --search "Chemistry SL" --dry-run
```

Files are verified and saved into content-addressed blobs at `store/blobs/` and registered into local SQLite index.

### Point local Web UI to hosted API

Open the web interface locally and point it directly to the hosted API:

```sh
open ui/index.html   # append ?api=https://ib-scrape.sidevv.xyz
```

The UI persists your API base in `localStorage`.

### Run local self-hosted API (optional)

If you wish to run a self-hosted API server with a local SQLite index:

```sh
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m uvicorn api.main:app --port 8471
```

---

## 📦 Data Sources

| Source | Connector | Access Method |
|---|---|---|
| pirateIB repo (`repo.*`, TinyFileManager) | `tfm.py` + `uc_harvest.py` | Headless Turnstile clearance + plain crawl |
| IBDocs repo (`dl.*`, Dufs) | `dufs.py` | Same Turnstile chain, `?json` API |
| XtremePapers (fdscript) | `xtreme.py` | Open direct PDF links |
| ibdocs.re catalog | `ibdocs.py` | Open SSR rows |
| brilliantlearning.in | `wp_rest.py` | Open WP REST (includes `_pda` files) |
| pirateib.sh/ibnotes | `ibnotes.py` | Curated link graph (623 links) |
| Mirror health | `mirror_api.py` | Realtime status JSON API |
| Google Drive | `drive.py` | Google Drive API key |
| pirateIB git | `git_mirror.py` | Open git clone |

---

## 🧪 Testing & Verification

The test suite runs entirely offline using mocked HTTP calls:

```sh
./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/python -m pytest tests/ -q
# 55 passed in <10s
```

---

## 📚 Documentation & Research

- **Research findings & mirror history:** [`FINDINGS.md`](FINDINGS.md)
- **Detailed architecture & connector docs:** [`DOCS.md`](DOCS.md)
- **Agent skill instructions:** [`skill/SKILL.md`](skill/SKILL.md)
- **Contributing guidelines:** [`CONTRIBUTING.md`](CONTRIBUTING.md)
- **Release notes:** [`CHANGELOG.md`](CHANGELOG.md)
