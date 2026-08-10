"""
Arquivo.pt — the Portuguese web archive.

Exposes a CDX API compatible with the Wayback Machine's, including the
`*.domain` wildcard, and needs no API key. It is an independent crawl of the
web with far deeper coverage of Portuguese-language content (PT and, to a
lesser extent, BR) than the Internet Archive has, so it surfaces historical
URLs the `wayback` source misses.

Reference: https://arquivo.pt/api
"""
import json

from sources.base import BaseSource, Target

_BASE_URL = 'https://arquivo.pt/wayback/cdx'
_LIMIT = 10000
_MAX_PAGES = 5


class Arquivopt(BaseSource):
    NAME = 'arquivopt'
    DESCRIPTION = 'Arquivo.pt — Portuguese web archive (CDX API, no auth)'
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        urls: set[str] = set()
        self.timeout = max(self.timeout, 45)  # the archive can be slow

        try:
            async with self._make_client() as client:
                for page in range(_MAX_PAGES):
                    params = {
                        'url': f'*.{target.host}',
                        'output': 'json',
                        'limit': str(_LIMIT),
                        'collapse': 'urlkey',
                        'page': str(page),
                    }
                    resp = await self._get(client, _BASE_URL, params=params)
                    if resp.status_code != 200:
                        break
                    body = resp.text.strip()
                    if not body:
                        break

                    before = len(urls)
                    for line in body.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except (json.JSONDecodeError, ValueError):
                            continue
                        url = entry.get('url', '') if isinstance(entry, dict) else ''
                        if url:
                            urls.add(url)
                    # No new rows means the pagination is exhausted
                    if len(urls) == before:
                        break
        except Exception as e:
            self._log_exc(e)

        return self._filter_urls(urls, target.host)
