"""
Shared helpers for the search-engine sources.

Underscore-prefixed on purpose: sources/__init__.py's loader skips modules
starting with '_', so this stays an importable helper instead of becoming a
selectable source (same trick as sources/_page_extractor.py).

Search engines are the one place where the tool's own identity hurts: the
default User-Agent (`SimpleReconURL/1`) gets a request blocked or challenged
immediately. These helpers provide a realistic desktop browser fingerprint and
polite pacing, both of which the string-x collectors rely on as well.
"""
import asyncio
import random

from core.assets import load_lines

# Default from cli/parser.py — used to tell "user left it alone" from
# "user explicitly asked for this UA".
_TOOL_DEFAULT_UA = 'SimpleReconURL/1'

# Data lives in assets/txt/ so it can be edited without touching code.
_UA_FILE = 'user_agents.txt'
_ENGINE_DOMAIN_FILE = 'search_engine_domains.txt'


def random_ua() -> str:
    """A random desktop User-Agent, or '' when the UA list is unavailable."""
    uas = load_lines(_UA_FILE)
    return random.choice(uas) if uas else ''


def effective_ua(configured_ua: str) -> str:
    """Pick the User-Agent to send to a search engine.

    Honours `--user-agent` when the user actually set one; otherwise rotates a
    browser UA, because the tool's default is an instant block here.

    If assets/txt/user_agents.txt is missing or empty there is nothing to
    rotate — fall back to whatever UA is configured rather than raising. A
    request has to carry *some* User-Agent, so "disable the feature" is not an
    option here the way it is for a probe-path list.
    """
    if configured_ua and configured_ua != _TOOL_DEFAULT_UA:
        return configured_ua
    return random_ua() or configured_ua or _TOOL_DEFAULT_UA


def browser_headers(referer: str = '', configured_ua: str = '') -> dict:
    """Browser-like headers for a search-engine request."""
    headers = {
        'User-Agent': effective_ua(configured_ua),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1',
    }
    if referer:
        headers['Referer'] = referer
    return headers


async def polite_sleep(base: float = 2.0) -> None:
    """Pause between paged requests, with jitter.

    Hammering result pages back-to-back is what trips the anti-bot checks;
    string-x uses the same ~2s + jitter pacing.
    """
    await asyncio.sleep(base + random.uniform(0.4, 1.4))


def site_query(host: str) -> str:
    """The single dork every engine module sends."""
    return f'site:{host}'


def drop_engine_chrome(urls: set[str], host: str) -> set[str]:
    """Remove the engine's own navigation links from *urls*.

    Anything inside the target's scope is always kept — otherwise scanning a
    target that happens to be one of these domains would silently return
    nothing.

    The domain list lives in assets/txt/search_engine_domains.txt; if it is
    missing the filter degrades to a no-op rather than dropping anything.
    """
    from urllib.parse import urlparse

    engine_domains = load_lines(_ENGINE_DOMAIN_FILE)
    if not engine_domains:
        return set(urls)

    kept: set[str] = set()
    for url in urls:
        try:
            h = (urlparse(url).hostname or '').lower().rstrip('.')
        except Exception:
            continue
        if not h:
            continue
        if h == host or h.endswith(f'.{host}'):
            kept.add(url)
            continue
        if any(h == d or h.endswith(f'.{d}') for d in engine_domains):
            continue
        kept.add(url)
    return kept
