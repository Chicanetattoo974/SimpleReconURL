"""
Google Search (direct scrape) — indexed URLs for the target host (best-effort).

Adapted from string-x's clc/google.py.

>>> HEADS-UP: google.com/search returned ZERO result links at the time this
>>> module was written — a ~90KB JavaScript shell page, with or without a
>>> consent cookie and browser headers.

It ships anyway because the block is IP/reputation-based and may lift from a
different network or through `--proxy`. When blocked it contributes nothing,
without erroring.

**For Google coverage that actually works today, use `googlecse`** — it
reaches Google's index through public Custom Search Engines and needs no
credentials.
"""
import re
from urllib.parse import quote_plus, unquote, urlparse, parse_qs

from sources.base import BaseSource, Target
from sources.passive._search_common import (
    browser_headers, drop_engine_chrome, polite_sleep, site_query,
)

_TEMPLATE = 'https://www.google.com/search?q={dork}&num=30&hl=en&start={start}'
_STARTS = (0, 30, 60)

# Modern Google links results directly; older/basic layouts use /url?q=
_HREF_RE = re.compile(r'href="(https?://[^"]+)"')
_URLQ_RE = re.compile(r'/url\?q=([^"&]+)')

# Consent interstitial cookie — cheap and harmless, occasionally unblocks EU IPs
_CONSENT_COOKIE = {'CONSENT': 'YES+cb.20220301-11-p0.en+FX+111'}


class Google(BaseSource):
    NAME = 'google'
    DESCRIPTION = 'Google Search scrape — indexed URLs (best-effort: usually blocked)'
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        dork = quote_plus(site_query(target.host))
        urls: set[str] = set()

        try:
            async with self._make_client(
                headers=browser_headers(
                    referer='https://www.google.com/',
                    configured_ua=self.user_agent,
                ),
                cookies=_CONSENT_COOKIE,
            ) as client:
                for i, start in enumerate(_STARTS):
                    try:
                        resp = await self._get(
                            client, _TEMPLATE.format(dork=dork, start=start)
                        )
                    except Exception as e:
                        self._log_exc(e)
                        break
                    if resp.status_code != 200:
                        break

                    page_urls = self._extract(resp.text)
                    if not page_urls:
                        break
                    urls |= page_urls
                    self._vlog(1, f'start={start}: {len(page_urls)} url(s)')

                    if i + 1 < len(_STARTS):
                        await polite_sleep()
        except Exception as e:
            self._log_exc(e)

        if not urls:
            self._vlog(1, 'no results — google.com is most likely blocking; try googlecse')
        return self._filter_urls(drop_engine_chrome(urls, target.host), target.host)

    # ------------------------------------------------------------------

    @staticmethod
    def _extract(html: str) -> set[str]:
        found: set[str] = set(_HREF_RE.findall(html))
        for raw in _URLQ_RE.findall(html):
            decoded = unquote(raw)
            if decoded.startswith(('http://', 'https://')):
                found.add(decoded)
        return found
