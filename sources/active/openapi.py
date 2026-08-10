"""
OpenAPI / Swagger specification discovery (active source).

Probes the well-known locations where API specs get exposed, then turns the
spec's `paths` object into full endpoint URLs. On a target that leaves its
spec reachable this is the single highest-yield module in the tool: one
request can reveal the entire API surface.

Handles both dialects:
  OpenAPI 3.x  -> `servers[].url` (may be relative to the spec's own URL)
  Swagger 2.0  -> `schemes[] + host + basePath`

Only JSON specs are parsed. YAML specs are common too, but parsing them would
add a PyYAML dependency to a project that has deliberately kept its
dependency list to two packages — so `.yaml` endpoints are probed and, if the
body is not JSON, skipped rather than guessed at.

Templated paths (`/users/{id}`) are emitted as-is. They are not fetchable
URLs, but they ARE the API surface, which is the whole reason this module
exists — do not "fix" this by dropping them.

Because this makes direct HTTP requests to the target it lives in sources/active/.
"""
import asyncio
import json
from urllib.parse import urljoin, urlparse

from core.assets import load_lines
from sources.base import BaseSource, Target

_MAX_ENDPOINTS = 2000
_CONCURRENCY = 5


class Openapi(BaseSource):
    NAME = 'openapi'
    SCOPE = 'origin'   # probes a fixed spec-path list against the origin
    DESCRIPTION = (
        'Active: OpenAPI/Swagger spec discovery — turns the API spec into '
        'full endpoint URLs'
    )
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        spec_paths = load_lines('openapi_paths.txt')
        if not spec_paths:
            self._vlog(1, 'no probe paths — assets/txt/openapi_paths.txt missing or empty')
            return set()

        urls: set[str] = set()
        seed = urlparse(target.url)
        origin = f'{seed.scheme}://{seed.netloc}'

        semaphore = asyncio.Semaphore(_CONCURRENCY)

        async def probe(client, path: str) -> None:
            spec_url = urljoin(origin, path)
            async with semaphore:
                try:
                    resp = await asyncio.wait_for(
                        client.get(spec_url), timeout=self.timeout
                    )
                except Exception:
                    return
                if resp.status_code != 200:
                    return
                try:
                    spec = json.loads(resp.text)
                except (json.JSONDecodeError, ValueError):
                    return  # YAML or an HTML error page — see module docstring
                if not isinstance(spec, dict) or 'paths' not in spec:
                    return
                self._vlog(1, f'spec found at {spec_url}')
                urls.add(spec_url)
                self._expand(spec, spec_url, origin, urls)

        try:
            async with self._make_client(verify=False) as client:
                await asyncio.gather(*[probe(client, p) for p in spec_paths])
        except Exception as e:
            self._log_exc(e)

        return self._filter_urls(urls, target.host)

    # ------------------------------------------------------------------

    def _expand(self, spec: dict, spec_url: str, origin: str, urls: set[str]) -> None:
        """Combine the spec's base URL(s) with every entry in `paths`."""
        bases: list[str] = []

        # OpenAPI 3.x — servers[].url, possibly relative ("/api/v2")
        servers = spec.get('servers')
        if isinstance(servers, list):
            for server in servers:
                if isinstance(server, dict) and server.get('url'):
                    bases.append(urljoin(spec_url, str(server['url'])))

        # Swagger 2.0 — schemes + host + basePath
        if not bases:
            host = spec.get('host')
            base_path = spec.get('basePath', '') or ''
            if host:
                schemes = spec.get('schemes') or ['https']
                for scheme in schemes:
                    bases.append(f'{scheme}://{host}{base_path}')
            elif base_path:
                bases.append(urljoin(origin, base_path))

        if not bases:
            bases = [origin]

        paths = spec.get('paths')
        if not isinstance(paths, dict):
            return
        for raw_path in paths:
            if len(urls) >= _MAX_ENDPOINTS:
                return
            path = str(raw_path)
            if not path.startswith('/'):
                continue
            for base in bases:
                # keep the base's own path segment: urljoin('.../api', '/x')
                # would drop it, so concatenate instead
                urls.add(base.rstrip('/') + path)
