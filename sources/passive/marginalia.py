"""
Marginalia Search — an independent, non-commercial web index.

Marginalia runs its own crawler with an index deliberately biased toward the
small, non-commercial web that Google and Bing rank into oblivion. That makes
it a genuinely different corpus: it surfaces pages the other sources never see.

Uses the official API with the documented **public** key, so no credentials are
needed:  https://api.marginalia.nu/public/search/<query>

Two things to keep in mind, both measured rather than assumed:

  * The public API takes a **free-text query, not a `site:` filter** — passing
    `site:example.com` returns an error. Querying the bare host works, but only
    a fraction of the hits are actually ON the target (measured: 1-3 of 20);
    the rest merely mention it. `_filter_urls` sorts that out, so the
    in-scope yield is modest by design. The value is the uniqueness of the
    index, not the volume.
  * The service is small and rate-limits hard. Hitting it in a loop earns an
    explicit "currently barraged by queries from bots" page after roughly three
    queries, so paging is kept short, requests are paced, and any failure just
    ends the pagination quietly.
"""
import json

from sources.base import BaseSource, Target
from sources.passive._search_common import (
    browser_headers, drop_engine_chrome, polite_sleep,
)

# 'public' is Marginalia's documented open key — not a placeholder to fill in.
_ENDPOINT = 'https://api.marginalia.nu/public/search/{query}'
_MAX_PAGES = 2


class Marginalia(BaseSource):
    NAME = 'marginalia'
    DESCRIPTION = 'Marginalia Search — independent non-commercial index (no auth)'
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        from urllib.parse import quote

        urls: set[str] = set()
        query = quote(target.host, safe='')

        try:
            async with self._make_client(
                headers=browser_headers(configured_ua=self.user_agent)
            ) as client:
                for page in range(1, _MAX_PAGES + 1):
                    url = _ENDPOINT.format(query=query)
                    if page > 1:
                        url = f'{url}?page={page}'
                    try:
                        resp = await self._get(client, url)
                    except Exception as e:
                        self._log_exc(e)
                        break
                    if resp.status_code != 200:
                        self._vlog(1, f'HTTP {resp.status_code} — likely rate limited')
                        break
                    try:
                        data = json.loads(resp.text)
                    except (json.JSONDecodeError, ValueError):
                        # The rate-limit response is an HTML page, not JSON
                        self._vlog(1, 'non-JSON response — rate limited, stopping')
                        break

                    results = data.get('results') or []
                    if not results:
                        break
                    for item in results:
                        if isinstance(item, dict) and item.get('url'):
                            urls.add(item['url'])

                    total_pages = data.get('pages') or 1
                    if page >= min(total_pages, _MAX_PAGES):
                        break
                    await polite_sleep()
        except Exception as e:
            self._log_exc(e)

        return self._filter_urls(drop_engine_chrome(urls, target.host), target.host)
