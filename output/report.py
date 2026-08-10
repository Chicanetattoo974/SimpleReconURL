"""
Markdown report renderer for SimpleReconURL.

Converts the list of per-target result dicts (produced by Engine.run_target())
into a human-readable Markdown document suitable for delivering to clients,
pasting into GitHub issues/PRs, or viewing in any Markdown renderer.

Pure function — no I/O, no global state.
"""
from __future__ import annotations

from datetime import datetime


# ── Section builders ──────────────────────────────────────────────────────────

def _esc(s: str) -> str:
    """Escape pipe characters inside table cells."""
    return str(s).replace('|', '\\|')


def _status_badge(status) -> str:
    if status is None:
        return '—'
    try:
        s = int(status)
    except (TypeError, ValueError):
        return str(status)
    if 200 <= s < 300:
        return f'`{s}` ✅'
    if 300 <= s < 400:
        return f'`{s}` ↪'
    if 400 <= s < 500:
        return f'`{s}` ⚠'
    if 500 <= s < 600:
        return f'`{s}` 🔴'
    return f'`{s}`'


def _header(seed: str, sources: dict, urls: set, live: dict) -> str:
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    source_list = ', '.join(f'`{s}`' for s in sorted(sources)) if sources else '—'
    live_count = sum(1 for i in live.values() if i.get('status') is not None)
    return (
        f'# Reconnaissance Report — {seed}\n\n'
        f'**Date:** {ts}  \n'
        f'**Sources:** {source_list}  \n'
        f'**URLs discovered:** {len(urls)}  \n'
        f'**Live URLs:** {live_count} / {len(urls)}'
    )


def _summary_table(urls: set, live: dict, extra_external: set) -> str:
    statuses = [i.get('status') for i in live.values()]
    c_2xx = sum(1 for s in statuses if s is not None and 200 <= s < 300)
    c_3xx = sum(1 for s in statuses if s is not None and 300 <= s < 400)
    c_4xx = sum(1 for s in statuses if s is not None and 400 <= s < 500)
    c_5xx = sum(1 for s in statuses if s is not None and 500 <= s < 600)
    c_dead = sum(1 for s in statuses if s is None)

    rows = [
        ('URLs discovered', len(urls)),
        ('Live — 2xx',  c_2xx),
        ('Redirects — 3xx', c_3xx),
        ('Client errors — 4xx', c_4xx),
        ('Server errors — 5xx', c_5xx),
        ('Unreachable', c_dead),
        ('External URLs (out of scope)', len(extra_external)),
    ]

    lines = ['## Summary', '', '| Metric | Value |', '|--------|-------|']
    for label, value in rows:
        lines.append(f'| {label} | {value} |')
    return '\n'.join(lines)


def _live_urls_table(live: dict) -> str:
    live_urls = {u: i for u, i in live.items() if i.get('status') is not None}
    if not live_urls:
        return '## Live URLs\n\n*No live URLs found.*'

    lines = [
        '## Live URLs', '',
        '| URL | Status | Title | Server | ms |',
        '|-----|--------|-------|--------|----|',
    ]
    for url in sorted(live_urls):
        info   = live_urls[url]
        status = _status_badge(info.get('status'))
        title  = _esc((info.get('title') or '')[:50])
        server = _esc((info.get('server') or '—')[:30])
        ms     = info.get('response_ms')
        ms_str = f'{ms}' if ms is not None else '—'
        lines.append(
            f'| `{_esc(url)}` | {status} | {title} | {server} | {ms_str} |'
        )
    return '\n'.join(lines)


def _duplicate_bodies_section(live: dict) -> str:
    hgroups: dict[str, list[str]] = {}
    for url, info in live.items():
        h = info.get('body_hash')
        if h:
            hgroups.setdefault(h, []).append(url)
    duplicate_bodies = {h: sorted(u) for h, u in hgroups.items() if len(u) > 1}
    if not duplicate_bodies:
        return ''
    lines = [
        '## Duplicate Body Hashes',
        '',
        '*URLs sharing identical response bodies — possible duplicate/soft-404 pages.*',
        '',
        '| Hash | URLs |',
        '|------|------|',
    ]
    for h, u in sorted(duplicate_bodies.items()):
        urls_str = ', '.join(f'`{_esc(x)}`' for x in u)
        lines.append(f'| `{h}` | {urls_str} |')
    return '\n'.join(lines)


def _all_urls_section(urls: set) -> str:
    if not urls:
        return ''
    lines = ['## All URLs', '', '```']
    lines.extend(sorted(urls))
    lines.append('```')
    return '\n'.join(lines)


def _extras_section(extras: dict) -> str:
    external = sorted(extras.get('urls_external', set()))
    assets = sorted(extras.get('urls_assets', set()))
    if not external and not assets:
        return ''

    def _block(title: str, urls: list) -> list:
        out = [f'### {title}', '', '```']
        out += urls[:50]  # cap to avoid enormous reports
        if len(urls) > 50:
            out.append(f'… and {len(urls) - 50} more')
        out += ['```', '']
        return out

    lines = ['## Extras', '']
    if external:
        lines += _block('External URLs (out of scope, not followed)', external)
    if assets:
        # Distinct from the block above on purpose: these ARE in scope and ARE
        # in the main URL list; they were just never fetched.
        lines += _block('Asset URLs (in scope, found but not crawled)', assets)
    return '\n'.join(lines).rstrip()


def _sources_section(sources: dict) -> str:
    if not sources:
        return ''
    lines = [
        '## Source Contributions', '',
        '| Source | URLs |',
        '|--------|------|',
    ]
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        lines.append(f'| `{src}` | {count} |')
    return '\n'.join(lines)


def _rounds_section(rounds: int, url_rounds: dict) -> str:
    """Per-round breakdown; only rendered when --recursive actually looped."""
    if rounds < 2 or not url_rounds:
        return ''
    per_round: dict[int, int] = {}
    for round_no in url_rounds.values():
        per_round[round_no] = per_round.get(round_no, 0) + 1
    lines = [
        '## Recursive Rounds', '',
        '| Round | New URLs |',
        '|-------|----------|',
    ]
    for round_no in sorted(per_round):
        lines.append(f'| {round_no} | {per_round[round_no]} |')
    lines += ['', f'*{rounds} round(s) executed; each one re-seeded with the previous round\'s new URLs.*']
    return '\n'.join(lines)


# ── Public API ────────────────────────────────────────────────────────────────

def render_markdown(results: list[dict]) -> str:
    """
    Render a Markdown reconnaissance report from a list of Engine result dicts.

    Returns the full report as a single string.
    """
    sections: list[str] = []

    for result in results:
        seed           = result.get('seed', '')
        urls           = result.get('urls', set()) or set()
        live           = result.get('live', {}) or {}
        sources        = result.get('sources', {}) or {}
        extras         = result.get('extras', {}) or {}
        extra_external = extras.get('urls_external', set()) or set()

        sections.append(_header(seed, sources, urls, live))
        sections.append(_summary_table(urls, live, extra_external))

        sections.append(_live_urls_table(live))

        dup_sec = _duplicate_bodies_section(live)
        if dup_sec:
            sections.append(dup_sec)

        sections.append(_all_urls_section(urls))

        extras_sec = _extras_section(extras)
        if extras_sec:
            sections.append(extras_sec)

        src_sec = _sources_section(sources)
        if src_sec:
            sections.append(src_sec)

        rounds_sec = _rounds_section(result.get('rounds', 1) or 1, result.get('url_rounds', {}) or {})
        if rounds_sec:
            sections.append(rounds_sec)

        sections.append('---\n\n*Generated by [SimpleReconURL v1](https://github.com/osintbrazuca/SimpleReconURL)*')

    return '\n\n---\n\n'.join(sections)
