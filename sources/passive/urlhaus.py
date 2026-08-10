"""
URLhaus (abuse.ch) — malicious URL database.

Queries the URLhaus API for all recorded URLs on the target host and its
subdomains. The URLs themselves are malicious samples, but real ones —
useful for surfacing paths/hosts not visible from other sources.

No API key required.  Reference: https://urlhaus-api.abuse.ch/
"""
from sources.base import BaseSource, Target

_BASE_URL = 'https://urlhaus-api.abuse.ch/v1/host/'


class Urlhaus(BaseSource):
    NAME = 'urlhaus'
    DESCRIPTION = 'URLhaus abuse.ch — malicious URL database (free, no auth)'
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        urls: set[str] = set()

        try:
            async with self._make_client() as client:
                # URLhaus uses POST with form-encoded body
                resp = await client.post(_BASE_URL, data={'host': target.host})
                if self.verbose >= 2:
                    self._vlog(2, f'HTTP {resp.status_code}')
                if resp.status_code != 200:
                    return set()

                data = resp.json()
                if data.get('query_status') == 'no_results':
                    return set()

                for url_entry in data.get('urls', []):
                    url_str = (url_entry.get('url') or '').strip()
                    if url_str:
                        urls.add(url_str)

        except Exception as e:
            self._log_exc(e)

        return self._filter_urls(urls, target.host)
