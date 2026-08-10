"""
Live URL verification.

Probes each discovered URL directly (it already carries its own scheme) and
records basic liveness metadata: HTTP status, title, server header, content
length, a body hash (useful for spotting duplicate-content/soft-404 pages),
and response time.
"""

import asyncio
import hashlib
import re
import time

import httpx

import core.colors as colors


def _extract_title(html: str) -> str:
    match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip()[:100] if match else ''


async def verify_live(
    urls: set[str],
    timeout: int = 5,
    quiet: bool = False,
    concurrency: int = 50,
    proxy: str | None = None,
) -> dict[str, dict]:
    """
    Probe each URL as given; on a connection-level failure, retry once with
    the other scheme (http<->https) in case the server only speaks one.

    Returns a dict mapping the original url -> response metadata. Live URLs
    have a non-None 'status' key.
    """
    results: dict[str, dict] = {}
    semaphore = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(
        max_connections=concurrency,
        max_keepalive_connections=max(1, concurrency // 2),
    )

    client_kwargs: dict = {
        'timeout': timeout,
        'follow_redirects': True,
        'verify': False,  # intentional: recon may hit self-signed certs
        'limits': limits,
    }
    if proxy:
        client_kwargs['proxy'] = proxy

    async with httpx.AsyncClient(**client_kwargs) as client:
        async def check(url: str) -> None:
            async with semaphore:
                candidates = [url]
                if url.startswith('https://'):
                    candidates.append('http://' + url[len('https://'):])
                elif url.startswith('http://'):
                    candidates.append('https://' + url[len('http://'):])

                for candidate in candidates:
                    try:
                        t_start = time.monotonic()
                        resp = await client.get(candidate)
                        entry: dict = {
                            'url': candidate,
                            'status': resp.status_code,
                            'title': _extract_title(resp.text),
                            'server': resp.headers.get('server', ''),
                            'content_length': len(resp.content),
                            'body_hash': hashlib.sha256(resp.content[:4096]).hexdigest()[:16],
                            'response_ms': int((time.monotonic() - t_start) * 1000),
                        }
                        results[url] = entry

                        if not quiet:
                            title_str = f' - {entry["title"]}' if entry['title'] else ''
                            print(colors.format_msg(
                                f'[LIVE] {url} → {resp.status_code}{title_str}'
                            ))
                        return
                    except Exception:
                        continue

                results[url] = {
                    'url': None, 'status': None, 'title': '', 'server': '',
                    'content_length': None, 'body_hash': None, 'response_ms': None,
                }

        await asyncio.gather(*[check(u) for u in urls])
    return results
