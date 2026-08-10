<h1 align="center">SRURL - Simple Recon URL v1.0.0</h1>

<p align="center">
  URL extraction and discovery tool for OSINT and reconnaissance workflows
</p>

<p align="center">
<a href="README.md"><img alt="Português" src="https://img.shields.io/badge/%F0%9F%87%A7%F0%9F%87%B7_Portugu%C3%AAs-757575?style=for-the-badge"></a>
<a href="README_EN.md"><img alt="English" src="https://img.shields.io/badge/%F0%9F%87%BA%F0%9F%87%B8_English-1E88E5?style=for-the-badge"></a>
<a href="README_ES.md"><img alt="Español" src="https://img.shields.io/badge/%F0%9F%87%AA%F0%9F%87%B8_Espa%C3%B1ol-757575?style=for-the-badge"></a>
</p>

<h1 align="center">
  <a href="#"><img src="./assets/img/banner.png" width="600px" alt="Simple Recon URL"></a>
</h1>


<p align="center">
<a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.10+-1E88E5?style=for-the-badge&logo=python&logoColor=white"></a>
<a href="#"><img alt="Version" src="https://img.shields.io/badge/Version-1.0.0-2E7D32?style=for-the-badge&logo=semanticrelease&logoColor=white"></a>
<a href="#"><img alt="Linux" src="https://img.shields.io/badge/Linux-supported-EF6C00?style=for-the-badge&logo=linux&logoColor=white"></a>
<a href="#"><img alt="macOS" src="https://img.shields.io/badge/macOS-supported-00838F?style=for-the-badge&logo=apple&logoColor=white"></a>
</p>

<p align="center">
<a href="https://github.com/osintbrazuca/SimpleReconURL/blob/master/LICENSE"><img alt="License" src="https://img.shields.io/github/license/osintbrazuca/SimpleReconURL?style=for-the-badge&color=1E88E5&logo=opensourceinitiative&logoColor=white"></a>
<a href="https://github.com/osintbrazuca/SimpleReconURL/graphs/contributors"><img alt="Contributors" src="https://img.shields.io/github/contributors-anon/osintbrazuca/SimpleReconURL?style=for-the-badge&color=2E7D32&logo=github&logoColor=white"></a>
<a href="https://github.com/osintbrazuca/SimpleReconURL/issues"><img alt="Open issues" src="https://img.shields.io/github/issues-raw/osintbrazuca/SimpleReconURL?style=for-the-badge&color=EF6C00&logo=github&logoColor=white"></a>
<a href="https://github.com/osintbrazuca/SimpleReconURL/discussions"><img alt="Discussions" src="https://img.shields.io/github/discussions/osintbrazuca/SimpleReconURL?style=for-the-badge&color=6A1B9A&logo=github&logoColor=white"></a>
<a href="https://github.com/osintbrazuca/SimpleReconURL/network/members"><img alt="Forks" src="https://img.shields.io/github/forks/osintbrazuca/SimpleReconURL?style=for-the-badge&color=00838F&logo=github&logoColor=white"></a>
<a href="https://github.com/osintbrazuca/SimpleReconURL/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/osintbrazuca/SimpleReconURL?style=for-the-badge&color=F9A825&logo=github&logoColor=white"></a>
</p>

URL extraction and discovery tool for OSINT and reconnaissance workflows.
Given a single seed URL, fetches its HTML and extracts every URL reachable from that page, by default just the page itself, optionally deepened with a same-origin crawler and enriched with external URL-discovery sources (Wayback Machine, Common Crawl, urlscan.io, AlienVault OTX, URLhaus, VirusTotal).

> [!NOTE]
> Built with async Python, no DNS/host-resolution logic, no external shell dependencies. Forked from [SimpleReconSubdomain](https://github.com/MrCl0wnLab/SimpleReconSubdomain), re-purposed around URLs instead of subdomains.

```
Author:   Cleiton Pinheiro a.k.a MrCl0wn
Blog:     https://blog.mrcl0wn.com
GitHub:   https://github.com/MrCl0wnLab
Twitter:  https://twitter.com/MrCl0wnLab
```

---

> [!CAUTION]
> **Legal disclaimer:** using SimpleReconURL against targets without prior mutual
> consent is illegal. It is the end user's responsibility to obey all applicable
> local, state and federal laws. The developers assume no liability and are not
> responsible for any misuse or damage caused by this program.

## Table of Contents

- [Installation](#installation)
- [API Keys](#api-keys)
- [Usage](#usage)
- [Profiles](#profiles)
- [Run-Config Presets](#run-config-presets)
- [Sources](#sources)
- [Same-Origin Crawler (spider)](#same-origin-crawler-spider)
- [Recursive Rounds](#recursive-rounds)
- [Headless Browser Capture](#headless-browser-capture)
- [Extras - External URLs](#extras-external-urls)
- [Page-Link Mapping - Graph JSON and HTML visualization](#page-link-mapping-graph-json-and-html-visualization)
- [Markdown Report](#markdown-report)
- [Database - SQLite Persistence](#database-sqlite-persistence)
- [Continuous Monitoring - --watch](#continuous-monitoring---watch)
- [Live Verification](#live-verification)
- [Output Formats](#output-formats)
- [Chaining with Other Tools](#chaining-with-other-tools)
- [Creating a New Module](#creating-a-new-module)
- [Banners](#banners)

---

## Installation

```bash
git clone https://github.com/osintbrazuca/SimpleReconURL
cd SimpleReconURL
pip install -r requirements.txt
```

**Dependencies** (`requirements.txt`):

| Package | Purpose |
|---|---|
| `httpx[socks]` | Async HTTP client for every source (`[socks]` enables `--proxy socks5://`) |
| `beautifulsoup4` | HTML parsing for the default page extractor, the `spider` crawler, and `robots_sitemap` |

### Optional: headless browser capture

> [!NOTE]
> The `browser` source needs Playwright plus its Chromium binary (~150MB). It is **not**
> required for anything else: without it that one source self-disables and the rest of
> the tool runs normally.

```bash
pip install -r requirements-browser.txt
playwright install chromium
```

See [Headless Browser Capture](#headless-browser-capture) for what it does.

### Docker

Run without a local Python setup. Two build paths, same image, then pass CLI args straight through:

```bash
# A) from local code (build context = repo root)
docker build -t docker/simplereconurl -f docker/Dockerfile .

# B) straight from GitHub, no local checkout needed
docker build -t docker/simplereconurl - < docker/Dockerfile.remote

# run (args after the image name go to simplereconurl.py)
docker run --rm docker/simplereconurl -u https://target.com/
```

See [docker/README_EN.md](docker/README_EN.md) for the full build options, persisting results (`--db` volume), the command log / `--watch` registry, mounting API keys, and running the scheduler.

---

## API Keys

> [!IMPORTANT]
> Keys live in `config/api_keys.json`, which is gitignored precisely so it is never
> committed by accident. Never version that file once it is filled in.

```json
{
    "alienvault_otx": "",
    "brave":          "",
    "publicwww":      "",
    "urlscan":        "",
    "virustotal":     ""
}
```

Fill in the keys you have. `alienvault_otx` and `urlscan` work unauthenticated (a key just raises the rate limit); `virustotal`, `brave` and `publicwww` require a key or the source returns nothing.

**Where to get each key:**

| Key | URL |
|---|---|
| `alienvault_otx` | https://otx.alienvault.com → Settings → API Integration |
| `urlscan` | https://urlscan.io/user/signup |
| `virustotal` | https://www.virustotal.com/gui/join-us |
| `publicwww` | https://publicwww.com/api.html (URL export needs a paid plan) |
| `brave` | https://brave.com/search/api/ (free tier available) |

---

## Usage

### Basic

```bash
# Single seed URL (scheme optional, https:// assumed)
python simplereconurl.py -u https://target.com/

# List of seed URLs
python simplereconurl.py -l seeds.txt

# List available sources
python simplereconurl.py --list-sources

# List available profiles (curated source groups)
python simplereconurl.py --list-profiles

# Print built-in usage examples and exit
python simplereconurl.py --list-examples

# Run a predefined profile (no need to spell out sources)
python simplereconurl.py -u https://target.com/ --profile crawl
python simplereconurl.py -u https://target.com/ --profile discovery --verify-live
```

<img src="./assets/img/exemplo-u.png" width="600px" alt="python simplereconurl.py -u https://argentina.gob.ar/">


### OSINT Context Examples

**Bug bounty: map a target page's outbound surface**
```bash
python simplereconurl.py -u https://target.com/ \
  --profile discovery --output json --outfile target_urls.json
```

**Deep crawl of a single site (same-origin only)**
```bash
python simplereconurl.py -u https://target.com/ \
  --sources spider,robots_sitemap \
  --verify-live \
  --output json --outfile crawl.json
```

**Full pipeline: seed page + crawl + discovery + liveness**
```bash
python simplereconurl.py -u https://target.com/ \
  --profile full --verify-live \
  --output json --outfile full.json
```

**Quiet mode: pipe discovered URLs directly to another tool**
```bash
python simplereconurl.py -u https://target.com/ --no-banner | httpx -silent
```

**Asset discovery from a list of seed URLs:**
```bash
python simplereconurl.py -l scope.txt --output json --outfile all_urls.json --timeout 60
```

### All Flags

```
Target:
  -u URL                 Single seed URL (scheme optional, assumed https://)
  -l FILE                File with list of seed URLs, one per line
  --stdin                Read seed URLs from stdin (one per line); enables pipe-friendly use

Output:
  -o {txt,json,csv,ndjson,html,markdown}
                         Output format (default: txt).
                         ndjson   = one compact JSON line per URL - ideal for jq piping
                         html     = interactive page-link map (vis-network via CDN)
                         markdown = human-readable reconnaissance report
  --outfile FILE         Write output to file
  --network-map          Include the page-link graph (nodes/edges) in JSON output.
                         Auto-enabled when -o html or --network-html is used.
  --network-html FILE    Write an HTML page-link map visualization to FILE alongside the
                         main output. Combine with any -o format.
  --db FILE              Per-target results database - persist the run and use as comparison source.
                         Stores discovered URLs (with source and, at -v 3, external URLs).
                         The command log lives in config/system.db.
  --db-news              Output and save only values not seen in prior --db runs (requires --db)
  --db-list TYPE         List and exit: urls | extras (from --db) or history
                         (from config/system.db, no --db). Optional -u filter.

Monitoring:
  --watch-add CRON       Register the current command (minus --watch-add) in config/system.db
                         on a 5-field cron schedule (e.g. "0,15,30,45 * * * *").
  --watch                Run the scheduler daemon: each minute launch due jobs in parallel
                         (prints each fired command). No --db needed; Ctrl-C to stop.
  --watch-list           List registered watch jobs with their IDs, then exit.
  --watch-del ID         Delete the watch job with the given ID (from --watch-list).
  --watch-clear          Delete all watch jobs, then exit.

Performance:
  -t N                   Thread multiplier for --verify-live concurrency (default: 8)
  --timeout N            HTTP timeout in seconds (default: 30)
  --rate-limit N         Max concurrent HTTP requests per source (0 = unlimited)

Network:
  --proxy URL            Route all HTTP requests through a proxy
                         (e.g. http://127.0.0.1:8080 or socks5://host:port)
  --user-agent UA        Override User-Agent for all source HTTP requests

Source control:
  --profile PROFILE      Run a predefined source group (fast, crawl, discovery, full).
                         Overrides --sources.
  --sources LIST         Comma-separated sources (default: all)
  --exclude LIST         Comma-separated sources to exclude (applied after --sources/--profile)
  --recursive N          Collection rounds (default: 1, max: 20). Each extra round feeds
                         the newly discovered URLs back as seeds and runs every selected
                         source over them. No source is re-run on an input it already
                         handled.
  --recursive-max-seeds N
                         Cap on how many new URLs are promoted to seeds per round
                         (default: 500, 0 = unlimited). Assets are never promoted.
  --no-passive           Skip passive discovery sources; the default page extraction and
                         active sources (spider/robots_sitemap) still run
  --list-sources         Print all sources with descriptions and exit
  --list-profiles        Print all profiles with their source sets and exit
  --list-examples        Print built-in usage examples and exit

Run-config:
  --config FILE          Load CLI argument defaults from a JSON preset file.
                         Only keys absent from the command line are applied;
                         explicit CLI flags always win.
                         Template: config/run_config.example.json

Post-processing:
  --verify-live          Probe each discovered URL: HTTP status, title, server,
                         content-length, body hash, response time

Display:
  -v [LEVEL]             Verbose level 1–4 (1=zero results, 2=+HTTP codes,
                         3=+body +extras (external URLs), 4=+exceptions)
  -q, --quiet            Results only; suppress all process messages
  --no-banner            Suppress banner and all process output (clean pipe mode)
  --no-progress          Disable the live progress line drawn during --recursive
                         rounds. It only ever appears when stderr is a terminal,
                         so piping is unaffected either way.
  --no-color             Disable ANSI colors
```

---

## Profiles

Profiles are curated source groups defined in [config/profiles.json](config/profiles.json). Use `--profile NAME` instead of typing long `--sources` lists.

```bash
python simplereconurl.py --list-profiles
python simplereconurl.py -u https://target.com/ --profile crawl
```

| Profile | Description | Sources |
|---|---|---|
| `fast` | Seed page only, no extra sources beyond the default extraction | *(none)* |
| `crawl` | Deep same-origin crawl of the seed site | `spider`, `nextjs` |
| `api` | API surface | `openapi`, `cms_routes`, `well_known` |
| `archive` | Historical web archives only | `wayback`, `commoncrawl`, `arquivopt` |
| `search` | Search engines | `googlecse`, `yahoo`, `bing`, `google`, `marginalia`, `publicwww` |
| `discovery` | External URL discovery: archives, threat intel, search | `wayback`, `commoncrawl`, `arquivopt`, `urlscan`, `alienvault`, `urlhaus`, `virustotal`, `brave` |
| `browser` | Headless browser runtime capture (needs Playwright) | `browser` |
| `full` | Everything except `browser` | crawl + robots/sitemap + API surface + feeds + all discovery |


<img src="./assets/img/list-profiles.png" width="600px" alt="Simple Recon URL">


> [!IMPORTANT]
> `full` is an explicit source list rather than `"all"` so that the `browser` source, which needs a ~150MB optional browser download, never runs implicitly. Run it via `--profile browser` or `--sources browser`. If you add a new source and want it in `full`, add it to the list in [config/profiles.json](config/profiles.json).

Add or edit profiles by modifying [config/profiles.json](config/profiles.json):

```json
{
  "myprofile": {
    "description": "My custom set",
    "sources": ["spider", "wayback"],
    "options": {"rate_limit": 5}
  }
}
```

---

## Run-Config Presets

A run-config is a JSON file that stores CLI argument defaults, allowing you to run repeatable scans without long command lines.

```bash
python simplereconurl.py -u https://target.com/ --config config/run_config.example.json
python simplereconurl.py -u https://target.com/ --config my_scan.json
```

**Precedence (highest → lowest):**
1. Explicit CLI flags (always win)
2. Values from the `--config` JSON file
3. Built-in argparse defaults

The annotated template at [config/run_config.example.json](config/run_config.example.json) documents every available key.

---

## Sources

```bash
python simplereconurl.py --list-sources
```

The seed page itself is **always** fetched and its URLs extracted first. This isn't a selectable source, it's the tool's core default behavior and can't be excluded via `--sources`/`--exclude`.

### Passive Sources

| Source | Requires key | Notes |
|---|---|---|
| `wayback` | No | web.archive.org CDX API, archived URLs under the seed's host |
| `commoncrawl` | No | Common Crawl CDX API, sweeps the 3 most recent crawl indexes |
| `arquivopt` | No | Arquivo.pt: Portuguese web archive, strong PT/BR coverage the Wayback lacks |
| `brave` | Required | Brave Search API, pages indexed by a search engine (`site:` query) |
| `googlecse` | No | Google via ~26 **public** Custom Search Engines: real Google index, no key |
| `yahoo` | No | Yahoo Search, the one major engine still answering `site:` without a challenge |
| `bing` | No | Bing Search: **best-effort**, usually served a bot challenge (see note below) |
| `google` | No | google.com scrape: **best-effort**, usually blocked; use `googlecse` instead |
| `marginalia` | No | Marginalia: independent non-commercial index; unique pages, low in-scope yield |
| `publicwww` | Required | PublicWWW: searches page **source code**, not text |
| `urlscan` | Optional | Higher rate limit with key; scanned page/task URLs |
| `alienvault` | Optional | AlienVault OTX `url_list` endpoint |
| `urlhaus` | No | URLhaus abuse.ch malicious URL database, no auth needed |
| `virustotal` | Required | VT `domains/{host}/urls` relationship |

<img src="./assets/img/list-sources.png" width="600px" alt="Simple Recon URL">


### Active Sources

> [!WARNING]
> Active sources send real HTTP requests **to the target** and show up in its logs.
> Only use them where you are authorised to.

| Source | Requires key | Notes |
|---|---|---|
| `spider` | No | Same-origin BFS crawler + JS/CSS/sourcemap miner, including **relative API endpoints** (`/api/v1/users`) that only exist inside JS bundles |
| `robots_sitemap` | No | `robots.txt` directives + recursive `sitemap.xml` `<loc>` extraction |
| `nextjs` | No | Next.js route extraction: build manifest, RSC flight data, `[param]` routes and `/_next/data/` endpoints |
| `openapi` | No | OpenAPI/Swagger spec discovery, expands `paths{}` into the full API surface |
| `well_known` | No | `.well-known/` harvesting: OIDC endpoints, `security.txt`, mobile deep-link paths |
| `cms_routes` | No | WordPress `/wp-json/` route table + Drupal `/jsonapi` |
| `feeds` | No | RSS/Atom/JSON feed discovery, entry URLs from the site's own feeds |
| `browser` | No (needs Playwright) | Headless browser, captures every request the page makes at runtime |

---

## Same-Origin Crawler (spider)

`spider` starts at the exact seed URL (path and query preserved) and does a breadth-first crawl up to depth 3 / 100 pages, following `<a href>` and `<link href>`, downloading `<script src>` JS files and their sourcemaps, and mining URL literals out of JS/`.map` bodies.

Same-origin only by default: a link is followed only if its host equals the seed's host or is a subdomain of it. Cross-origin links encountered along the way are **not followed**, but are recorded and surfaced at `-v 3` / in `--db` as external URLs, the same pattern every other source uses for out-of-scope findings.

```bash
python simplereconurl.py -u https://target.com/ --sources spider -v 3
```

---

## Recursive Rounds

By default SRURL collects once and stops. With `--recursive N` the result becomes the input of the next collection: the newly discovered URLs become seeds, every selected source runs over them again, and the cycle repeats for up to N rounds. The default is 1, which is exactly the long-standing behavior, and the maximum is 20.

```bash
# three rounds, with whatever profile and sources you already use
python simplereconurl.py -u https://target.com/ --profile crawl --recursive 3

# aggressive re-feeding, with a per-round seed cap
python simplereconurl.py -u https://target.com/ --recursive 10 --recursive-max-seeds 200
```

Every round reports what it yielded:

```
[*] Round 2/3: 232 new seed url(s)...
[+] Round 2/3: +1841 urls
[*] Round 3/3: 1602 new seed url(s)...
[+] Round 3/3: +403 urls

[+] Total unique URLs found: 2501 (3 round(s))
[+] 184 asset url(s) found, not crawled (-v 3 to list them)
```

### Live progress

A round can take minutes. While it runs, a single line is rewritten in place, showing how much has been collected and how much of it is new:

```
[*] round 2/3 [######----------]  43% | tasks 128/296 | urls 1841 (+412 new) | now /blog/post-1
```

Every counter is labeled, because the two fractions measure different things:

| Field | What it is |
|---|---|
| `round 2/3` | current round and the total asked for with `--recursive` |
| `tasks 128/296` | **source runs** finished and scheduled for this round, not URLs |
| `urls 1841` | running unique total for the whole run, across every round |
| `(+412 new)` | how many of those are new **in this round** |
| `now /blog/post-1` | the URL being processed right now |

The percentage is real rather than estimated: the tool knows upfront how many runs the round will have, because it builds the full list before dispatching. Nothing already on screen is erased, the line uses `\r` and overwrites itself.

> [!TIP]
> `tasks` is usually far smaller than `seeds × sources`, and that is the layered dedup at work. Host-layer sources already queried the whole domain in round 1, so they never run again and contribute zero runs here.

> [!NOTE]
> The line goes to **stderr**, and only when stderr is a terminal. In practice `python simplereconurl.py -u https://target.com/ --recursive 3 | httpx` still shows progress on screen **and** delivers a clean pipe, because only stdout was redirected. Meanwhile `... > log.txt 2>&1` produces no progress at all, so the file never fills up with terminal garbage. Use `--no-progress` to turn it off, or `-q` which suppresses everything.

On a narrow terminal the line degrades by priority: the URL goes first, then the bar. The counters never go.

### Nothing is tested twice

A URL is never fetched again in a later round, and no source is re-run with an input it already handled. This holds across rounds, not just within one.

The non-obvious part is that "already handled" means different things per source, because sources do not read the same part of the target. Each one declares its layer, shown in the `scope` column of `--list-sources`:

| Layer | Sources | Runs |
|---|---|---|
| `url` | `page`, `browser` | once per URL, since they read the exact page |
| `origin` | `spider`, `nextjs`, `openapi`, `well_known`, `cms_routes`, `feeds` | once per origin, since they probe a fixed path set per site |
| `host` | the 15 passive ones and `robots_sitemap` | once per domain, since they already query `*.host` in one shot |

> [!IMPORTANT]
> Every selected module still runs. What the tool avoids is repeating a run whose result would be identical. Querying Wayback 257 times with the same query returns no extra URL, and on a 61-URL test target this cut 1403 source executions down to 151 without losing a single result.

A newly discovered subdomain counts as a new origin, so `origin`-layer sources do run again for it.

### Seeds and limits

Only URLs that can contain links become seeds. Assets are dropped by extension (`.css`, `.js`, `.png`, `.woff2`, `.pdf` and the like), because the page extractor only parses HTML. JS bundles are still mined by `spider`, the module built for that.

**Those assets are not lost.** They stay in the result's URL list like any other finding; what the tool now reports is which ones were found and never visited. The count is printed at the end, and at `-v 3` the full list enters the output in its own block:

```
## Extras
### External URLs (out of scope, not followed)
### Asset URLs (in scope, found but not crawled)
```

> [!TIP]
> The two blocks are different things, which is why they are kept apart. External URLs are **out** of scope and are **not** in the main list. Assets are **in** scope and **are** already in it: the only new information is that they were not fetched. That is why the asset block appears in the JSON, in the markdown report and in `--db` (type `url_asset`), but is never appended to the `csv`, `ndjson` and `txt` outputs, where it would emit a second row for the same URL.

> [!WARNING]
> Recursion multiplies the traffic sent to the target. `--recursive-max-seeds` (default 500) limits how many new URLs become seeds per round, and it is worth tuning alongside `--rate-limit` before raising N much. A value outside the 1 to 20 range stops the run with exit code 2 rather than being silently clamped.

Recursion stops on its own once there are no new seeds left, even if N has not been reached.

---

## Search Engines

Search engines know URLs nothing else does: pages linked only from third-party sites, which no archive snapshot and no same-origin crawl will ever reach. All four modules send a single `site:{host}` query and page through the results.

```bash
python simplereconurl.py -u https://target.com/ --profile search
python simplereconurl.py -u https://target.com/ --sources googlecse,yahoo -v 1
```

**Which ones actually work** (measured, not assumed):

| Source | Key | Status |
|---|---|---|
| `googlecse` | none | ✅ Reaches the real Google index through ~26 **public** Custom Search Engines. Rotates 3 per run, since each has its own index and scope. |
| `yahoo` | none | ✅ Still answers `site:` without a challenge. Paginates 4 offsets, verified to return distinct result sets, not the same page repeated. |
| `marginalia` | none | ✅ Independent index nobody else has. But it is a **free-text search, not `site:`**, measured 1–3 of 20 hits actually on target, and it rate-limits after ~3 queries. Low volume, unique coverage. |
| `publicwww` | required | Searches page **source code** rather than text, so it finds the target's pages by a shared snippet (Analytics ID, bundle name). URL export needs a paid plan. |
| `bing` | none | ⚠️ Best-effort. Returned a Cloudflare Turnstile challenge and **zero** results during testing, even with browser headers. |
| `google` | none | ⚠️ Best-effort. `google.com/search` returned a JavaScript shell page with **zero** result links. Use `googlecse` for Google coverage. |

> [!TIP]
> For Google coverage use `googlecse`: it reaches the real index through public Custom
> Search Engines and does not rely on scraping, which is currently blocked.

`bing` and `google` ship anyway because the block is IP/reputation-based, not permanent. They may work from another network or behind `--proxy`. When blocked they contribute nothing and never break a run, so seeing `0 new urls` from them is the expected outcome, not a bug.

Two implementation notes worth knowing:

- **The tool's default User-Agent is an instant block here.** These modules rotate a realistic desktop browser UA instead, unless you set `--user-agent` explicitly, in which case yours is honoured.
- **The engines' own navigation is filtered out.** Scraping a result page also scoops up its header/footer links; one Bing query alone contributed 61 junk `r.bing.com` URLs before that filter existed. Links inside the target's scope are never dropped, so scanning one of those domains still works.

---

## Next.js Route Extraction

A Next.js app keeps its whole route table inside the JS bundle, not in the HTML. Minified chunks contain arrays like

```js
["/[username]/[contractAddress]/[tokenId]/bid", "/admin/approve", "/settings", ...]
```

which enumerate every page of the site, admin areas and dynamic routes included, linked from nowhere.

```bash
python simplereconurl.py -u https://target.com/ --sources nextjs -v 1
python simplereconurl.py -u https://target.com/ --profile crawl      # spider + nextjs
```

The framework has two routers that expose completely different things, and both are handled:

| Router | What it gives |
|---|---|
| **Pages Router** (legacy, common on smaller targets) | `__NEXT_DATA__` → `buildId`; `/_next/static/<buildId>/_buildManifest.js`, whose keys are the **complete route table**; and `/_next/data/<buildId>/<route>.json` per-route JSON endpoints, frequently unauthenticated |
| **App Router** (Next 13+, what most sites run) | RSC flight data (`self.__next_f.push`) streamed into the HTML: no `__NEXT_DATA__`, no build manifest |

Route templates (`/[username]/...`, `/blog/[...slug]`) are emitted as-is. They are not fetchable URLs, but they are the route surface, which is the point, same call as `openapi` makes for `/users/{id}`.

Detection costs a single request: if the seed page shows no `/_next/`, `__NEXT_DATA__` or `self.__next_f` marker, the module says so at `-v 1` and stops without probing anything.

> [!NOTE]
> The `spider` source also mines relative paths from JS and now understands `[param]` segments too, so it picks up dynamic routes on any framework. `nextjs` goes further with the framework-specific artifacts (build manifest, buildId, `/_next/data/` endpoints). Running both re-downloads some chunks, accepted, as there is no cross-source cache.

---

## Headless Browser Capture

Every other source reads **static markup or text**. The `browser` source opens the seed URL in a hidden Chromium instance and records every request the page actually makes **at runtime**, `fetch`/XHR API calls, scripts injected by JS, tracking beacons, lazy-loaded assets, WebSocket handshakes. None of that exists in the HTML, so no amount of parsing will find it.

```bash
# one-time setup
pip install -r requirements-browser.txt && playwright install chromium

python simplereconurl.py -u https://target.com/ --profile browser
python simplereconurl.py -u https://target.com/ --sources browser -v 2   # log method + resource type
```

The difference on a page whose endpoints are called from JavaScript:

```
# static parsing (--profile fast)
http://target/static-link.html

# browser capture (--profile browser)
http://target/
http://target/api/v1/users?page=1        <- fetch()
http://target/api/v1/config.json         <- fetch()
http://target/api/v1/late-call           <- fetch() fired 400ms after load
http://target/assets/injected-by-js.js   <- <script> appended by JS
http://target/beacon.gif?t=1786253769401 <- runtime-generated URL
http://target/static-link.html
```

How it behaves:

- **Headless always**: the browser window is never shown.
- **Scope** follows the same rule as every other source: in-scope requests are results; third-party hosts (CDNs, analytics, fonts) go to external URLs, visible at `-v 3` and in `--db`.
- **Waits for late traffic**: after `load` it waits for network idle (bounded, so polling/WebSocket pages don't hang it), then scrolls once to trigger lazy-loaded requests.
- **Fails soft**: a navigation timeout or unreachable host still returns whatever was captured before the failure, and the browser is always closed.
- **Honours `--timeout`, `--proxy` and `--user-agent`** like the rest of the tool.
- Without Playwright installed it prints one install hint and returns nothing; it never breaks a run.

Not included in `--profile full` on purpose. See the note under [Profiles](#profiles).

---

## Extras: external URLs

Verbose level **`-v 3`** surfaces URLs collected during enumeration that fall outside the seed's host, useful for mapping third-party dependencies and understanding what a page links out to. (Level 3 also enables HTTP body-preview logging.)

```bash
python simplereconurl.py -u https://target.com/ --sources spider -v 3 --no-banner
```

### Output per format

**txt**: appended section (suppressed with `--no-banner`/`--quiet`):
```
https://target.com/
https://target.com/about

# External URLs
https://accounts.google.com/o/oauth2/...
https://cdn.jsdelivr.net/npm/...
```

**json**: top-level `"extras"` object:
```json
"extras": {
  "urls_external": ["https://accounts.google.com/...", "https://cdn.jsdelivr.net/..."]
}
```

**ndjson**: additional lines with `type` field:
```json
{"seed": "https://target.com/", "url": "https://cdn.jsdelivr.net/...", "type": "url_external"}
```

**csv**: extra rows with `type` = `url_external`.

### jq recipes for extras

```bash
python simplereconurl.py -u https://target.com/ --sources spider -v 3 -o ndjson \
  | jq 'select(.type == "url_external") | .url'
```

---

## Page-link mapping: graph JSON and HTML visualization

Turn the flat URL list into a navigable graph: a JSON graph (nodes + edges) you can pipe into other tools, and an interactive HTML page for visual triage. The graph is built **entirely from data already collected** during the run, no extra requests.

### Flag reference: three axes

| Flag | Role | Output lands in | Combinable? |
|---|---|---|---|
| **`-o html`** | Primary output format - replaces `txt`/`json`/`csv`/`ndjson` | `stdout` or `--outfile` | One `-o` at a time |
| **`--network-html FILE`** | Side artifact - always writes the HTML visualization to `FILE` | `FILE` (any path) | Yes - works alongside any `-o` |
| **`--network-map`** | Injects a `"network"` block (nodes/edges) into the JSON output | Inside the JSON document | Only meaningful with `-o json`; auto-enabled by `-o html`/`--network-html` |

```bash
python simplereconurl.py -u https://target.com/ --profile full --network-map -o json --outfile out.json
python simplereconurl.py -u https://target.com/ --profile full -o html --outfile map.html
```

### Graph model

| Node type | Built from | Notes |
|---|---|---|
| `seed` | scan target | one per seed URL |
| `page` | `result.urls` | colored by `live.status` (2xx/3xx/4xx/5xx/none) |
| `external` | `extras.urls_external` (needs `-v 3`) | out-of-scope URLs found but not followed |

| Edge relation | Direction |
|---|---|
| `links_to` | `seed → page` |
| `links_to_external` | `seed → external` |

This is "what was found from this seed," not a literal page-to-page crawl graph; sources report which URLs they found, not which page linked to which.

### HTML viewer

Single self-contained file. Loads [vis-network](https://visjs.github.io/vis-network/) `9.1.9` from `unpkg.com` (CDN: requires internet when opened). Click a node for HTTP status/title/server; all seeds from a multi-target run merge into one graph.

---

## Markdown Report

`-o markdown` produces a complete reconnaissance report as a single `.md` file: summary metrics, live-URL table, duplicate response-body detection, the full URL list, external-URL extras, and per-source contribution counts.

```bash
python simplereconurl.py -u https://target.com/ --verify-live -o markdown --outfile report.md
```

---

## Database: SQLite persistence

Persist every run to a SQLite file, diff new findings against past runs, and read the stored data back, all with the Python stdlib `sqlite3` (no extra dependency). There are **two** stores:

- **Per-target results DB**: `--db FILE` (a path you choose). Holds recon **results only**: discovered `urls` (tagged with source + optional liveness fields) and `extras` (external URLs, at `-v 3`). Different files are independent stores.
- **Fixed system DB**: `config/system.db` (resolved relative to the install, **never passed as a parameter**). Holds the command-history log and the `--watch` scheduler jobs.

```bash
# Save the full run
python simplereconurl.py -u https://target.com/ --db recon.db

# Only new since last run
python simplereconurl.py -u https://target.com/ --db recon.db --db-news

# Inspect the database
python simplereconurl.py --db recon.db --db-list urls
python simplereconurl.py --db recon.db --db-list extras
python simplereconurl.py --db-list history

# Pipe stored URLs into another tool
python simplereconurl.py --db recon.db --db-list urls | httpx -silent
```

### Schema

Append-only, keyed by `seed`.

| Table | Contents |
|---|---|
| `urls` | discovered URLs + source + optional live-check fields (status, title, server, body_hash, response_ms) |
| `extras` | external (out-of-scope) URLs, saved at `-v 3` |

---

## Continuous Monitoring (`--watch`)

A built-in cron scheduler: register recon commands once, then run a daemon that fires them on schedule. Jobs live in the fixed `config/system.db`, no external `cron`/`systemd` needed.

```bash
# every 15 minutes, run a discovery scan that persists results + diffs
python simplereconurl.py -u https://target.com/ --profile discovery --db target.db --quiet \
  --watch-add "0,15,30,45 * * * *"

# run the scheduler
python simplereconurl.py --watch

# manage jobs
python simplereconurl.py --watch-list
python simplereconurl.py --watch-del 3
python simplereconurl.py --watch-clear
```

---

## Live Verification

`--verify-live` probes each discovered URL directly (it already carries its own scheme; a connect-level failure retries once with the other scheme) and records HTTP status, title, server header, content length, a body hash, and response time.

```bash
python simplereconurl.py -u https://target.com/ --verify-live -o json --outfile out.json
```

```
[LIVE] https://target.com/about → 200 - About Us
[LIVE] https://target.com/old-page → 404
```

The `duplicate_bodies` field in JSON output flags URLs sharing an identical response body hash, useful for spotting soft-404s or duplicate-content pages.

<img src="./assets/img/exemplo-live.png" width="600px" alt="python simplereconurl.py -u https://argentina.gob.ar/">


---

## Output Formats

### Terminal (default)

```
------------------------------------------------------------
[*] Enumerating: https://target.com/
------------------------------------------------------------
[*] Extracting URLs from the seed page...
[*] [page] +12 urls
[*] [spider] +34 urls
[*] [wayback] +8 urls

[+] Total unique URLs found: 41

https://target.com/
https://target.com/about
https://target.com/blog/post-1
...
```

### JSON

```json
{
  "seed": "https://target.com/",
  "timestamp": "2026-05-27T14:32:01.123456",
  "total": 41,
  "urls": ["https://target.com/", "https://target.com/about"],
  "live_urls": {
    "https://target.com/about": {
      "status": 200,
      "title": "About Us",
      "server": "nginx/1.24.0",
      "content_length": 1842,
      "body_hash": "a1b2c3d4e5f6a7b8",
      "response_ms": 125
    }
  },
  "sources": {"page": 12, "spider": 34, "wayback": 8}
}
```

### CSV

```
seed,url,type,source,status,title,server,body_hash,response_ms
https://target.com/,https://target.com/about,url,spider,200,About Us,nginx/1.24.0,a1b2c3d4e5f6a7b8,125
```

### NDJSON

One compact JSON line per URL: designed for streaming and `jq` piping.

```json
{"seed": "https://target.com/", "url": "https://target.com/about", "type": "url", "source": "spider", "status": 200, "title": "About Us"}
```

```bash
# Live URLs only
python simplereconurl.py -u https://target.com/ --verify-live -o ndjson | jq 'select(.status != null)'

# Extract only URLs (pipe-friendly)
python simplereconurl.py -u https://target.com/ -o ndjson | jq -r '.url'
```

### TXT

```bash
python simplereconurl.py -u https://target.com/ -o txt --outfile results/target.txt
```

### HTML: interactive page-link map

See [Page-Link Mapping](#page-link-mapping-graph-json-and-html-visualization).

### Markdown: human-readable reconnaissance report

See [Markdown Report](#markdown-report).

---

## Chaining with Other Tools

### httpx - HTTP probing

```bash
python simplereconurl.py -u https://target.com/ --no-banner | httpx -silent -status-code -title -tech-detect
python simplereconurl.py -u https://target.com/ --no-banner | httpx -silent -mc 200
```

### nuclei - vulnerability scanning

```bash
python simplereconurl.py -u https://target.com/ --no-banner \
  | httpx -silent \
  | nuclei -t cves/ -silent
```

### katana / gau - further crawling

```bash
python simplereconurl.py -u https://target.com/ --no-banner | httpx -silent | katana -silent
python simplereconurl.py -u https://target.com/ --no-banner | gau --threads 10
```

### gowitness / aquatone - screenshots

```bash
python simplereconurl.py -u https://target.com/ --no-banner | httpx -silent | gowitness scan single
python simplereconurl.py -u https://target.com/ --no-banner | aquatone -out aquatone-report/
```

### string-x (strx): enrichment and automation

[string-x](https://github.com/MrCl0wnLab/string-x) is a modular automation tool using a `{STRING}` placeholder. It pairs naturally with SimpleReconURL via pipes.

```bash
# HTTP probe all discovered URLs
python simplereconurl.py -u https://target.com/ --no-banner \
  | strx -st "echo {STRING}" -module "clc:http_probe" -pm

# Extract emails from every discovered page
python simplereconurl.py -u https://target.com/ --no-banner \
  | strx -st "curl -sk {STRING}" -module "ext:email" -pm

# Notify Telegram with every newly discovered URL
python simplereconurl.py -u https://target.com/ --db recon.db --db-news --no-banner \
  | strx -st "echo {STRING}" -module "con:telegram" -pm
```

---

## Creating a New Module

All sources inherit from `BaseSource` in `sources/base.py`. Drop the file in `sources/passive/` or `sources/active/` - no other file needs editing.

The class name must be the **title-cased filename** (e.g. `myservice.py` → class `Myservice`), and `NAME` must equal the filename without `.py`.

A source's `fetch(target)` receives a `Target` (`target.url` = the seed's full URL, `target.host` = its lowercased hostname) and returns the in-scope **URLs** it found, always route the raw findings through `self._filter_urls(urls, target.host)`, which keeps in-scope URLs and automatically routes out-of-scope ones into `self.extras['urls_external']`.

### New Passive (domain-query) Source

```python
# sources/passive/myservice.py
from sources.base import BaseSource, Target
from core.config import get_key


class Myservice(BaseSource):
    NAME = 'myservice'
    DESCRIPTION = 'My custom service'
    API_TOKEN_IS_REQUIREMENT = True

    async def fetch(self, target: Target) -> set[str]:
        api_key = get_key('myservice')
        if not api_key:
            return set()

        urls: set[str] = set()
        headers = {'Authorization': f'Bearer {api_key}'}
        async with self._make_client(headers=headers) as client:
            resp = await self._get(client, f'https://api.myservice.com/urls/{target.host}')
            if resp.status_code == 200:
                for entry in resp.json().get('data', []):
                    if entry.get('url'):
                        urls.add(entry['url'])

        return self._filter_urls(urls, target.host)
```

Add the key to `config/api_keys.json`:
```json
{ "myservice": "your-api-key-here" }
```

### New Active (direct-HTTP) Source

```python
# sources/active/myactive.py
from sources.base import BaseSource, Target


class Myactive(BaseSource):
    NAME = 'myactive'
    DESCRIPTION = 'Active: custom URL probe'
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        urls: set[str] = set()
        try:
            async with self._make_client(verify=False) as client:
                resp = await self._get(client, target.url)
                # ... parse resp.text for URLs ...
        except Exception as e:
            self._log_exc(e)
        return self._filter_urls(urls, target.host)
```

---

## Banners

Startup art is picked **at random** on every run, following the same scheme as [string-x](https://github.com/MrCl0wnLab/string-x). Each banner is a `.txt` file in [core/banner/asciiart/](core/banner/asciiart/); a fixed footer with the tool name, version and author links is printed underneath.

To add a banner, just drop a `.txt` file into that directory. Nothing else to edit:

```bash
cp my-art.txt core/banner/asciiart/
```

Rules for banner files:

- **Raw ANSI, not Rich markup.** Colors must be embedded as real escape codes (`ESC[0;91m … ESC[0m`). This is the one deliberate difference from string-x, which stores `[color]…[/color]` tags and renders them through the `rich` library, here files are printed as-is, so the project needs no extra dependency. Under `--no-color` (or when stdout is piped) the escapes are stripped automatically.
- **Two placeholders** are substituted at display time, both sourced from [core/settings.py](core/settings.py):

  | Placeholder | Becomes |
  |---|---|
  | `[VERSION]` | `1.0.0` |
  | `[DESCRIPTION]` | `Extract and discover URLs from a seed page` |

- Keep art reasonably narrow; there is no terminal-width filtering, so very wide art wraps on narrow terminals.

Where the banner shows:

| Command | Banner |
|---|---|
| Normal run, `--help`/`-h`, `--list-sources`, `--list-profiles`, `--list-examples`, no-arg invocation | yes |
| `-q` / `--quiet` / `--no-banner` (any command) | no |
| `--db-list` | no, it emits pipe-friendly data lines, so it stays safe for `\| httpx` |

A missing, empty or unreadable banner directory is not an error: the tool simply prints the footer alone and carries on.

<img src="./assets/img/list-examples.png" width="600px" alt="Examples">


---

## 📄 LICENSE

This project is licensed under the Apache License. See the [LICENSE](LICENSE) file for details.

## 👨‍💻 AUTHOR

**MrCl0wn**
- 🌐 **Blog**: [http://blog.mrcl0wn.com](http://blog.mrcl0wn.com)
- 🐙 **GitHub**: [@MrCl0wnLab](https://github.com/MrCl0wnLab)
- 🐦 **Twitter**: [@MrCl0wnLab](https://twitter.com/MrCl0wnLab)
- 📧 **Email**: mrcl0wnlab\@\gmail.com

---

## Contributing ✨ <a name="contributing"></a>

Contributions of any kind are welcome!

<a href="https://github.com/osintbrazuca/SimpleReconURL/graphs/contributors">
  <img src="https://contributors-img.web.app/image?repo=osintbrazuca/SimpleReconURL&max=500" alt="Contributors list" width="100%"/>
</a>

---

<div align="center">

**⭐ If this project was useful, consider leaving a star!**

**💡 Suggestions and feedback are always welcome!**

**💀 Hacker Hackeia!**

</div>
