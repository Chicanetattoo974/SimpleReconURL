from sources.base import BaseSource, Target
from core.config import get_key


class URLScan(BaseSource):
    NAME = 'urlscan'
    DESCRIPTION = 'URLScan.io scan history — scanned page and task URLs for the target host'
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        url = f'https://urlscan.io/api/v1/search/?q=domain:{target.host}&size=200'
        urls: set[str] = set()
        headers = {}
        api_key = get_key('urlscan')
        if api_key:
            headers['API-Key'] = api_key

        try:
            async with self._make_client(headers=headers) as client:
                resp = await self._get(client, url)
                if resp.status_code != 200:
                    return set()
                for result in resp.json().get('results', []):
                    page = result.get('page', {})
                    task_url = result.get('task', {}).get('url', '')
                    if page.get('url'):
                        urls.add(page['url'])
                    if task_url:
                        urls.add(task_url)
        except Exception as e:
            self._log_exc(e)
        return self._filter_urls(urls, target.host)
