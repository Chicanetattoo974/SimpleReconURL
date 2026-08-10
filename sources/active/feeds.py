"""
RSS / Atom / JSON Feed discovery and parsing (active source).

Feeds enumerate a site's content URLs directly, which makes them a cheap way
to pull in article/post URLs that a depth-limited crawl would never reach.

Discovery is two-pronged: the declared <link rel="alternate"> on the seed page
(authoritative) plus the conventional feed paths (for sites that serve a feed
without advertising it).

Because this makes direct HTTP requests to the target it lives in sources/active/.
"""
import asyncio
import json
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from core.assets import load_lines
from sources.base import BaseSource, Target

_FEED_TYPES = (
    'application/rss+xml',
    'application/atom+xml',
    'application/feed+json',
    'application/json',
    'text/xml',
)

_MAX_FEEDS = 10
_MAX_ENTRIES = 1000
_CONCURRENCY = 4


class Feeds(BaseSource):
    NAME = 'feeds'
    SCOPE = 'origin'   # feed autodiscovery resolves to the same origin feeds
    DESCRIPTION = (
        'Active: RSS/Atom/JSON feed discovery — pulls entry URLs from the '
        "site's own content feeds"
    )
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        urls: set[str] = set()
        seed = urlparse(target.url)
        origin = f'{seed.scheme}://{seed.netloc}'

        try:
            async with self._make_client(verify=False) as client:
                candidates = await self._discover(client, target.url, origin)
                semaphore = asyncio.Semaphore(_CONCURRENCY)

                async def parse_feed(feed_url: str) -> None:
                    async with semaphore:
                        try:
                            resp = await asyncio.wait_for(
                                client.get(feed_url), timeout=self.timeout
                            )
                        except Exception:
                            return
                        if resp.status_code != 200:
                            return
                        body = resp.text
                        found = self._parse(body, feed_url)
                        if found:
                            urls.add(feed_url)
                            urls.update(found)
                            self._vlog(1, f'{len(found)} entry URL(s) from {feed_url}')

                await asyncio.gather(
                    *[parse_feed(u) for u in list(candidates)[:_MAX_FEEDS]]
                )
        except Exception as e:
            self._log_exc(e)

        return self._filter_urls(urls, target.host)

    # ------------------------------------------------------------------

    async def _discover(self, client, seed_url: str, origin: str) -> set[str]:
        """Feed URLs declared by the page, plus the conventional paths."""
        feed_paths = load_lines('feed_paths.txt')
        if not feed_paths:
            self._vlog(1, 'no feed paths — assets/txt/feed_paths.txt missing or empty')
        candidates: set[str] = {urljoin(origin, p) for p in feed_paths}
        try:
            resp = await asyncio.wait_for(client.get(seed_url), timeout=self.timeout)
            if resp.status_code < 400:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for tag in soup.find_all('link', href=True):
                    rel = ' '.join(tag.get('rel', []))
                    if 'alternate' not in rel:
                        continue
                    if tag.get('type', '').lower() in _FEED_TYPES:
                        candidates.add(urljoin(str(resp.url), tag['href']))
        except Exception:
            pass
        return candidates

    @staticmethod
    def _parse(body: str, feed_url: str) -> set[str]:
        """Extract entry URLs from RSS, Atom or JSON Feed content."""
        found: set[str] = set()

        stripped = body.lstrip()
        if stripped.startswith('{'):
            try:
                data = json.loads(body)
            except (json.JSONDecodeError, ValueError):
                return found
            for item in (data.get('items') or [])[:_MAX_ENTRIES]:
                if isinstance(item, dict):
                    for key in ('url', 'external_url', 'id'):
                        value = item.get(key)
                        if isinstance(value, str) and value.startswith('http'):
                            found.add(value)
                            break
            return found

        if '<rss' not in stripped[:400] and '<feed' not in stripped[:400] \
                and '<rdf' not in stripped[:400].lower():
            return found  # not a feed (probably an HTML 404 page)

        soup = BeautifulSoup(body, 'html.parser')
        # RSS: <item><link>URL</link>  |  Atom: <entry><link href="URL"/>
        for tag in soup.find_all('link'):
            href = tag.get('href')
            if href:
                found.add(urljoin(feed_url, href))
            else:
                text = (tag.get_text() or '').strip()
                if text.startswith('http'):
                    found.add(text)
            if len(found) >= _MAX_ENTRIES:
                break
        for tag in soup.find_all('guid'):
            text = (tag.get_text() or '').strip()
            if text.startswith('http'):
                found.add(text)
        return found
