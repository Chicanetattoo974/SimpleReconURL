import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

import core.colors as colors

_DEFAULT_UA = 'SimpleReconURL/1'
# Per-source cap on collected URLs — wayback/commoncrawl can return 10k+ entries
_MAX_URLS_PER_SOURCE = 2000


@dataclass(frozen=True)
class Target:
    """A single scan target: the full seed URL plus its scope anchor (host)."""
    url: str    # full seed URL as given, e.g. 'https://example.com/blog/post-1?x=1'
    host: str   # lowercased hostname, e.g. 'example.com'

    @classmethod
    def from_url(cls, seed_url: str) -> 'Target':
        host = (urlparse(seed_url).hostname or '').lower().rstrip('.')
        return cls(url=seed_url, host=host)


class BaseSource(ABC):
    NAME: str = ''
    DESCRIPTION: str = ''
    API_TOKEN_IS_REQUIREMENT: bool = False
    # How much of the Target this source actually reads. Only consulted by the
    # --recursive round loop, to avoid re-running a source with an input that
    # is provably identical to one it already handled:
    #   'host'   -> only target.host          (every passive source, robots_sitemap)
    #   'origin' -> only scheme://netloc      (probes a fixed path set per site)
    #   'url'    -> the full URL, path & query included
    # Default is 'host' because that is what 16 of the current sources do; a
    # new source that reads target.url must say so or it will run once per host.
    SCOPE: str = 'host'

    def __init__(
        self,
        timeout: int = 30,
        rate_limit: int = 0,
        verbose: int = 0,
        proxy: str | None = None,
        user_agent: str = _DEFAULT_UA,
    ) -> None:
        self.timeout = timeout
        self.rate_limit = rate_limit
        self.verbose = verbose
        self.proxy = proxy
        self.user_agent = user_agent
        # Semaphore to cap concurrent requests per source (0 = unlimited)
        self._sem: asyncio.Semaphore | None = (
            asyncio.Semaphore(rate_limit) if rate_limit > 0 else None
        )
        # Out-of-scope URLs found during fetch(); populated by _filter_urls().
        self.extras: dict[str, set] = {
            'urls_external': set(),
        }

    def _make_client(self, **kwargs) -> httpx.AsyncClient:
        """
        Return a pre-configured AsyncClient with proxy and User-Agent applied.

        Callers can override any default by passing kwargs; 'headers' are
        merged (caller values win) rather than replaced.
        """
        merged_headers: dict = {'User-Agent': self.user_agent}
        if 'headers' in kwargs:
            merged_headers.update(kwargs.pop('headers'))
        client_kwargs: dict = {
            'timeout': self.timeout,
            'follow_redirects': True,
            'headers': merged_headers,
        }
        if self.proxy:
            client_kwargs['proxy'] = self.proxy
        client_kwargs.update(kwargs)
        return httpx.AsyncClient(**client_kwargs)

    def _vlog(self, level: int, msg: str) -> None:
        """Print *msg* when self.verbose >= *level*."""
        if self.verbose >= level:
            print(colors.format_msg(f'[*] [{self.NAME}] {msg}'))

    def _log_exc(self, e: Exception) -> None:
        """Print exception class and message at verbose level 4+."""
        if self.verbose >= 4:
            print(colors.format_msg(f'[!] [{self.NAME}] {type(e).__name__}: {e}'))

    async def _get(self, client, url: str, **kwargs):
        """Wrap client.get(); enforces rate_limit, logs HTTP status and body preview."""
        if self._sem:
            async with self._sem:
                return await self._do_get(client, url, **kwargs)
        return await self._do_get(client, url, **kwargs)

    async def _do_get(self, client, url: str, **kwargs):
        resp = await client.get(url, **kwargs)
        if self.verbose >= 2:
            self._vlog(2, f'HTTP {resp.status_code}')
        if self.verbose >= 3:
            preview = resp.text[:400].replace('\n', ' ')
            self._vlog(3, preview)
        return resp

    @abstractmethod
    async def fetch(self, target: Target) -> set[str]:
        """Fetch URLs related to *target*. Must always return a set of
        in-scope full URLs (never raises)."""

    def _filter_urls(self, urls: set[str], host: str) -> set[str]:
        """Keep only URLs whose hostname is *host* or a subdomain of it.

        Out-of-scope URLs (different host entirely) are routed into
        self.extras['urls_external'] so callers can optionally surface them
        (-v 3) instead of being silently dropped.
        """
        result: set[str] = set()
        for u in urls:
            if not u or len(result) >= _MAX_URLS_PER_SOURCE:
                continue
            candidate = u.strip()
            if not candidate:
                continue
            if '://' not in candidate:
                candidate = f'http://{candidate}'
            try:
                h = (urlparse(candidate).hostname or '').lower().rstrip('.')
            except Exception:
                continue
            if not h:
                continue
            if h == host or h.endswith(f'.{host}'):
                result.add(candidate)
            elif len(self.extras['urls_external']) < _MAX_URLS_PER_SOURCE:
                self.extras['urls_external'].add(candidate)
        return result
