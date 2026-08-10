"""
Brave Search API — indexed URLs for the target host.

Search engines know URLs that no archive or crawl will surface: pages that are
linked only from third-party sites. This is the tool's only search-engine
source, and it uses the official API on purpose — scraping DuckDuckGo now
returns a CAPTCHA and Bing scraping is fragile, so an authenticated API is the
only reliable route.

Brave offers a free tier (rate-limited, roughly 1 query/second), which is why
results are paginated sequentially rather than concurrently.

Key: `brave` in config/api_keys.json — https://brave.com/search/api/
"""
import asyncio

from sources.base import BaseSource, Target
from core.config import get_key

_ENDPOINT = 'https://api.search.brave.com/res/v1/web/search'
_PAGE_SIZE = 20
_MAX_PAGES = 5   # free tier is small; 5 pages ≈ 100 results


class Brave(BaseSource):
    NAME = 'brave'
    DESCRIPTION = 'Brave Search API — indexed URLs for the target host'
    API_TOKEN_IS_REQUIREMENT = True

    async def fetch(self, target: Target) -> set[str]:
        api_key = get_key('brave')
        if not api_key:
            return set()

        urls: set[str] = set()
        headers = {
            'X-Subscription-Token': api_key,
            'Accept': 'application/json',
        }

        try:
            async with self._make_client(headers=headers) as client:
                for page in range(_MAX_PAGES):
                    params = {
                        'q': f'site:{target.host}',
                        'count': str(_PAGE_SIZE),
                        'offset': str(page),
                    }
                    resp = await self._get(client, _ENDPOINT, params=params)
                    if resp.status_code == 429:
                        self._vlog(1, 'rate limited — stopping pagination')
                        break
                    if resp.status_code != 200:
                        self._vlog(1, f'HTTP {resp.status_code} — check the API key')
                        break

                    results = (resp.json().get('web') or {}).get('results') or []
                    if not results:
                        break
                    for item in results:
                        url = item.get('url', '') if isinstance(item, dict) else ''
                        if url:
                            urls.add(url)

                    if len(results) < _PAGE_SIZE:
                        break
                    # Free tier allows ~1 request/second
                    await asyncio.sleep(1)
        except Exception as e:
            self._log_exc(e)

        return self._filter_urls(urls, target.host)
