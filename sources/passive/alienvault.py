from sources.base import BaseSource, Target
from core.config import get_key


class AlienVault(BaseSource):
    NAME = 'alienvault'
    DESCRIPTION = 'AlienVault OTX — URLs observed for the target host'
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        url_list = (
            f'https://otx.alienvault.com/api/v1/indicators/domain/{target.host}/url_list'
            '?limit=500&page=1'
        )
        urls: set[str] = set()
        headers = {}
        api_key = get_key('alienvault_otx')
        self.timeout = 30

        if api_key:
            headers['X-OTX-API-KEY'] = api_key

        try:
            async with self._make_client(headers=headers) as client:
                resp = await self._get(client, url_list)
                if resp.status_code != 200:
                    return set()
                for entry in resp.json().get('url_list', []):
                    entry_url = entry.get('url', '')
                    if entry_url:
                        urls.add(entry_url)
        except Exception as e:
            self._log_exc(e)
        return self._filter_urls(urls, target.host)
