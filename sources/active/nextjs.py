"""
Next.js route extraction (active source).

A Next.js app keeps its entire route table inside the JS bundle, not in the
HTML. Minified chunks carry arrays like

    ["/[username]/[contractAddress]/[tokenId]/bid", "/admin/approve", ...]

which enumerate every page of the site, including admin areas and dynamic
routes that are linked from nowhere. This module goes after those, plus the
framework's own metadata artifacts.

The framework has two routers and they expose completely different things:

  Pages Router (legacy, still common on smaller targets)
    __NEXT_DATA__                              JSON blob in the HTML -> buildId
    /_next/static/<buildId>/_buildManifest.js  self.__BUILD_MANIFEST, whose KEYS
                                               are the complete route table
    /_next/data/<buildId>/<route>.json         per-route JSON data endpoints,
                                               frequently unauthenticated

  App Router (Next 13+, what most sites run today)
    self.__next_f.push([...])                  RSC flight data streamed into the
                                               HTML, containing real route paths
    no __NEXT_DATA__, no _buildManifest.js

Both are handled. Route templates (`/[username]/...`, `/blog/[...slug]`) are
emitted as-is: they are not fetchable URLs, but they ARE the route surface,
which is the entire point of the module — same call already documented in
sources/active/openapi.py for `/users/{id}`.

Overlaps with `spider` on chunk downloads by design; there is no cross-source
cache, and the duplicated traffic costs less than inventing one.

Because this makes direct HTTP requests to the target it lives in sources/active/.
"""
import asyncio
import json
import re
from urllib.parse import urljoin, urlparse

from sources.base import BaseSource, Target

# Cheap fingerprints — any one of these means "this is Next.js"
_MARKERS = ('/_next/', '__NEXT_DATA__', 'self.__next_f')

_NEXT_DATA_RE = re.compile(
    r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S | re.I
)
_CHUNK_RE = re.compile(r'["\'(](/_next/static/[^"\'()\s\\]+\.js)')
# Quoted absolute paths, including Next dynamic segments: [id], [...slug]
_ROUTE_RE = re.compile(r'''["'`](/[A-Za-z0-9_\-./\[\]~%:]{1,180})["'`]''')
# Build-manifest keys are the routes themselves
_MANIFEST_KEY_RE = re.compile(r'["\'](/[^"\']{0,180})["\']\s*:')

# Noise guards, same spirit as spider's: reject protocol-relative and
# all-numeric fragments, and require at least one letter.
_REJECT_RE = re.compile(r'^/(?:/|\d+(?:[./]\d+)*$)')
_HAS_ALPHA_RE = re.compile(r'[A-Za-z]')
# Asset paths are already collected as URLs; as *routes* they are noise.
_ASSET_SUFFIXES = (
    '.js', '.css', '.map', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp',
    '.avif', '.ico', '.woff', '.woff2', '.ttf', '.otf', '.mp4', '.webm',
)

_MAX_CHUNKS = 40
_MAX_ROUTES = 1500
_CONCURRENCY = 5


class Nextjs(BaseSource):
    NAME = 'nextjs'
    SCOPE = 'origin'   # buildId and chunk manifest are per-site, not per-page
    DESCRIPTION = (
        'Active: Next.js route extraction — build manifest, RSC flight data '
        'and dynamic route templates mined from /_next/ chunks'
    )
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        seed = urlparse(target.url)
        origin = f'{seed.scheme}://{seed.netloc}'

        routes: set[str] = set()   # paths, joined to origin at the end
        urls: set[str] = set()     # already-absolute URLs

        try:
            async with self._make_client(verify=False) as client:
                # ── Detection: one request, no path probing ───────────
                try:
                    resp = await asyncio.wait_for(
                        client.get(target.url), timeout=self.timeout
                    )
                except Exception as e:
                    self._log_exc(e)
                    return set()
                html = resp.text if resp.status_code < 400 else ''
                if not any(marker in html for marker in _MARKERS):
                    self._vlog(1, 'not a Next.js app — nothing to do')
                    return set()

                build_id = ''

                # ── Pages Router: __NEXT_DATA__ ───────────────────────
                match = _NEXT_DATA_RE.search(html)
                if match:
                    try:
                        data = json.loads(match.group(1))
                    except (json.JSONDecodeError, ValueError):
                        data = None
                    if isinstance(data, dict):
                        build_id = str(data.get('buildId') or '')
                        page = data.get('page')
                        if isinstance(page, str) and page.startswith('/'):
                            routes.add(page)
                        self._walk(data, routes, urls)
                        self._vlog(1, f'Pages Router, buildId={build_id or "?"}')

                # ── App Router: RSC flight data + any quoted path ─────
                if not match:
                    self._vlog(1, 'App Router (no __NEXT_DATA__)')
                routes |= self._routes_from(html)

                # ── Build manifest (Pages Router): the whole route table ──
                if build_id:
                    routes |= await self._build_manifest(client, origin, build_id)

                # ── Chunks: where the route arrays actually live ──────
                chunks = [
                    urljoin(str(resp.url), c) for c in _CHUNK_RE.findall(html)
                ]
                chunks = list(dict.fromkeys(chunks))[:_MAX_CHUNKS]
                if chunks:
                    urls.update(chunks)
                    routes |= await self._mine_chunks(client, chunks)
        except Exception as e:
            self._log_exc(e)

        routes = {r for r in routes if self._is_route(r)}
        self._vlog(1, f'{len(routes)} route(s), {len(urls)} asset URL(s)')

        for route in list(routes)[:_MAX_ROUTES]:
            urls.add(urljoin(origin, route))
            # Pages Router exposes each route's data as JSON — often the
            # most interesting thing on the whole target.
            if build_id:
                suffix = 'index' if route == '/' else route.strip('/')
                urls.add(f'{origin}/_next/data/{build_id}/{suffix}.json')

        return self._filter_urls(urls, target.host)

    # ------------------------------------------------------------------

    @staticmethod
    def _is_route(path: str) -> bool:
        """Keep page-like paths, drop asset paths and obvious noise."""
        if not path.startswith('/') or len(path) < 2:
            return False
        if _REJECT_RE.match(path) or not _HAS_ALPHA_RE.search(path):
            return False
        if path.startswith('/_next/'):
            return False
        return not path.lower().endswith(_ASSET_SUFFIXES)

    @classmethod
    def _routes_from(cls, text: str) -> set[str]:
        return {m.group(1) for m in _ROUTE_RE.finditer(text)}

    @classmethod
    def _walk(cls, node, routes: set[str], urls: set[str]) -> None:
        """Collect paths and absolute URLs from anywhere in __NEXT_DATA__."""
        if isinstance(node, str):
            if node.startswith(('http://', 'https://')):
                urls.add(node)
            elif node.startswith('/') and len(node) > 1:
                routes.add(node)
        elif isinstance(node, dict):
            for value in node.values():
                cls._walk(value, routes, urls)
        elif isinstance(node, list):
            for value in node:
                cls._walk(value, routes, urls)

    async def _build_manifest(self, client, origin: str, build_id: str) -> set[str]:
        """Route table from _buildManifest.js (Pages Router only)."""
        found: set[str] = set()
        for name in ('_buildManifest.js', '_ssgManifest.js'):
            url = f'{origin}/_next/static/{build_id}/{name}'
            try:
                resp = await asyncio.wait_for(client.get(url), timeout=self.timeout)
            except Exception:
                continue
            if resp.status_code != 200:
                continue
            body = resp.text
            found |= {m.group(1) for m in _MANIFEST_KEY_RE.finditer(body)}
            found |= self._routes_from(body)
            self._vlog(1, f'{name}: {len(found)} route(s) so far')
        return found

    async def _mine_chunks(self, client, chunks: list[str]) -> set[str]:
        """Download the JS chunks and pull every quoted route out of them."""
        found: set[str] = set()
        semaphore = asyncio.Semaphore(_CONCURRENCY)

        async def grab(url: str) -> None:
            async with semaphore:
                try:
                    resp = await asyncio.wait_for(
                        client.get(url), timeout=self.timeout
                    )
                except Exception:
                    return
                if resp.status_code == 200:
                    found.update(self._routes_from(resp.text))

        await asyncio.gather(*[grab(u) for u in chunks])
        return found
