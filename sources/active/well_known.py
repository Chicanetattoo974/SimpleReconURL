"""
.well-known/ harvesting (active source).

RFC 8615 reserves /.well-known/ for machine-readable metadata, and several of
those documents are effectively URL directories:

  openid-configuration        every OAuth/OIDC endpoint of the target
  oauth-authorization-server  same, for plain OAuth 2.0
  security.txt                policy / contact / hall-of-fame URLs
  apple-app-site-association  the deep-link PATHS handled by the iOS app
  assetlinks.json             the Android equivalent
  host-meta / nodeinfo        service discovery links

The Apple/Android files are the interesting ones for recon: they enumerate
paths the mobile app talks to, which frequently are not linked anywhere on
the website. They contain paths (not URLs), so they get joined to the origin.

Because this makes direct HTTP requests to the target it lives in sources/active/.
"""
import asyncio
import json
import re
from urllib.parse import urljoin, urlparse

from core.assets import load_lines
from sources.base import BaseSource, Target

_TEXT_URL_RE = re.compile(r'''https?://[^\s'"<>)\]]+''')
_MAX_URLS = 1000
_CONCURRENCY = 5


class Well_known(BaseSource):
    NAME = 'well_known'
    SCOPE = 'origin'   # /.well-known/* is defined per origin
    DESCRIPTION = (
        'Active: .well-known/ harvesting — OIDC endpoints, security.txt, '
        'and mobile deep-link paths (apple-app-site-association, assetlinks)'
    )
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        well_known_paths = load_lines('well_known_paths.txt')
        if not well_known_paths:
            self._vlog(1, 'no probe paths — assets/txt/well_known_paths.txt missing or empty')
            return set()

        urls: set[str] = set()
        seed = urlparse(target.url)
        origin = f'{seed.scheme}://{seed.netloc}'

        semaphore = asyncio.Semaphore(_CONCURRENCY)

        async def probe(client, path: str) -> None:
            doc_url = urljoin(origin, path)
            async with semaphore:
                try:
                    resp = await asyncio.wait_for(
                        client.get(doc_url), timeout=self.timeout
                    )
                except Exception:
                    return
                if resp.status_code != 200:
                    return
                body = resp.text
                # An SPA that returns index.html for everything would otherwise
                # make every probe look like a hit.
                if '<html' in body[:200].lower():
                    return
                self._vlog(1, f'found {path}')
                urls.add(doc_url)

                try:
                    data = json.loads(body)
                except (json.JSONDecodeError, ValueError):
                    # plain-text documents (security.txt, dnt-policy)
                    for m in _TEXT_URL_RE.finditer(body):
                        urls.add(m.group(0).rstrip('.,;)'))
                    return

                self._walk_json(data, origin, urls)
                self._deep_links(data, origin, urls)

        try:
            async with self._make_client(verify=False) as client:
                await asyncio.gather(*[probe(client, p) for p in well_known_paths])
        except Exception as e:
            self._log_exc(e)

        return self._filter_urls(urls, target.host)

    # ------------------------------------------------------------------

    @staticmethod
    def _walk_json(node, origin: str, urls: set[str]) -> None:
        """Collect every absolute URL sitting anywhere in the document."""
        if len(urls) >= _MAX_URLS:
            return
        if isinstance(node, str):
            if node.startswith(('http://', 'https://')):
                urls.add(node)
        elif isinstance(node, dict):
            for value in node.values():
                Well_known._walk_json(value, origin, urls)
        elif isinstance(node, list):
            for value in node:
                Well_known._walk_json(value, origin, urls)

    @staticmethod
    def _deep_links(data, origin: str, urls: set[str]) -> None:
        """Turn apple-app-site-association / assetlinks paths into URLs.

        AASA entries look like {"paths": ["/promo/*", "NOT /admin/*"]} or the
        newer {"components": [{"/": "/promo/*"}]}. Wildcards are stripped to
        the containing directory — '/promo/*' is reported as '/promo/'.
        """
        if not isinstance(data, dict):
            return

        raw_paths: list[str] = []
        details = data.get('applinks', {}).get('details') if isinstance(data.get('applinks'), dict) else None
        for entry in details or []:
            if not isinstance(entry, dict):
                continue
            raw_paths.extend(p for p in entry.get('paths', []) if isinstance(p, str))
            for comp in entry.get('components', []) or []:
                if isinstance(comp, dict) and isinstance(comp.get('/'), str):
                    raw_paths.append(comp['/'])

        for path in raw_paths:
            if len(urls) >= _MAX_URLS:
                return
            path = path.strip()
            if path.upper().startswith('NOT '):   # exclusion rule, not a path
                continue
            path = path.split('*')[0]
            if path.startswith('/') and len(path) > 1:
                urls.add(urljoin(origin, path))
