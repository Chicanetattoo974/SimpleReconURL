"""
PublicWWW — search engine over page SOURCE CODE.

Every other source in this tool searches text, archives or DNS-adjacent data.
PublicWWW indexes the actual HTML/JS/CSS of pages, which makes it a different
axis entirely: it finds URLs by what the markup *contains* rather than what the
page says. Useful for pulling in the target's pages via a shared snippet — an
Analytics ID, a bundle filename, a unique inline script.

Query used here is the plain host, which matches any page whose source
references it.

Key: `publicwww` in config/api_keys.json — https://publicwww.com/api.html
The `export=urls` parameter requires a paid plan; without a valid key the
endpoint answers with the site's HTML instead of a URL list, which is detected
and treated as "no results" rather than parsed as garbage.
"""
from urllib.parse import quote

from sources.base import BaseSource, Target
from core.config import get_key
from sources.passive._search_common import browser_headers, drop_engine_chrome

_ENDPOINT = 'https://publicwww.com/websites/{query}/'
_MAX_LINES = 2000


class Publicwww(BaseSource):
    NAME = 'publicwww'
    DESCRIPTION = 'PublicWWW — source-code search engine (finds pages by markup)'
    API_TOKEN_IS_REQUIREMENT = True

    async def fetch(self, target: Target) -> set[str]:
        api_key = get_key('publicwww')
        if not api_key:
            return set()

        urls: set[str] = set()
        url = _ENDPOINT.format(query=quote(f'"{target.host}"', safe=''))

        try:
            async with self._make_client(
                headers=browser_headers(configured_ua=self.user_agent)
            ) as client:
                resp = await self._get(
                    client, url, params={'export': 'urls', 'key': api_key}
                )
                if resp.status_code != 200:
                    self._vlog(1, f'HTTP {resp.status_code} — check the API key/plan')
                    return set()

                body = resp.text
                # A missing/invalid key returns the site's HTML page rather than
                # an error status, so detect that instead of parsing markup.
                if '<html' in body[:400].lower():
                    self._vlog(1, 'got HTML instead of a URL export — key or plan issue')
                    return set()

                for line in body.splitlines()[:_MAX_LINES]:
                    line = line.strip()
                    if line.startswith(('http://', 'https://')):
                        urls.add(line)
        except Exception as e:
            self._log_exc(e)

        return self._filter_urls(drop_engine_chrome(urls, target.host), target.host)
