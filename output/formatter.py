import csv
import io
import json
import sys
from datetime import datetime
from typing import Optional

import core.colors as colors
from output.graph import build_network_graph
from output.html_renderer import render_html
from output.report import render_markdown


def save_output(
    results: list[dict],
    fmt: str = 'txt',
    outfile: Optional[str] = None,
    quiet: bool = False,
    network_map: bool = False,
    network_html_file: Optional[str] = None,
) -> None:
    """
    Serialize *results* to the requested format and write to *outfile* or stdout.

    *results* is a list of per-seed dicts with keys:
        seed, urls (set), live (dict), sources (dict), url_sources (dict),
        extras (dict, optional)

    Formats: txt, json, csv, ndjson, html, markdown

    When *network_map* is True (or fmt == 'html'), each JSON record also carries
    a 'network' field with nodes/edges. When *network_html_file* is given, an
    HTML visualization is written there regardless of *fmt*.
    """
    # markdown primary output
    if fmt == 'markdown':
        md = render_markdown(results)
        if outfile:
            try:
                with open(outfile, 'w') as fh:
                    fh.write(md)
                    fh.write('\n')
                if not quiet:
                    print(colors.format_msg(f'\n[+] Markdown report saved to: {outfile}'))
            except OSError as exc:
                print(colors.format_msg(f'[!] Could not write to {outfile}: {exc}'), file=sys.stderr)
        else:
            print('\n' + md)
        if network_html_file:
            _write_html(results, network_html_file, quiet)
        return

    # html primary output: render and short-circuit; the side artifact
    # (network_html_file) still runs at the bottom if also set.
    if fmt == 'html':
        html_out = render_html(results)
        if outfile:
            try:
                with open(outfile, 'w') as fh:
                    fh.write(html_out)
                if not quiet:
                    print(colors.format_msg(f'\n[+] HTML page-link map saved to: {outfile}'))
            except OSError as exc:
                print(colors.format_msg(f'[!] Could not write to {outfile}: {exc}'), file=sys.stderr)
        else:
            print(html_out)
        if network_html_file and network_html_file != outfile:
            _write_html(results, network_html_file, quiet)
        return

    include_network = network_map or bool(network_html_file)
    segments: list[str] = []

    for result in results:
        seed = result['seed']
        urls: set[str] = result.get('urls', set())
        live: dict = result.get('live', {})
        sources: dict = result.get('sources', {})
        url_sources: dict = result.get('url_sources', {})
        extras: dict = result.get('extras', {})
        extra_external: set[str] = extras.get('urls_external', set())
        # Deliberately NOT appended to the csv/ndjson/txt bodies below: those
        # append externals because they are absent from the main url list.
        # Assets are already in it, so appending them would emit a second row
        # for the same URL. JSON and the markdown report name their sections,
        # so they can carry it without ambiguity.
        extra_assets: set[str] = extras.get('urls_assets', set())
        timestamp = datetime.now().isoformat()

        if fmt == 'json':
            live_urls: dict = {}
            for url, info in live.items():
                if info.get('status') is not None:
                    entry = {
                        'status': info.get('status'),
                        'title': info.get('title', ''),
                        'server': info.get('server', ''),
                        'content_length': info.get('content_length', 0),
                    }
                    if info.get('body_hash'):
                        entry['body_hash'] = info['body_hash']
                    if info.get('response_ms') is not None:
                        entry['response_ms'] = info['response_ms']
                    live_urls[url] = entry

            # Detect URLs returning identical body content (duplicate/soft-404 pages)
            _hgroups: dict[str, list[str]] = {}
            for url, info in live.items():
                h = info.get('body_hash')
                if h:
                    _hgroups.setdefault(h, []).append(url)
            duplicate_bodies = {
                h: sorted(u) for h, u in _hgroups.items() if len(u) > 1
            }

            data = {
                'seed': seed,
                'timestamp': timestamp,
                'total': len(urls),
                'urls': sorted(urls),
                'live_urls': live_urls,
                'sources': sources,
            }
            if extra_external or extra_assets:
                data['extras'] = {}
                if extra_external:
                    data['extras']['urls_external'] = sorted(extra_external)
                if extra_assets:
                    data['extras']['urls_assets'] = sorted(extra_assets)
            if duplicate_bodies:
                data['duplicate_bodies'] = duplicate_bodies
            if include_network:
                data['network'] = build_network_graph(result)
            segments.append(json.dumps(data, indent=2))

        elif fmt == 'csv':
            buf = io.StringIO()
            writer = csv.DictWriter(
                buf,
                fieldnames=[
                    'seed', 'url', 'type', 'source',
                    'status', 'title', 'server',
                    'body_hash', 'response_ms',
                ],
            )
            writer.writeheader()
            for url in sorted(urls):
                live_info = live.get(url, {})
                writer.writerow({
                    'seed': seed,
                    'url': url,
                    'type': 'url',
                    'source': url_sources.get(url, ''),
                    'status': live_info.get('status', ''),
                    'title': live_info.get('title', ''),
                    'server': live_info.get('server', ''),
                    'body_hash': live_info.get('body_hash', '') or '',
                    'response_ms': live_info.get('response_ms', '') if live_info.get('response_ms') is not None else '',
                })
            for url in sorted(extra_external):
                writer.writerow({
                    'seed': seed, 'url': url, 'type': 'url_external', 'source': '',
                    'status': '', 'title': '', 'server': '', 'body_hash': '', 'response_ms': '',
                })
            segments.append(buf.getvalue())

        elif fmt == 'ndjson':
            # One compact JSON line per URL — pipe-friendly
            for url in sorted(urls):
                live_info = live.get(url, {})
                record: dict = {'seed': seed, 'url': url, 'type': 'url'}
                if url_sources.get(url):
                    record['source'] = url_sources[url]
                if live_info.get('status') is not None:
                    record['status'] = live_info['status']
                    if live_info.get('title'):
                        record['title'] = live_info['title']
                    if live_info.get('server'):
                        record['server'] = live_info['server']
                    if live_info.get('body_hash'):
                        record['body_hash'] = live_info['body_hash']
                    if live_info.get('response_ms') is not None:
                        record['response_ms'] = live_info['response_ms']
                segments.append(json.dumps(record))
            for url in sorted(extra_external):
                segments.append(json.dumps({'seed': seed, 'url': url, 'type': 'url_external'}))

        else:  # txt (default)
            lines = list(sorted(urls))
            if extra_external:
                if not quiet:
                    lines.append('')
                    lines.append('# External URLs')
                lines.extend(sorted(extra_external))
            segments.append('\n'.join(lines))

    output = '\n'.join(segments)

    if outfile:
        try:
            with open(outfile, 'w') as fh:
                fh.write(output)
                if fmt != 'ndjson':
                    fh.write('\n')
            if not quiet:
                print(colors.format_msg(f'\n[+] Output saved to: {outfile}'))
        except OSError as exc:
            print(colors.format_msg(f'[!] Could not write to {outfile}: {exc}'), file=sys.stderr)
    else:
        if output:
            print('\n' + output)

    if network_html_file:
        _write_html(results, network_html_file, quiet)


def _write_html(results: list[dict], path: str, quiet: bool) -> None:
    try:
        with open(path, 'w') as fh:
            fh.write(render_html(results))
        if not quiet:
            print(colors.format_msg(f'[+] HTML page-link map saved to: {path}'))
    except OSError as exc:
        print(colors.format_msg(f'[!] Could not write to {path}: {exc}'), file=sys.stderr)
