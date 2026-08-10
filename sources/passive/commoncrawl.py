# -*- coding: utf-8 -*-
"""
Common Crawl CDX API source.

Queries the latest available Common Crawl index for all URLs under *.{host}.
Complements the Wayback Machine with independent crawl data.

No API key required.
Reference: https://index.commoncrawl.org/
"""

import json

from sources.base import BaseSource, Target

_INDEX_URL = 'https://index.commoncrawl.org/collinfo.json'
# Note: Common Crawl CDX endpoint requires the '-index' suffix after the collection ID
_CDX_TEMPLATE = 'https://index.commoncrawl.org/{index}-index?url=*.{host}&output=json&limit=5000&fl=url&collapse=urlkey'

# Common Crawl publishes ~126 crawl indexes, each a separate snapshot in time.
# Querying only the newest one misses everything that vanished before it, so a
# few of the most recent indexes are swept instead. Straight trade-off: each
# extra index is one more (slow) CDX request.
_MAX_INDEXES = 3


class Commoncrawl(BaseSource):
    NAME = 'commoncrawl'
    DESCRIPTION = 'Common Crawl CDX API - historical web crawl URL index'
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        urls: set[str] = set()

        async with self._make_client() as client:
            # Step 1: fetch the list of available indexes (listed newest-first)
            try:
                resp = await self._get(client, _INDEX_URL)
                if resp.status_code != 200:
                    return set()
                indexes = resp.json()
                if not indexes:
                    return set()
                index_ids = [
                    idx.get('id', '') for idx in indexes[:_MAX_INDEXES] if idx.get('id')
                ]
                if not index_ids:
                    return set()
            except Exception as exc:
                self._log_exc(exc)
                return set()

            self._vlog(1, f'querying {len(index_ids)} index(es): {", ".join(index_ids)}')

            # Step 2: query CDX for all URLs under *.host, one call per index
            for index_id in index_ids:
                cdx_url = _CDX_TEMPLATE.format(index=index_id, host=target.host)
                try:
                    resp = await self._get(client, cdx_url)
                    if resp.status_code != 200:
                        continue

                    for line in resp.text.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            url = entry.get('url', '')
                        except (json.JSONDecodeError, AttributeError):
                            # Some CDX endpoints return plain text lines
                            url = line

                        if url:
                            urls.add(url)

                except Exception as exc:
                    self._log_exc(exc)

        return self._filter_urls(urls, target.host)
