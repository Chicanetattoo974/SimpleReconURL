from sources.base import BaseSource, Target
from core.config import get_key


class VirusTotal(BaseSource):
    NAME = 'virustotal'
    DESCRIPTION = 'VirusTotal — URLs observed for the target host'
    API_TOKEN_IS_REQUIREMENT = True

    async def fetch(self, target: Target) -> set[str]:
        api_key = get_key('virustotal')
        if not api_key:
            return set()

        # VT v3 domain relationship: URLs seen referencing this host.
        # https://docs.virustotal.com/reference/domain-urls
        url = f'https://www.virustotal.com/api/v3/domains/{target.host}/urls'
        urls: set[str] = set()
        headers = {'x-apikey': api_key}

        try:
            async with self._make_client(headers=headers) as client:
                cursor = None
                while True:
                    params: dict = {'limit': 40}
                    if cursor:
                        params['cursor'] = cursor
                    resp = await self._get(client, url, params=params)
                    if resp.status_code != 200:
                        self._vlog(1, f'HTTP {resp.status_code} — check the endpoint/key')
                        break
                    data = resp.json()
                    for entry in data.get('data', []):
                        entry_url = entry.get('attributes', {}).get('url', '')
                        if entry_url:
                            urls.add(entry_url)
                    cursor = data.get('meta', {}).get('cursor')
                    if not cursor:
                        break
        except Exception as e:
            self._log_exc(e)
        return self._filter_urls(urls, target.host)
