"""
Bing Search — indexed URLs for the target host (best-effort).

Adapted from string-x's clc/bing.py, including its URL templates and header
set.

>>> HEADS-UP: Bing was serving a Cloudflare Turnstile challenge instead of
>>> results at the time this module was written. Testing the exact string-x
>>> templates with full browser headers returned a 200 with a ~70KB shell page
>>> and ZERO result links.

It ships anyway because the block is IP/reputation-based, not permanent: it
may work from a different network, from a residential IP, or through
`--proxy`. When it is blocked the module simply contributes nothing — it
never errors and never blocks a run. If you see 0 results from this source,
that is the expected outcome today, not a bug.

Compare with `googlecse` and `yahoo`, which do return results without auth.
"""
import re
from urllib.parse import quote_plus, unquote

from sources.base import BaseSource, Target
from sources.passive._search_common import (
    browser_headers, drop_engine_chrome, polite_sleep, site_query,
)

_TEMPLATES = (
    'https://www.bing.com/search?q={dork}&form=DEEPSH&shm=cr&shajax=2',
    'https://www.bing.com/search?q={dork}&filt=rf&first=1&FORM=PERE',
    'https://www.bing.com/search?q={dork}&filt=rf&first=11&FORM=PERE',
    'https://www.bing.com/search?q={dork}&filt=rf&first=21&FORM=PERE',
)

# Direct result links, plus Bing's base64 /ck/a redirect wrapper (u=a1<b64>)
_HREF_RE = re.compile(r'href="(https?://[^"]+)"')
_CK_RE = re.compile(r'[?&]u=a1([A-Za-z0-9_\-]+)')


class Bing(BaseSource):
    NAME = 'bing'
    DESCRIPTION = 'Bing Search — indexed URLs (best-effort: usually challenged)'
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        dork = quote_plus(site_query(target.host))
        urls: set[str] = set()

        try:
            async with self._make_client(
                headers=browser_headers(
                    referer='https://www.bing.com/',
                    configured_ua=self.user_agent,
                )
            ) as client:
                for i, template in enumerate(_TEMPLATES):
                    try:
                        resp = await self._get(client, template.format(dork=dork))
                    except Exception as e:
                        self._log_exc(e)
                        break
                    if resp.status_code != 200:
                        break

                    page_urls = self._extract(resp.text)
                    if page_urls:
                        urls |= page_urls
                        self._vlog(1, f'template {i + 1}: {len(page_urls)} url(s)')

                    if i + 1 < len(_TEMPLATES):
                        await polite_sleep()
        except Exception as e:
            self._log_exc(e)

        if not urls:
            self._vlog(1, 'no results — Bing is most likely serving a bot challenge')
        return self._filter_urls(drop_engine_chrome(urls, target.host), target.host)

    # ------------------------------------------------------------------

    @staticmethod
    def _extract(html: str) -> set[str]:
        html = re.sub(r'</?strong>', '', html)
        found: set[str] = set(_HREF_RE.findall(html))

        # /ck/a?...&u=a1<base64url> wrappers
        import base64
        for token in _CK_RE.findall(html):
            try:
                padded = token + '=' * (-len(token) % 4)
                decoded = base64.urlsafe_b64decode(padded).decode('utf-8', 'ignore')
            except Exception:
                continue
            if decoded.startswith(('http://', 'https://')):
                found.add(unquote(decoded))
        return found
