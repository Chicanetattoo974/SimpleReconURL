"""
HTML + JS spider (active source).

Phase 1 — Fetches the seed URL exactly as given (http fallback only when the
           initial request fails at the connection level, not on a non-5xx
           response).
Phase 2 — BFS crawl: follows <a href> and <link href> up to _MAX_DEPTH,
           collecting <script src> and <link preload as=script> into a
           separate JS queue along the way. Same-origin (seed host or a
           subdomain of it) only — cross-origin links found along the way
           are recorded in self.extras['urls_external'] instead of being
           followed.
Phase 3 — Downloads each JS file; mines URL literals from its body and
           discovers sourcemap references (X-SourceMap header or
           //# sourceMappingURL).
Phase 4 — Downloads .map files and mines URL literals from their content.

Because this makes direct HTTP requests to the target it lives in sources/active/.
"""
import asyncio
import re
import warnings
from collections import deque
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from sources.base import BaseSource, Target

warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)

_BROWSER_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
}

_JS_HEADERS = {
    'Accept': '*/*',
    'Sec-Fetch-Dest': 'script',
    'Sec-Fetch-Mode': 'no-cors',
}

_MAX_PAGES         = 100
_MAX_DEPTH         = 3
_CONCURRENCY       = 5
_MAX_JS_FILES      = 40
_MAX_MAP_FILES     = 30
_MAX_CSS_FILES     = 20
_MAX_EXTERNAL_URLS = 2000
_MAX_LITERAL_URLS  = 2000

# Stylesheets reference fonts, sprites and background images that appear
# nowhere in the HTML. Resolved against the stylesheet's own URL, which is
# what the CSS spec requires for relative url() references.
_CSS_URL_RE    = re.compile(r'''url\(\s*['"]?([^'")\s]+)['"]?\s*\)''', re.IGNORECASE)
_CSS_IMPORT_RE = re.compile(r'''@import\s+(?:url\(\s*)?['"]([^'"]+)['"]''', re.IGNORECASE)

_MAP_COMMENT_RE = re.compile(
    r'//[#@]\s*sourceMappingURL=([^\s\'"]+)', re.IGNORECASE
)
_URL_LITERAL_RE = re.compile(r'''https?://[^\s'"<>)\\]+''')

# Root-relative endpoint literals inside JS/.map bodies, e.g. "/api/v1/users",
# `/graphql`, '/_next/data/build/x.json'. These are where most API endpoints of
# a modern bundle live, and they are invisible to _URL_LITERAL_RE above.
# Deliberately narrow: must be quoted, must start with a single '/', and may
# only contain URL-ish characters. A looser pattern floods the results with
# regex literals, CSS selectors and date fragments.
# The query string is captured too — parameter names are valuable recon output.
# `[]` in the path charset is what lets Next.js dynamic routes through
# ("/[username]/[tokenId]/bid", "/blog/[...slug]"). Without it the framework's
# entire dynamic route surface is silently dropped — only the static routes of
# the same array survive.
_REL_PATH_RE = re.compile(
    r'''['"`](/[A-Za-z0-9_\-./{}\[\]~%:]{2,180}'''
    r'''(?:\?[A-Za-z0-9_\-.=&%{}\[\]]{1,120})?)['"`]'''
)
# Rejected outright: protocol-relative ('//cdn...' is handled as a URL), paths
# with no letter at all ('/1/2/3' — dates, version fragments, math), and common
# JS/CSS noise that happens to start with a slash.
_REL_PATH_REJECT_RE = re.compile(r'^/(?:/|\d+(?:[./]\d+)*$)')
_REL_PATH_HAS_ALPHA_RE = re.compile(r'[A-Za-z]')


def _in_scope(url: str, host: str) -> bool:
    try:
        h = (urlparse(url).hostname or '').lower().rstrip('.')
    except Exception:
        return False
    return h == host or h.endswith(f'.{host}')


class Spider(BaseSource):
    NAME = 'spider'
    SCOPE = 'origin'   # its own BFS already walks the whole origin
    DESCRIPTION = (
        'Active: same-origin HTML crawler + JS/CSS/sourcemap miner — follows '
        'links, mines relative API endpoints from JS bundles, .map and .css files'
    )
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        host = target.host

        # BFS state
        page_queue: deque[tuple[str, int]] = deque()
        visited: set[str] = set()   # dedup — prevents the same URL being enqueued twice
        fetched: int = 0            # counts actually completed HTTP requests
        external: set[str] = set()  # cross-origin links seen but not followed

        # JS / CSS collection (populated during BFS)
        js_urls: list[str] = []
        js_seen: set[str] = set()
        css_urls: list[str] = []
        css_seen: set[str] = set()

        # URL literals mined from JS/.map bodies
        literal_urls: set[str] = set()

        _seed = urlparse(target.url)
        origin = f'{_seed.scheme}://{_seed.netloc}'

        def _mine_literals(body: str) -> None:
            if len(literal_urls) >= _MAX_LITERAL_URLS:
                return
            # Absolute URLs
            for m in _URL_LITERAL_RE.finditer(body):
                if len(literal_urls) >= _MAX_LITERAL_URLS:
                    break
                literal_urls.add(m.group(0).rstrip('.,;)'))
            # Root-relative endpoints, resolved against the seed's origin
            for m in _REL_PATH_RE.finditer(body):
                if len(literal_urls) >= _MAX_LITERAL_URLS:
                    break
                path = m.group(1)
                if _REL_PATH_REJECT_RE.match(path):
                    continue
                if not _REL_PATH_HAS_ALPHA_RE.search(path):
                    continue
                literal_urls.add(urljoin(origin, path))

        async with self._make_client(verify=False, headers=_BROWSER_HEADERS) as client:
            # ── Phase 1: seed from the exact seed URL ─────────────────
            candidates = [target.url]
            if target.url.startswith('https://'):
                candidates.append('http://' + target.url[len('https://'):])

            root_url = ''
            for candidate_url in candidates:
                try:
                    resp = await asyncio.wait_for(
                        client.get(candidate_url),
                        timeout=self.timeout,
                    )
                    if resp.status_code < 500:
                        root_url = str(resp.url)
                        visited.add(root_url)
                        self._enqueue_links(resp.text, root_url, host, visited, page_queue, external, depth=1)
                        self._collect_js(resp.text, root_url, host, js_seen, js_urls, external)
                        self._collect_css(resp.text, root_url, host, css_seen, css_urls, external)
                        break
                except Exception:
                    continue

            if not root_url:
                self.extras['urls_external'].update(external)
                return self._filter_urls(visited, host)

            # ── Phase 2: BFS crawl ────────────────────────────────────
            semaphore = asyncio.Semaphore(_CONCURRENCY)

            async def crawl(url: str, depth: int) -> None:
                nonlocal fetched
                async with semaphore:
                    try:
                        resp = await asyncio.wait_for(
                            client.get(url),
                            timeout=self.timeout,
                        )
                        fetched += 1
                        if resp.status_code < 400:
                            html = resp.text
                            actual_url = str(resp.url)
                            self._collect_js(html, actual_url, host, js_seen, js_urls, external)
                            self._collect_css(html, actual_url, host, css_seen, css_urls, external)
                            if depth < _MAX_DEPTH:
                                self._enqueue_links(
                                    html, actual_url, host, visited, page_queue, external, depth + 1
                                )
                    except Exception:
                        pass

            while page_queue and fetched < _MAX_PAGES:
                batch: list[tuple[str, int]] = []
                while page_queue and len(batch) < _CONCURRENCY:
                    batch.append(page_queue.popleft())
                await asyncio.gather(*[crawl(url, d) for url, d in batch])

            # ── Phase 3: download JS files ────────────────────────────
            map_urls: list[str] = []
            map_seen: set[str] = set()

            def _register_map(js_url: str, body: str, headers: dict) -> None:
                map_ref = headers.get('x-sourcemap') or headers.get('sourcemap', '')
                if not map_ref:
                    matches = _MAP_COMMENT_RE.findall(body)
                    map_ref = matches[-1] if matches else ''
                if map_ref and not map_ref.startswith('data:'):
                    map_url = urljoin(js_url, map_ref)
                    if map_url not in map_seen:
                        map_seen.add(map_url)
                        map_urls.append(map_url)

            async def fetch_js(url: str) -> None:
                async with semaphore:
                    try:
                        resp = await asyncio.wait_for(
                            client.get(url, headers=_JS_HEADERS),
                            timeout=self.timeout,
                        )
                        if resp.status_code == 200:
                            body = resp.text
                            _mine_literals(body)
                            _register_map(url, body, dict(resp.headers))
                    except Exception:
                        pass

            await asyncio.gather(*[fetch_js(u) for u in js_urls[:_MAX_JS_FILES]])

            # ── Phase 4: download .map files ──────────────────────────
            async def fetch_map(url: str) -> None:
                async with semaphore:
                    try:
                        resp = await asyncio.wait_for(
                            client.get(url, headers=_JS_HEADERS),
                            timeout=self.timeout,
                        )
                        if resp.status_code == 200:
                            _mine_literals(resp.text)
                    except Exception:
                        pass

            if map_urls:
                await asyncio.gather(*[fetch_map(u) for u in map_urls[:_MAX_MAP_FILES]])

            # ── Phase 5: download stylesheets ─────────────────────────
            async def fetch_css(url: str) -> None:
                async with semaphore:
                    try:
                        resp = await asyncio.wait_for(
                            client.get(url),
                            timeout=self.timeout,
                        )
                        if resp.status_code == 200:
                            body = resp.text
                            for rx in (_CSS_URL_RE, _CSS_IMPORT_RE):
                                for m in rx.finditer(body):
                                    ref = m.group(1).strip()
                                    if not ref or ref.startswith('data:'):
                                        continue
                                    if len(literal_urls) >= _MAX_LITERAL_URLS:
                                        return
                                    # relative to the stylesheet, per the CSS spec
                                    literal_urls.add(urljoin(url, ref))
                    except Exception:
                        pass

            if css_urls:
                await asyncio.gather(*[fetch_css(u) for u in css_urls[:_MAX_CSS_FILES]])

        self.extras['urls_external'].update(external)
        all_found = (
            visited
            | set(js_urls[:_MAX_JS_FILES])
            | set(map_urls[:_MAX_MAP_FILES])
            | set(css_urls[:_MAX_CSS_FILES])
            | literal_urls
        )
        return self._filter_urls(all_found, host)

    # ── Static helpers ────────────────────────────────────────────────

    @staticmethod
    def _enqueue_links(
        html: str,
        base_url: str,
        host: str,
        visited: set[str],
        queue: deque,
        external: set[str],
        depth: int,
    ) -> None:
        soup = BeautifulSoup(html, 'html.parser')
        hrefs: list[str] = []
        for tag in soup.find_all('a', href=True, limit=500):
            hrefs.append(tag['href'])
        for tag in soup.find_all('link', href=True, limit=100):
            hrefs.append(tag['href'])
        for href in hrefs:
            if not href or len(href) <= 3:
                continue
            url = urljoin(base_url, href)
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                continue
            canonical = parsed._replace(fragment='', query='').geturl()
            if not _in_scope(canonical, host):
                if len(external) < _MAX_EXTERNAL_URLS:
                    external.add(canonical)
                continue
            if canonical not in visited:
                visited.add(canonical)
                queue.append((canonical, depth))

    @staticmethod
    def _collect_css(
        html: str,
        base_url: str,
        host: str,
        seen: set[str],
        out: list[str],
        external: set[str],
    ) -> None:
        """Queue in-scope <link rel=stylesheet> hrefs for later url() mining."""
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup.find_all('link', href=True):
            rel = ' '.join(tag.get('rel', []))
            as_attr = tag.get('as', '')
            if 'stylesheet' not in rel and as_attr != 'style':
                continue
            url = urljoin(base_url, tag.get('href', ''))
            if urlparse(url).scheme not in ('http', 'https'):
                continue
            if not _in_scope(url, host):
                if len(external) < _MAX_EXTERNAL_URLS:
                    external.add(url)
                continue
            if url not in seen:
                seen.add(url)
                out.append(url)

    @staticmethod
    def _collect_js(
        html: str,
        base_url: str,
        host: str,
        seen: set[str],
        out: list[str],
        external: set[str],
    ) -> None:
        soup = BeautifulSoup(html, 'html.parser')
        raw: list[str] = []
        for tag in soup.find_all('script', src=True):
            src = tag.get('src', '')
            if src:
                raw.append(src)
        for tag in soup.find_all('link', href=True):
            rel = ' '.join(tag.get('rel', []))
            as_attr = tag.get('as', '')
            href = tag.get('href', '')
            if href and ('script' in as_attr or 'modulepreload' in rel):
                raw.append(href)
        for src in raw:
            url = urljoin(base_url, src)
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                continue
            if not _in_scope(url, host):
                if len(external) < _MAX_EXTERNAL_URLS:
                    external.add(url)
                continue
            if url not in seen:
                seen.add(url)
                out.append(url)
