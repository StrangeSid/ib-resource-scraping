# IB Resource Scraping — Findings

Date: 2026-10-08
Goal: scrape several IB resource sites and store/organise everything in one defragmented local place. Same idea as pirateIB Git ("self-host your own pirateIB").
Status: research only. No code built yet.

## 1. Sources surveyed

| # | URL | Reachable 2026-10-08 | What it is |
|---|-----|----------------------|------------|
| 1 | https://pirateib.sh/ | yes (static, no challenge) | Main hub. Links out to everything else |
| 2 | https://dojo.pirateib.sh/ | NO — Cloudflare challenge (403, `cf-mitigated: challenge`) | RevisionDojo clone/archive frontend |
| 3 | https://git.pirateib.sh/pirateIB | yes (Forgejo, JS-required but listings readable) | 8 repos, self-host model. The template to copy |
| 4 | https://dl.pirateib.sh/DOWNLOAD%20REPO%20-%20ZIPS/ | NO — Cloudflare challenge | Bulk ZIP snapshot (Oct 2025), single-folder downloads |
| 5 | https://village.pirateib.sh/ | NO — Cloudflare challenge | Revision Village style frontend (`village` repo) |
| 6 | https://brilliantlearning.in/ | yes (WordPress) | PYP/MYP/DP + IGCSE/SAT, heavy copy protection |
| 7 | https://ibresources.cc/mirrors2 | NO — dead (empty response / transport error) | Was mirror list |
| 8 | https://ibresources.cc/ | NO — dead (same) | Was mirror hub |
| 9 | https://ibresources.cc/mirrors/ | NO — dead (same) | Was mirror list |
| 10 | https://repo.pirateib.sh/IB%20DOCUMENTS/ | NO — Cloudflare challenge | TinyFileManager file repo |
| 11 | https://repo.pirateib.sh/?p=IB+DOCUMENTS | NO — same host, same challenge expected | Same repo, `?p=` path addressing |
| 12 | https://dl.pirateib.su/IB%20BOOKS/ | NO — challenge expected (`.su` twin of #4) | IB Docs book tree |
| 13 | https://pirateib.sh/ibnotes/ | yes | "Biggest IB Notes Compilation Ever" — curated link list, not a file host |
| 14 | https://repo.pirateib.sh/StudyIB/pages/subjects/page-networks/index.html | NO — Cloudflare challenge | StudyIB static subject pages inside repo |

`.su` ↔ `.sh` migration happened ~Feb 2026 ("Domain migration - su to sh" commits). Treat `pirateib.su` and `pirateib.sh` hostnames as the same infrastructure.

## 2. pirateIB hub (pirateib.sh) — structure

Static site, easy to scrape. Sections found:

- Announcements: Telegram (`telegram.pirateib.sh`), Discord (`discord.pirateib.sh`), `./announcements`
- Main file repos: `dl.pirateib.sh/`, mirror list `ibresources.cc/mirrors2` (now dead)
- HOT items: May 2026 official exam pack (`pirateib.su/m26exampack`), May 2026 grade boundaries PDF under `dl.pirateib.su/IB%20GRADE%20BOUNDARIES/`
- `./resguide/`, `./ibnotes/`, Mortar & Pestle QB (`pestle.pirateib.su`), Marxify exemplars repo (`./marxify/`, TOK/IA/EE) + upload portal (`upload-to-marxify.pirateib.sh`), SME Archive (`smearchive.pirateib.sh`), Village, Dojo
- Self-host: `git.pirateib.sh`, single-folder ZIP snapshot `dl.pirateib.sh/DOWNLOAD%20REPO%20-%20ZIPS/` (Oct 2025; notes say missing SME Archive offline + papers-by-subject)

## 3. pirateIB Git (git.pirateib.sh/pirateIB) — the model to copy

Forgejo instance. 8 public repos:

| Repo | Lang / size / commits | Purpose |
|------|----------------------|---------|
| `pirateib-website` | HTML 94%, 1.6 MiB, 14 commits | Code for pirateib.sh hub + `ibnotes/`, `mypnotes/`, `marxify/`, `resguide/`, `announce/` subpages |
| `pirateib-repo` | PHP 100%, 96 KiB, 7 commits | Self-hosted file repo. TinyFileManager + FrankenPHP on Docker. Serves `repo.pirateib.sh`. `files/` + root `index.php`, `Caddyfile`, `compose.yml`, port 8080 default |
| `pirateib-git` | CSS/Docker, small | Self-host a Forgejo+Codeberg Git clone |
| `village` | JS 81%, 61 MiB, 5 commits | Code for `village.pirateib.su` |
| `rdojo` | JS 99.7%, **748 MiB**, 3 commits | RevisionDojo 1:1 archive (`rev-dojo-archive.pages.dev`). Vite app: `npm install && npm run build && npm run preview` (prod) or `npm run dev`. Roadmap lists scrapers still needed: Videos, Lessons, Exercises, Vocabulary, OnePrep; wants PRO account donations + free AI grading |
| `rdojo-old` | HTML, archived | Previous dojo version |
| `pestle` | HTML/JS/CSS, **528 MiB**, 7 commits | Mortar & Pestle IB QuestionBank (`pestle.pages.dev`). Has `app/`, `assets/`, `OPEN PESTLE - WINDOWS.exe` launcher + `INSTRUCTIONS FOR MAC-LINUX.txt` |
| `svgtopng-cli` | JS | SVG→PNG tool "vibecoded for pirating some books" |

Key quote from `pirateib-repo` README: "Not the same as IB Docs repo — dl.pirateib.su". So `repo.*` (TinyFileManager self-host kit) and `dl.*` (IB Docs tree) are two different corpora. Public hosting needs VPN + domain + Cloudflare reverse proxy; "Anti-scraping measures must also be used to combat aggressive scraper bots"; takedown risk warning.

Practical takeaway: the fastest mirror is `git clone` / ZIP download of these 8 repos via Forgejo (`/archive/master.zip`, `.tar.gz`, `.bundle`). rdojo + pestle alone are ~1.3 GiB — plan disk and LFS accordingly. That already gives hub + QB frontends + self-host kits without any HTML scraping.

## 4. File repos (repo.* / dl.*) — URL + tech patterns

- Stack: TinyFileManager `index.php` at root, path addressing via `?p=` query param, e.g. `repo.pirateib.sh/index.php?p=IB+BOOKS%2FGroup+3+-+Individuals+and+Societies%2FBusiness+Management%2FLevel7+Education`, `?p=Lewwinski+Business+Management`, `?p=ibGenius`, `?p=IB+TEACHER+SUPPORT+MATERIAL`.
- Directory-style URLs also exist: `repo.pirateib.sh/IB%20DOCUMENTS/`, `dl.pirateib.sh/DOWNLOAD%20REPO%20-%20ZIPS/`, `dl.pirateib.su/IB%20BOOKS/`, `dl.pirateib.su/IB%20GRADE%20BOUNDARIES/May%202026%20Grade%20Boundaries%20non-exam%20route.pdf`.
- Static StudyIB tree inside repo: `repo.pirateib.sh/StudyIB/pages/subjects/page-networks/index.html` — crawlable subject-page graph once past the challenge.
- All of `repo.*`, `dl.*`, `dojo.*`, `village.*` sit behind Cloudflare managed challenge (verified `403 cf-mitigated: challenge` with plain curl). Simple `requests`/`curl` scraping will fail. Needs: real browser session (Playwright/Selenium + JS), Cloudflare clearance cookies, session reuse, slow polite crawl, `?p=` enumeration + StudyIB HTML crawl + ZIP-manifest diffing.
- Known corpora names: `IB DOCUMENTS`, `IB BOOKS` (with `Group 3 - Individuals and Societies/Business Management/Level7 Education`), `IB GRADE BOUNDARIES`, `IB TEACHER SUPPORT MATERIAL`, Lewwinski Business Management, ibGenius, `DOWNLOAD REPO - ZIPS` (Oct 2025 snapshot).

## 5. ibnotes (pirateib.sh/ibnotes/) — link aggregator, not a host

- One giant static page: General + per-subject sections (English A L&L/Lit, Bio, Chem, Physics, CS, Maths, BM, Econ, History, Geo, …).
- Links point overwhelmingly to third parties: Google Drive folders/files, Google Docs/Sheets/Slides, Notion, Quizlet, YouTube playlists, blogs/Weebly/Wix/WordPress, Scribd, Overleaf, Spotify podcasts, `repo.pirateib.sh/index.php?p=...`, `ib-academy.nl`, `znotes.org`, `bioninja`, `ibphysics.org`, etc.
- Scraping plan for this source is two-stage: (a) extract + classify every outbound link by platform; (b) per-platform downloaders (Drive export API, Docs export, Notion public pages, Quizlet, YouTube). Expect link-rot and permission-denied links; record HTTP status per link.

## 6. brilliantlearning.in — WordPress, protected

- Taxonomy: IB PYP / MYP (exam schedule, books, past papers, grade boundaries, syllabus+notes, formula booklet, mock papers, global-contexts table, topic-wise/criteria questions) / DP (exam schedule, books, syllabus/subject guide, past papers split HL/SL, mock HL/SL, specimen papers, formula booklet, resources/study-materials, grade boundaries, question banks) + IGCSE (Grade 9/10) + SAT.
- Grade-boundary PDFs are first-class targets: May 2026, Nov 2025, May 2025.
- Protections observed: adblock detector ("Please disable your adblocker"), `Content is protected !!` (copy/right-click guard), `pdfjs-viewer-shortcode` viewer (`.../viewer.php?file=...&...#toolbar=0`), `_pda` protected uploads (`/wp-content/uploads/_pda/...`, i.e. Prevent-Direct-Access style). Tags reference `pirateib`, `doxxib`, `ibdocs`, `revision village`.
- Scraping plan: sitemap + WP JSON (`/wp-json/`) enumeration, category/tag pages, `viewer.php?file=` param extraction for real PDF URLs, cookie-authenticated session for `_pda` paths, polite rate limits. Check `robots.txt`/`ToS` before aggressive crawling.

## 7. ibresources.cc — currently dead

`GET /`, `/mirrors`, `/mirrors2` all return empty / transport error as of 2026-10-08. Was the mirror-list source linked from pirateib.sh. Treat as unavailable; retry later, fall back to Wayback Machine if mirror URLs are needed.

## 8. Implications for our scraper project (no code yet)

1. **Source connectors (one per tech, not one per URL):** (a) Forgejo/Git connector (clone + `/archive/*.zip` + release polling); (b) TinyFileManager connector (`?p=` traversal + file download + checksum); (c) StudyIB static-HTML connector; (d) ibnotes link-graph extractor + per-platform downloaders; (e) WordPress connector (sitemap/wp-json/pdfjs/`_pda`); (f) Cloudflare-session layer shared by b/c + dojo/village frontends.
2. **Biggest blocker is bot protection, not parsing:** `*.pirateib.sh` file/app hosts need browser-based sessions; `ibresources.cc` is down; brilliantlearning needs adblock/JS + auth handling; ibnotes needs Google/Notion/Quizlet/YouTube handlers.
3. **Storage layout (proposal):** `store/<source>/<subject>/<level>/<type>/<sha256>-<filename>` + `metadata.sqlite` (source URL, fetched_at, sha256, size, subject tags, license/risk flag) + per-source manifest JSON. Dedup by hash across `repo.*` vs `dl.*` vs ZIP snapshot vs Git clones — overlap is expected and large.
4. **Sync strategy:** pin Oct 2025 ZIP snapshot as baseline; incremental `?p=` listing diffs + Forgejo commit polling (`pirateib-website` last active 2026-09-17, `pirateib-repo` 2026-09-07); re-check dead `ibresources.cc` mirrors on a timer.
5. **Legal/ToS caution:** pirateIB itself warns about takedowns; keep fetches local/personal, rate-limited, with source attribution and a blocklist. Grade boundaries and official exam packs are the highest-risk items — store metadata + provenance.
6. **Suggested build order:** Git-clone mirror first (biggest instant win, no challenge) → TinyFileManager `?p=` crawler with Cloudflare session → ibnotes link extraction → brilliantlearning WP crawler → dedup index + single search/browse UI (the "defragmented place").

## 9. Open questions

- Do we want full binary mirror (multiple GiB confirmed: rdojo ~900 MiB, pestle 1.1 GiB, rdojo-old 616 MiB, village 125 MiB — see §10) or metadata-first + on-demand download?
- Cloudflare approach: manual clearance-cookie paste vs automated Playwright solver? Headless Chrome alone does NOT pass (§11).
- `_pda`/Drive-private links: skip on 403 or use authenticated personal accounts?
- Village `*.questionData.js` payloads are AES-encrypted (`U2FsdGVkX1...`); key lives in obfuscated `main.js`. Decrypt offline or drive the frontend in a browser?

## 10. Local clone analysis (2026-10-08, tmp clones outside repo)

All 8 `git.pirateib.sh/pirateIB/*` repos clone cleanly over HTTPS with `--depth 1` — no auth, no challenge. Giants are heavy and `--filter=blob:none` is NOT honored (Forgejo fetches full blobs anyway: pestle pulled ~500 MiB post-filter). Sizes on disk:

| Repo | Size | Stack / notes |
|------|------|---------------|
| `pirateib-website` | 4.2 MiB | Static hub. `index.html` (93 lines), `ibnotes/`, `mypnotes/`, `marxify/`, `resguide/`, `announce/`, `assets/`. `robots.txt` = `Allow: /`. Meta keywords confirm lineage: `ibdocs2, IB Documents (2) Team, r/pirateIB`. Commented-out traces: WhatsApp/Instagram links, N25 exam-pack ZIP (`DOWNLOAD REPO - ZIPS/N25 exam pack.zip`, 0.8 GB), Tor mirror (`./tor` + `onion.png`) |
| `pirateib-repo` | 276 KiB | TinyFileManager **v2.5.3** single `files/index.php` (2561 lines). `APP_TITLE='pirateIB Repository'`, `$use_auth=false`, `$global_readonly=true`, `$root_path='.'`, `$exclude_items=('*.php','sitemap.xml','robots.txt','download.html')`, upload cap 5 GB / 2 MB chunks. Path addressing = `$_GET['p']` → `fm_clean_path($p)` (line 348-356) — crawler pattern: enumerate `?p=<path>`, parse listing table, recurse. `compose.yml` = `dunglas/frankenphp:latest`, `SERVER_NAME=:8080`, `./files:/app/public:ro,noexec,nosuid,nodev`, `no-new-privileges`, `cap_drop: ALL + NET_BIND_SERVICE`, 1 CPU / 512 MiB. `Caddyfile`: `admin off`, `:8080 root /app/public + php_server` |
| `pirateib-git` | 260 KiB | `docker-compose.yml` = Forgejo `codeberg.org/forgejo/forgejo:12` + `custom-conf`/`custom-public` mounts, `network_mode: container:wireguard`, sidecar `cloudflare/cloudflared tunnel run --token … --protocol http2`. Public self-host = WireGuard + Cloudflare Tunnel |
| `svgtopng-cli` | 204 KiB | Real tool, not a stub. Batch SVG→PNG via headless Chromium (Playwright), browser-faithful render (not native rasterizer). `node dist/cli.js`, `-o/-W/-H/-t/-m/-f/-b/-c/-z/-j` flags, default height 1400, 16k px cap. Used "for pirating some books" (screenshot-style raster path — relevant if we hit SVG-only books) |
| `village` | 125 MiB | `src/` = 243 files: ~200 `*.questionData.js` webpack chunks + fonts + `index.html` + `main.js`. Payloads are **AES-encrypted** (`(self.webpackChunkrevisionvillage...).push([[1002],{1002:V=>{V.exports="U2FsdGVkX19..."}}})` — OpenSSL `Salted__` base64). `main.js` is obfuscated. `index.html`: canonical `https://village.pirateib.su/`, keywords `revision town, revision village, pirateib village, revision village crack, revision village free, revision village archive`, description "pirateIB Village is a free archive of Revision Village IB resources. Formerly called Revision Town." |
| `pestle` | 1.1 GiB | `app/index.html` + `app/index.js` (QB UI: topic combine, markscheme/report modals, PDF-gen buttons), `assets/jsonqb/` = **22 files, 498 MiB**: `Biology/Chemistry/Physics 2025 QB merged+split`, legacy per-subject (`Biology/Chemistry/Physics/Business/Econ/ESS/Geo/History/Psych/SEHS/CS/DT/Digital Society/Math AA+AI QB.json`) + `README.txt` (topic-prefix notes for Psych/Geo/History syllabus splits). QB record = `{Question: HTML with base64-embedded PNGs, …}` — base64 images explain size. `assets/uploads/` = 24 MiB user uploads. `OPEN PESTLE - WINDOWS.exe` + `INSTRUCTIONS FOR MAC-LINUX.txt` = offline launcher |
| `rdojo` | ~916 MiB, checkout incomplete (reset timed out) | Vite + React 19 + Tailwind 4 + react-router + `@react-pdf-viewer` + fuse.js + jszip (`packages/central`, `public`, `src`). Treat as present-but-unverified; re-clone with big timeout when needed |
| `rdojo-old` | 616 MiB | Same Vite/React shape (`revisiondojo3`, `render.yaml`, `Dockerfile`). Archived predecessor |

`resguide/index.html` (110 lines) is the best machine-readable corpus map — exact `dl.*` paths: `DOWNLOAD REPO - ZIPS/` (Oct 2025) + `Full repo (you might not need this)/` (Feb 2025), `IB OFFICIAL EE EXEMPLARS/`, `IB QUESTIONBANKS/` v4 (`4. Fourth Edition - TOPIC`, ≤2018) / v5 (`5. Fifth Edition - TOPIC`, `5. Fifth Edition - PAPER/HTML`, 2018-2022) / v6 (`6. Sixth Edition - 2025 Sciences`, Econ/Chem/Bio/Phy), `StudyIB/`, `ThinkIB/`, `SaveMyExams - Notes/`, `smearchive.pages.dev`, `revisiontown2024.pages.dev`, `pestle.pages.dev` (v5+v6) + `pestle-ib.firebaseapp.com` (v4), plus paywall-unlock tooling list (LibSTC/Anna's/Sci-Hub/LibGen, Scribd/Studocu/Issuu/CourseHero/Chegg downloaders).

## 11. Browser probe (Chrome DevTools, headless)

- `GET repo.pirateib.sh/` in real Chromium → Cloudflare managed challenge, French locale ("Vérification de sécurité en cours … se protéger contre les bots malveillants"), Ray ID `a47586f49f36702d`. 30 s wait: **no auto-resolve**, no Turnstile widget to click. Same `cf-mitigated: challenge` as curl for `dl.*`, `repo.*`, `dojo`, `village`, `arrib.cc`, `dynamicrepo.sbs`, `sufferingrepo.me`.
- Conclusion: file/app hosts need either a non-headless session with clearance cookies (manual paste → reuse in crawler) or a solver (Playwright stealth + Turnstile handling). Budget this as its own work item; curl/`requests` alone will never pass.
- Counterpoint: static Pages frontends are OPEN — `pestle.pages.dev` (QB landing, links `app/index.html`) fetched fine with plain HTTP. Prefer `*.pages.dev` / `*.firebaseapp.com` origins over challenged `*.pirateib.sh` where content overlaps.

## 12. ibresources.cc — HTML dead, API alive

- `/`, `/mirrors`, `/mirrors2` still empty via curl (origin down or blocking datacenter UAs).
- Wayback capture 2026-05-05 of `/mirrors2` recovered the mirror table + pointed at the JSON API. **Live API works today**: `GET https://ibresources.cc/api/v2/mirrors` (deprecated → successor `/api/v3/mirrors`, `Link: </api/v3/mirrors>; rel="successor-version"`) and `/api/v3/mirrors` both return 200 JSON with per-mirror `status` + `uptime`.
- Current v3 list (all `online`): `dl.pirateib.su`, `dl.pirateib.sh`, `arrib.cc` (IBDocs Backup 2), `repo.pirateib.su`, `repo.pirateib.sh`, `dynamicrepo.sbs`, `sufferingrepo.me` (uptimes 99.7–100). **DoxxIB (`doxxib.pp.ua`) is gone** — present in May Wayback, absent from v2+v3 today, and the host returns empty (dead). Drop it; keep polling the API for list changes.
- Crawler use: poll `/api/v3/mirrors` for discovery/health instead of scraping HTML; probe each mirror with a real browser session (all non-`dl`/`repo` mirrors are Cloudflare-challenged too).

## 13. Selenium vs Cloudflare — trials run 2026-10-08 (venv in tmp, selenium 4.50.0, Mac Chrome)

- Sources read: SO Q68289474 (HeadlessChrome UA string is the tell; recipes = undetected-chromedriver, selenium-stealth, uc+stealth combo), birdeatsbug 2025-11 guide (persistent profile, UA/header rotation, proxy pools, explicit waits + cookie reuse, official API preferred; Puppeteer/Playwright/Scrapy/BrowserStack as alternates). agentskillsforall `selenium-skill` checked: LambdaTest E2E-testing skill (locators, waits, POM, Grid) — **nothing Cloudflare-specific, NOT installed** (repo stays code-free per plan).
- Trial A (vanilla headless=new + stealth flags + clean UA, 20 s wait) → stuck on FR managed challenge. Trial B (+`selenium-stealth`: languages/vendor/platform/WebGL spoof, 30 s) → stuck on EN challenge (Ray `a475938eee37bd92`); stealth patch applied (locale flipped) but challenge persists. Trial C (headed, no headless flags) → stuck too.
- Verdict: **browser fingerprint is not the binding constraint — IP/network reputation or TLS fingerprint likely is**. uc last release Feb 2024 (stale vs current Chrome) — low expected value, skipped. Remaining levers in order: (1) persistent profile + one manual solve, reuse `cf_clearance` cookies in crawler; (2) residential/ISP IP instead of flagged ASN; (3) SeleniumBase UC mode (actively maintained uc successor) + Xvfb headed; (4) token-solving API as last resort (paid, ToS-sensitive).
- Trial scripts kept outside repo (`sel-test/cf_trial.py`, `cf_trialB.py` + screenshots); NOT committed.

## 14. More APIs found (no browser needed)

- **brilliantlearning WP REST fully open**: `/wp-json/wp/v2/types` lists posts/pages/media/menu-items/categories/tags — public, no auth. `/wp-json/wp/v2/media?search=…&per_page=N` returns full records incl `source_url`, `mime_type`, `filesize`, `slug`. M2026/N2025/MYP grade-boundary PDFs all enumerated this way.
- **`_pda` protection is theater**: `source_url` values like `/wp-content/uploads/_pda/2026/07/M2026-Grade-Boundaries.pdf` return **HTTP 200 + full bytes via plain curl** (verified 1,132,272 bytes, no cookie). WP connector = REST enumerate → direct GET. No Selenium, no login.
- **rdojo content paths** (from `src/routes/*/…tsx`): PDFs live at `dl.pirateib.sh/Revision%20Dojo%20Archive/{predictedpapers/<slug>.pdf, cheatsheets/<id>.pdf, exemplars/<id>.pdf}` — exact bulk-download targets once past challenge. Jojo AI backend = `${CHAT_API}/api/{create,chat,followup-questions,chat/update-title,presigned-url,file}` but `CHAT_API` comes only from `VITE_CHAT_API_URL` env (no default anywhere in repo) — no public AI endpoint found; skip.
- **pestle runtime URLs**: `app/index.js` builds QB JSON `baseUrl` from `window.location` (localhost vs prod switch) + dead `https://link-r2-dev/<filename>` placeholder (R2 migration stub); Discord webhook POST at line 296 = report-broken feature (do not touch). QB data itself already local via git clone — no API needed.
- **Dead ends**: `revisionvillage-archive.pages.dev` returns empty (gone; use git clone instead). `CHAT_API` has no discoverable default. DoxxIB stays dead.

## 15. Wider hunt (2026-10-08) + API backend built

- **ibdocs.re + dl.ibdocs.re (NEW, open, no challenge)**: IB Docs 3 Team catalog, TanStack SSR. Routes `/past-papers/{year}/{session}` (2010–2026, may/november + more-papers), `/past-papers-by-subject`, `/exemplars`, `/team`. Folder rows link `/IB PAST PAPERS - YEAR/...` tree (same layout as dl hosts). Mirror: `ibresources.lol/mirror`. CC BY-NC-ND footer. Connector `ibdocs.py` crawls SSR `a.file-row` rows; proof: 60 records (may-2025) → FTS.
- **ibresources.cc back in Google index** (bot allowlist or cache) with new entries: Mirror Browser (single UI over all mirrors), XtremePapers, Revision Hub, OpenSlum, `ibresources.in` (mirror list, now HTTP 451), Tor mirror `pirateib.sh/tor`. Direct curl still 403.
- **More repo suffixes** (from indexed TFM pages + mirrors): `repo.*`: sh/su/ua/me/sbs/org (one page variant lists …/io). `repo.pirateib.me` dead (000). Reddit r/IBO adds: `ibcalculator.com` (200), `citecount.com/ib-resources`, `marksyib.com` (410 gone).
- **Revision Dojo Archive tree** (via indexed TFM): root folders `Revision Dojo Archive` (upd 2026-04-06), `Revision Village` + `RV - Other Materials` (upd 2026-08-30); inside: `cheatsheets/`, `exemplars/`, `predictedpapers/` (+ `index.html` 112 B). N25 papers path prefix seen: `dl.pirateib.sh/…/2025 Examination Session/…N25/`.
- **Backend API v1 built** (`api/main.py`, FastAPI :8471, `{status,data,meta}` envelope): `/health`, `/stats`, `/search` (FTS5 porter, kind=file|remote|link), `/resources/{sha}`, `/download/{sha}`, `/mirrors` (?refresh), `/links`. FTS rows: 684 (4 local + 60 ibdocs remote + 620 links). All 8 endpoints curl-verified 200. Frontend UI + MCP/skill = later.
