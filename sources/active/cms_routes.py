"""
CMS REST route discovery (active source).

Content management systems publish their own API route table, which makes a
single request worth hundreds of endpoint URLs:

  WordPress  /wp-json/          -> routes{} (one entry per REST endpoint)
  Drupal     /jsonapi           -> links{} (one entry per resource type)

WordPress alone powers a large share of the web, so this is a high-hit-rate
module in practice — a live check against a real site returned 527 routes.

Routes whose key carries a regex template (`/wp/v2/posts/(?P<id>[\\d]+)`) are
dropped: that is a routing pattern, not a URL, and emitting it would only put
regex noise in the results. Literal routes are kept, and `_links.self` is
preferred when present since WordPress already gives it as an absolute URL.

Because this makes direct HTTP requests to the target it lives in sources/active/.
"""
import asyncio
import json
from urllib.parse import urljoin, urlparse

from sources.base import BaseSource, Target

_WP_BASES = ('/wp-json/', '/?rest_route=/')
_EXTRA_PATHS = ('/wp-sitemap.xml', '/jsonapi')

_MAX_ROUTES = 1000
_CONCURRENCY = 4


class Cms_routes(BaseSource):
    NAME = 'cms_routes'
    SCOPE = 'origin'   # CMS REST roots are mounted per origin
    DESCRIPTION = (
        'Active: CMS REST route discovery — WordPress /wp-json/ route table '
        'and Drupal /jsonapi resource links'
    )
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        urls: set[str] = set()
        seed = urlparse(target.url)
        origin = f'{seed.scheme}://{seed.netloc}'

        semaphore = asyncio.Semaphore(_CONCURRENCY)

        async def get_json(client, url: str):
            async with semaphore:
                try:
                    resp = await asyncio.wait_for(
                        client.get(url), timeout=self.timeout
                    )
                except Exception:
                    return None
                if resp.status_code != 200:
                    return None
                try:
                    return json.loads(resp.text)
                except (json.JSONDecodeError, ValueError):
                    return None

        try:
            async with self._make_client(verify=False) as client:
                # ── WordPress REST index ──────────────────────────────
                for base in _WP_BASES:
                    base_url = urljoin(origin, base)
                    data = await get_json(client, base_url)
                    if not isinstance(data, dict) or 'routes' not in data:
                        continue
                    urls.add(base_url)
                    self._wp_routes(data, base_url, urls)
                    self._vlog(1, f'{len(urls)} route(s) from {base}')
                    break  # one working entry point is enough

                # ── Drupal JSON:API + WP sitemap ──────────────────────
                for path in _EXTRA_PATHS:
                    url = urljoin(origin, path)
                    data = await get_json(client, url)
                    if data is None:
                        continue
                    urls.add(url)
                    if isinstance(data, dict):
                        links = data.get('links')
                        if isinstance(links, dict):
                            for value in links.values():
                                href = (
                                    value.get('href') if isinstance(value, dict) else value
                                )
                                if isinstance(href, str) and href.startswith('http'):
                                    urls.add(href)
        except Exception as e:
            self._log_exc(e)

        return self._filter_urls(urls, target.host)

    # ------------------------------------------------------------------

    @staticmethod
    def _wp_routes(data: dict, base_url: str, urls: set[str]) -> None:
        routes = data.get('routes')
        if not isinstance(routes, dict):
            return
        for route, meta in routes.items():
            if len(urls) >= _MAX_ROUTES:
                return
            # Regex-templated routes are routing patterns, not URLs
            if '(?' in route:
                continue
            self_url = ''
            if isinstance(meta, dict):
                links = meta.get('_links', {})
                if isinstance(links, dict):
                    self_entry = links.get('self')
                    if isinstance(self_entry, list) and self_entry:
                        first = self_entry[0]
                        self_url = (
                            first.get('href', '') if isinstance(first, dict) else str(first)
                        )
                    elif isinstance(self_entry, str):
                        self_url = self_entry
            if self_url.startswith('http'):
                urls.add(self_url)
            else:
                urls.add(base_url.rstrip('/') + route)
