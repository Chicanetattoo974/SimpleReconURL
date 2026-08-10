"""
Yahoo Search — indexed URLs for the target host.

Adapted from string-x's clc/yahoo.py. Yahoo is currently the one major engine
that still answers a plain `site:` query without a challenge, which makes it
the scraping counterpart to the API-free `googlecse` source.

Results are not linked directly: Yahoo wraps every hit in a redirect of the
form `.../RU=<urlencoded target>/RK=...`, so the real URL is recovered by
pulling the RU= segment and unquoting it. Yahoo's own navigation is wrapped
the same way, but those are on yahoo.com and get dropped by _filter_urls.

Pagination through the `b=` offset returns genuinely different result sets
(verified: 4 pages yielded 31 unique URLs versus 9 for a single page).
"""
import re
from urllib.parse import quote_plus, unquote

from sources.base import BaseSource, Target
from sources.passive._search_common import (
    browser_headers, drop_engine_chrome, polite_sleep, site_query,
)

_TEMPLATE = (
    'https://search.yahoo.com/search?fr2=piv-web&p={dork}&b={offset}'
    '&pz=7&bct=0&xargs=0&ei=UTF-8'
)
# Result offsets, matching string-x's paging (1, 8, 15, 22 ...)
_OFFSETS = (1, 8, 15, 22)

# Yahoo's redirect wrapper: /RU=<urlencoded url>/RK=...
_RU_RE = re.compile(r'/RU=([^/]+)/R[A-Za-z]')


class Yahoo(BaseSource):
    NAME = 'yahoo'
    DESCRIPTION = 'Yahoo Search — indexed URLs for the target host (no auth)'
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        dork = quote_plus(site_query(target.host))
        urls: set[str] = set()

        try:
            async with self._make_client(
                headers=browser_headers(
                    referer='https://search.yahoo.com/',
                    configured_ua=self.user_agent,
                )
            ) as client:
                for i, offset in enumerate(_OFFSETS):
                    url = _TEMPLATE.format(dork=dork, offset=offset)
                    try:
                        resp = await self._get(client, url)
                    except Exception as e:
                        self._log_exc(e)
                        break
                    if resp.status_code != 200:
                        break

                    page_urls = self._extract(resp.text)
                    if not page_urls:
                        break
                    urls |= page_urls
                    self._vlog(1, f'page b={offset}: {len(page_urls)} url(s)')

                    if i + 1 < len(_OFFSETS):
                        await polite_sleep()
        except Exception as e:
            self._log_exc(e)

        return self._filter_urls(drop_engine_chrome(urls, target.host), target.host)

    # ------------------------------------------------------------------

    @staticmethod
    def _extract(html: str) -> set[str]:
        """Recover the real URLs from Yahoo's /RU=.../RK= redirect wrappers."""
        found: set[str] = set()
        for raw in _RU_RE.findall(html):
            decoded = unquote(raw)
            if decoded.startswith(('http://', 'https://')):
                found.add(decoded)
        return found
