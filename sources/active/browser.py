"""
Headless browser network capture (active source).

Opens the seed URL in a hidden Chromium instance and records every network
request the page makes — XHR/fetch API calls, dynamically injected scripts,
tracking beacons, lazy-loaded assets, WebSocket handshakes. This is traffic
that only exists at runtime, so the static extractors (_page_extractor,
spider) cannot see it no matter how thoroughly they parse the markup.

Flow:
  1. Launch headless Chromium and open the seed URL exactly as given.
  2. Record every request fired while the page loads and settles.
  3. Scroll once to trigger lazy-loaded / infinite-scroll requests.

In-scope requests are returned; third-party ones (CDNs, analytics, fonts)
are routed to self.extras['urls_external'] by _filter_urls, the same way
spider handles cross-origin links.

Requires the optional `playwright` package plus its browser binary:
    pip install -r requirements-browser.txt
    playwright install chromium
Without it the source self-disables with a single message instead of failing.

Because this drives a real browser against the target it lives in sources/active/.
"""
from sources.base import BaseSource, Target

# Best-effort wait for late XHR after 'load' fires (ms). Bounded on purpose:
# pages with polling or open WebSockets never reach a true network-idle state.
_NETWORK_IDLE_MS = 5000
# Settle time after scrolling, for lazy-loaded resources to start fetching (ms).
_POST_SCROLL_MS = 1500
# Hard cap on captured requests — an ad-heavy page can fire thousands.
_MAX_REQUESTS = 3000

_INSTALL_HINT = (
    'playwright not installed — run: '
    'pip install -r requirements-browser.txt && playwright install chromium'
)


class Browser(BaseSource):
    NAME = 'browser'
    SCOPE = 'url'   # renders the exact page in a headless browser
    DESCRIPTION = (
        'Active: headless browser — captures every network request the page '
        'makes at runtime (XHR/fetch, beacons, lazy-loaded assets)'
    )
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            self._vlog(1, _INSTALL_HINT)
            return set()

        # Populated by the request event handler. Lives outside the try below so
        # a navigation failure still returns whatever was captured before it.
        urls: set[str] = set()

        def _on_request(request) -> None:
            if len(urls) >= _MAX_REQUESTS:
                return
            urls.add(request.url)
            self._vlog(2, f'{request.method} {request.resource_type} {request.url}')

        try:
            async with async_playwright() as pw:
                launch_kwargs: dict = {'headless': True}
                if self.proxy:
                    launch_kwargs['proxy'] = {'server': self.proxy}
                browser = await pw.chromium.launch(**launch_kwargs)
                try:
                    context = await browser.new_context(
                        user_agent=self.user_agent,
                        ignore_https_errors=True,
                    )
                    page = await context.new_page()
                    page.on('request', _on_request)

                    await page.goto(
                        target.url,
                        wait_until='load',
                        timeout=self.timeout * 1000,
                    )

                    # Best-effort: a timeout here is normal and not an error —
                    # everything captured so far is still valid.
                    try:
                        await page.wait_for_load_state(
                            'networkidle', timeout=_NETWORK_IDLE_MS
                        )
                    except Exception:
                        pass

                    try:
                        await page.evaluate(
                            'window.scrollTo(0, document.body.scrollHeight)'
                        )
                        await page.wait_for_timeout(_POST_SCROLL_MS)
                    except Exception:
                        pass
                finally:
                    await browser.close()
        except Exception as e:
            self._log_exc(e)

        self._vlog(1, f'captured {len(urls)} request(s)')
        return self._filter_urls(urls, target.host)
