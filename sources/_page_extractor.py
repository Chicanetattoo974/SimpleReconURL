"""
Default page-URL extractor.

Fetches the seed URL exactly as given and extracts every URL referenced on
that single page: element attributes (href/src/action/data/...), srcset
candidate lists, meta refresh targets, CSS url() inside <style> blocks and
style= attributes, and URLs sitting in HTML comments.

This is the tool's core "by default" behavior — placed here (underscore-
prefixed) rather than in sources/passive|active/ so sources/__init__.py's
dynamic loader never registers it: it can't be excluded via
--exclude/--sources, doesn't show up in --list-sources, and always runs first
in core/engine.py::Engine.run_target().

Deliberately makes exactly ONE HTTP request. Linked stylesheets and JS bundles
are referenced here but never downloaded — that is the spider's job. Keeping
this module to a single request is what makes `--profile fast` genuinely mean
"just the seed page".
"""
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Comment

from sources.base import BaseSource, Target

# (tag, attribute) pairs whose value is a single URL
_LINK_ATTRS = (
    ('a', 'href'),
    ('link', 'href'),
    ('script', 'src'),
    ('img', 'src'),
    ('form', 'action'),
    ('iframe', 'src'),
    ('source', 'src'),
    ('video', 'src'),
    ('audio', 'src'),
    ('track', 'src'),
    ('embed', 'src'),
    ('object', 'data'),
    ('area', 'href'),
    ('input', 'src'),
    ('video', 'poster'),
)

# Attributes holding a comma-separated candidate list ("a.png 1x, b.png 2x")
_SRCSET_ATTRS = (('img', 'srcset'), ('source', 'srcset'), ('img', 'data-srcset'))

_CSS_URL_RE = re.compile(r'''url\(\s*['"]?([^'")\s]+)['"]?\s*\)''', re.IGNORECASE)
_META_REFRESH_RE = re.compile(r"""url\s*=\s*([^\s;'"]+)""", re.IGNORECASE)
_COMMENT_URL_RE = re.compile(r'''https?://[^\s'"<>)\]]+''')

_SKIP_PREFIXES = ('#', 'javascript:', 'mailto:', 'tel:', 'data:', 'blob:', 'about:')


class PageExtractor(BaseSource):
    NAME = 'page'
    DESCRIPTION = 'Default: fetch the seed URL and extract every URL on the page'
    SCOPE = 'url'   # reads the exact page; this is what --recursive re-feeds
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        urls: set[str] = set()
        try:
            async with self._make_client(verify=False) as client:
                resp = await self._get(client, target.url)
                if resp.status_code < 400:
                    base_url = str(resp.url)
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    self._collect(soup, base_url, urls)
        except Exception as e:
            self._log_exc(e)
        return self._filter_urls(urls, target.host)

    # ------------------------------------------------------------------

    def _collect(self, soup: BeautifulSoup, base_url: str, urls: set[str]) -> None:
        def add(raw: str) -> None:
            raw = (raw or '').strip()
            if not raw or raw.startswith(_SKIP_PREFIXES):
                return
            candidate = urljoin(base_url, raw)
            if urlparse(candidate).scheme in ('http', 'https'):
                urls.add(candidate)

        # Plain single-URL attributes
        for tag_name, attr in _LINK_ATTRS:
            for tag in soup.find_all(tag_name, {attr: True}):
                add(tag.get(attr, ''))

        # srcset: "img-480.png 480w, img-800.png 800w" -> take the URL part
        for tag_name, attr in _SRCSET_ATTRS:
            for tag in soup.find_all(tag_name, {attr: True}):
                for candidate in tag.get(attr, '').split(','):
                    add(candidate.strip().split()[0] if candidate.strip() else '')

        # <meta http-equiv="refresh" content="0; url=/next">
        for tag in soup.find_all('meta', attrs={'http-equiv': True}):
            if tag.get('http-equiv', '').lower() != 'refresh':
                continue
            m = _META_REFRESH_RE.search(tag.get('content', ''))
            if m:
                add(m.group(1).strip('\'"'))

        # CSS url() in <style> blocks and inline style= attributes
        for style_tag in soup.find_all('style'):
            for m in _CSS_URL_RE.finditer(style_tag.get_text() or ''):
                add(m.group(1))
        for tag in soup.find_all(style=True):
            for m in _CSS_URL_RE.finditer(tag.get('style', '')):
                add(m.group(1))

        # Absolute URLs left behind in HTML comments (dev/staging leftovers)
        for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
            for m in _COMMENT_URL_RE.finditer(str(comment)):
                add(m.group(0).rstrip('.,;)'))
