import argparse

from core.profiles import load_profiles, profile_names
from sources import PASSIVE_SOURCES, ACTIVE_SOURCES

# Built dynamically from the auto-discovered source modules
ALL_PASSIVE = list(PASSIVE_SOURCES)
ALL_ACTIVE  = list(ACTIVE_SOURCES)
ALL_SOURCES = ALL_PASSIVE + ALL_ACTIVE

MAX_RECURSIVE_ROUNDS = 20


def _recursive_rounds(value: str) -> int:
    """Validate --recursive: an int in 1..20.

    Fails closed like the source-selection checks in Engine._abort(): an out of
    range value stops the run (argparse exits 2) instead of being clamped, so a
    typo can never silently turn into a much larger amount of traffic.
    """
    try:
        rounds = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid int value: '{value}'")
    if not 1 <= rounds <= MAX_RECURSIVE_ROUNDS:
        raise argparse.ArgumentTypeError(
            f'must be between 1 and {MAX_RECURSIVE_ROUNDS} (got {rounds})'
        )
    return rounds


class _ColoredFormatter(argparse.RawDescriptionHelpFormatter):
    """Argparse formatter with ANSI color support."""

    def start_section(self, heading: str | None) -> None:
        import core.colors as C
        if heading:
            heading = C.bold(C.cyan(heading))
        super().start_section(heading)

    def _format_usage(self, usage, actions, groups, prefix):
        import core.colors as C
        return super()._format_usage(
            usage, actions, groups,
            prefix if prefix is not None else C.bold(C.cyan('usage')) + ': ',
        )

    def _format_action_invocation(self, action) -> str:
        import core.colors as C
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            metavar, = self._metavar_formatter(action, default)(1)
            return C.cyan(metavar)
        parts = []
        if action.nargs == 0:
            parts.extend(C.cyan(s) for s in action.option_strings)
        else:
            default = self._get_default_metavar_for_optional(action)
            args_string = self._format_args(action, default)
            for option_string in action.option_strings:
                parts.append(f'{C.cyan(option_string)} {C.yellow(args_string)}')
        return ', '.join(parts)


def build_parser() -> argparse.ArgumentParser:
    import core.colors as C

    description = (
        f'{C.bold(C.white("SimpleReconURL v1"))}'
        ' - Extract and discover URLs from a seed page'
    )
    epilog = (
        f'{C.bold(C.cyan("quick start:"))}\n'
        f'  {C.gray("python simplereconurl.py -u https://target.com/")}\n'
        f'  {C.gray("python simplereconurl.py -u https://target.com/ --profile discovery --verify-live")}\n'
        f'\n'
        f'{C.bold(C.cyan("see more:"))}\n'
        f'  {C.gray("python simplereconurl.py --list-sources")}    {C.gray("# all sources")}\n'
        f'  {C.gray("python simplereconurl.py --list-profiles")}   {C.gray("# curated source groups")}\n'
        f'  {C.gray("python simplereconurl.py --list-examples")}   {C.gray("# usage examples + tool chaining")}\n'
    )

    parser = argparse.ArgumentParser(
        prog='simplereconurl.py',
        description=description,
        formatter_class=_ColoredFormatter,
        epilog=epilog,
    )

    # Target
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument(
        '-u', '--url', metavar='URL', help='Single seed URL (scheme optional, assumed https://)'
    )
    target_group.add_argument(
        '-l', '--list', metavar='FILE', help='File with list of seed URLs, one per line'
    )
    target_group.add_argument(
        '--stdin',
        action='store_true',
        help='Read seed URLs from stdin (one per line); enables pipe-friendly use',
    )

    # Output
    parser.add_argument(
        '-o', '--output',
        choices=['txt', 'json', 'csv', 'ndjson', 'html', 'markdown'],
        default='txt',
        help='Output format (default: txt). ndjson = one JSON line per URL; '
             'html = interactive page-link map; markdown = human-readable report',
    )
    parser.add_argument('--outfile', metavar='FILE', help='Write output to file')
    parser.add_argument(
        '--network-map',
        action='store_true',
        help='Include the page-link graph (nodes/edges) in JSON output. '
             'Auto-enabled when -o html or --network-html is used.',
    )
    parser.add_argument(
        '--network-html',
        metavar='FILE',
        help='Write an HTML page-link map visualization to FILE alongside the main output. '
             'Combine with any -o format.',
    )
    parser.add_argument(
        '--db',
        metavar='FILE',
        help='SQLite database file used as both store and comparison source. '
             'Without --db-news, saves the full run (URLs, live data, and at -v 3 also '
             'external URLs found out of scope). With --db-news, also the baseline to diff against.',
    )
    parser.add_argument(
        '--db-news',
        action='store_true',
        help='Compare this run against the --db database and output only values not seen before, '
             'saving the new ones back to the DB. Requires --db.',
    )
    parser.add_argument(
        '--db-list',
        choices=['urls', 'extras', 'history'],
        metavar='TYPE',
        help='List stored data and exit. urls/extras read the --db database '
             '(extras=external URLs found out of scope); history reads the fixed '
             'config/system.db command log (no --db needed). Optionally filter with -u URL.',
    )

    # Continuous monitoring (cron scheduler stored in config/system.db)
    parser.add_argument(
        '--watch-add',
        metavar='CRON',
        help='Register the current command in config/system.db to run on a 5-field cron '
             "schedule (e.g. '0,15,30,45 * * * *'); the --watch-add flag itself is stripped "
             'from the stored command. Use --watch to run the scheduler.',
    )
    parser.add_argument(
        '--watch',
        action='store_true',
        help='Monitoring daemon: every minute, run any config/system.db job whose cron '
             'schedule matches now (jobs due in the same minute run in parallel). Ctrl-C to stop.',
    )
    parser.add_argument(
        '--watch-list',
        action='store_true',
        help='List registered watch jobs (with their IDs) and exit.',
    )
    parser.add_argument(
        '--watch-del',
        type=int,
        metavar='ID',
        help='Delete the watch job with the given ID (from --watch-list) and exit.',
    )
    parser.add_argument(
        '--watch-clear',
        action='store_true',
        help='Delete all registered watch jobs and exit.',
    )

    # Performance
    parser.add_argument(
        '-t', '--threads',
        type=int, default=8,
        help='Thread multiplier for --verify-live concurrency (default: 8)',
    )
    parser.add_argument(
        '--timeout',
        type=int, default=30,
        help='HTTP timeout in seconds (default: 30)',
    )
    parser.add_argument(
        '--rate-limit',
        type=int, default=0,
        metavar='N',
        help='Max concurrent requests per source (0=unlimited)',
    )

    # Source control
    parser.add_argument(
        '--profile',
        metavar='PROFILE',
        help=(
            'Run a predefined source group. Available: '
            + ', '.join(profile_names())
            + '. Overrides --sources if both are given.'
        ),
    )
    parser.add_argument(
        '--sources',
        metavar='SOURCES',
        help=f'Comma-separated sources to use (default: all). Available: {", ".join(ALL_SOURCES)}',
    )
    parser.add_argument(
        '--exclude',
        metavar='SOURCES',
        help='Comma-separated sources to exclude. Applied after --sources/--profile selection',
    )
    # Recursive rounds
    parser.add_argument(
        '--recursive',
        type=_recursive_rounds, default=1, metavar='N',
        help=f'Collection rounds (default: 1, max: {MAX_RECURSIVE_ROUNDS}). Each extra round feeds '
             'the newly discovered URLs back as seeds and runs every selected source over them. '
             'Sources are not re-run on an input they already handled: page-level sources run once '
             'per URL, site-level ones once per origin, domain-level ones once per host.',
    )
    parser.add_argument(
        '--recursive-max-seeds',
        type=int, default=500, metavar='N',
        help='Cap on how many new URLs are promoted to seeds per recursive round '
             '(default: 500, 0=unlimited). Non-HTML assets are never promoted.',
    )
    parser.add_argument(
        '--no-passive',
        action='store_true',
        help='Skip passive discovery sources (wayback/commoncrawl/urlscan/alienvault/urlhaus/virustotal). '
             'The default seed-page extraction and active sources (spider/robots_sitemap) still run.',
    )
    parser.add_argument(
        '--list-sources',
        action='store_true',
        help='List all available sources and exit',
    )
    parser.add_argument(
        '--list-profiles',
        action='store_true',
        help='List all available profiles and exit',
    )
    parser.add_argument(
        '--list-examples',
        action='store_true',
        help='Print categorized usage examples (incl. tool chaining) and exit',
    )

    # Run-config preset
    parser.add_argument(
        '--config',
        metavar='FILE',
        help=(
            'JSON file with CLI argument presets (run-config). '
            'Explicit CLI flags always override values from the config file. '
            'See config/run_config.example.json for the full format.'
        ),
    )

    # Post-processing
    parser.add_argument(
        '--verify-live',
        action='store_true',
        help='Verify which discovered URLs are alive: HTTP status, title, server, '
             'content-length, body hash and response time.',
    )

    # Verbosity
    parser.add_argument(
        '-v', '--verbose',
        nargs='?', const=1, type=int, default=0,
        metavar='LEVEL',
        help='Verbose level (cumulative): 1=zero results, 2=+HTTP codes, '
             '3=+HTTP body +extras (external URLs in output and DB), 4=full debug+exceptions',
    )
    parser.add_argument(
        '-q', '--quiet', action='store_true', help='Quiet mode (results only)'
    )
    parser.add_argument(
        '--no-banner',
        action='store_true',
        help='Suppress banner and all process output; print only the final URL list',
    )
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable the live progress line drawn during --recursive rounds. '
             'The line only ever appears when stderr is a terminal, so piping is '
             'unaffected either way.',
    )
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable ANSI color output',
    )

    # Network / proxy
    parser.add_argument(
        '--proxy',
        metavar='URL',
        help='Route all HTTP requests through this proxy (e.g. http://127.0.0.1:8080 or socks5://host:port)',
    )
    parser.add_argument(
        '--user-agent',
        metavar='UA',
        default='SimpleReconURL/1',
        help='Override the HTTP User-Agent header sent by all sources (default: SimpleReconURL/1)',
    )

    return parser


def print_sources() -> None:
    import core.colors as C

    def _key_badge(cls) -> str:
        if cls.API_TOKEN_IS_REQUIREMENT:
            return C.red('[API key obrigatória]')
        return ''

    def _scope_badge(cls) -> str:
        # Surfaced so the SCOPE default is observable rather than silent: it is
        # what decides how often --recursive re-runs the source.
        return C.gray(f'{getattr(cls, "SCOPE", "host"):<6}')

    print(f'\n{C.bold(C.white("Available sources:"))}\n')
    print(f'  {C.gray("(the seed page itself is always extracted by default, before any of these run)")}\n')
    print(f'  {C.gray("scope = what the source reads, so how often --recursive re-runs it:")}')
    print(f'  {C.gray("host = once per target domain | origin = once per site | url = every page")}\n')
    print(f'  {C.bold(C.cyan("PASSIVE"))} ')
    for cls in PASSIVE_SOURCES.values():
        badge = _key_badge(cls)
        suffix = f'  {badge}' if badge else ''
        print(f'    {C.cyan(f"{cls.NAME:<16}")} {_scope_badge(cls)} {cls.DESCRIPTION}{suffix}')
    print(f'\n  {C.bold(C.cyan("ACTIVE"))} {C.gray("(direct HTTP to the target):")}')
    for cls in ACTIVE_SOURCES.values():
        print(f'    {C.cyan(f"{cls.NAME:<16}")} {_scope_badge(cls)} {cls.DESCRIPTION}')
    print()


def print_profiles() -> None:
    import core.colors as C

    profiles = load_profiles()
    if not profiles:
        print('No profiles found.')
        return

    print(f'\n{C.bold(C.white("Available profiles:"))}\n')
    for name, cfg in profiles.items():
        sources = cfg.get('sources', 'all')
        if isinstance(sources, list):
            src_str = ', '.join(sources)
        else:
            src_str = str(sources)
        opts = cfg.get('options', {})
        opts_str = f'  {C.gray(str(opts))}' if opts else ''
        print(f'  {C.cyan(f"{name:<12}")} {cfg.get("description", "")}')
        print(f'  {" " * 12} {C.gray("sources:")} {src_str}{opts_str}')
    print()


def print_db_list(kind: str, db_path: str | None, seed: str | None = None) -> None:
    """Print stored data of *kind* (pipe-friendly plain lines).

    urls/extras come from the per-target *db_path*; history comes from the
    fixed config/system.db command log.
    """
    if kind == 'history':
        from core import system_db
        for _id, ts, targets, command in system_db.list_command_history(seed):
            print(f'{ts} | {targets or ""} | {command or ""}')
        return

    from output import db
    if kind == 'urls':
        for url, _source in db.list_urls(db_path, seed):
            print(url)
    elif kind == 'extras':
        for _type, value in db.list_extras(db_path, seed):
            print(value)


def print_watch_list() -> None:
    """Print registered watch jobs as an aligned table (ID first, for --watch-del)."""
    import core.colors as C
    from core import system_db

    jobs = system_db.list_watch_jobs()
    if not jobs:
        print(C.gray('No watch jobs registered. Add one with --watch-add "<cron>".'))
        return

    header = '  {:<4} {:<20} {:<19} {}'.format('ID', 'SCHEDULE', 'LAST RUN', 'COMMAND')
    print('\n' + C.bold(C.white('Watch jobs')) + ' ' + C.gray('(' + system_db.SYSTEM_DB + ')') + '\n')
    print(C.bold(header))
    for j in jobs:
        # pad the plain value first, then colorize, so ANSI codes don't break alignment
        idc   = C.cyan('{:<4}'.format(j['id']))
        sched = '{:<20}'.format(j['schedule'])
        last  = '{:<19}'.format(j['last_run'] or '—')
        print('  {} {} {} {}'.format(idc, sched, last, C.gray(j['command'])))
    print()


# ---------------------------------------------------------------------------
# Categorized usage examples (printed via --list-examples)
# ---------------------------------------------------------------------------
_EXAMPLES: list[tuple[str, list[str]]] = [
    ('Basics', [
        'python simplereconurl.py -u https://target.com/',
        'python simplereconurl.py -l seeds.txt',
        'python simplereconurl.py --list-sources',
        'python simplereconurl.py --list-profiles',
        'python simplereconurl.py --list-examples',
    ]),
    ('Profiles (curated source groups)', [
        'python simplereconurl.py -u https://target.com/ --profile fast',
        'python simplereconurl.py -u https://target.com/ --profile crawl --verify-live',
        'python simplereconurl.py -u https://target.com/ --profile discovery --output json --outfile discovery.json',
        'python simplereconurl.py -u https://target.com/ --profile full -v 2',
    ]),
    ('Custom source selection', [
        'python simplereconurl.py -u https://target.com/ --sources wayback,commoncrawl',
        'python simplereconurl.py -u https://target.com/ --sources spider,robots_sitemap',
        'python simplereconurl.py -u https://target.com/ --sources virustotal,urlscan,alienvault',
        'python simplereconurl.py -u https://target.com/ --no-passive --sources spider',
    ]),
    ('Recursive rounds (feed results back as seeds)', [
        'python simplereconurl.py -u https://target.com/ --recursive 3',
        'python simplereconurl.py -u https://target.com/ --profile crawl --recursive 3',
        'python simplereconurl.py -u https://target.com/ --recursive 10 --recursive-max-seeds 200',
        'python simplereconurl.py -u https://target.com/ --recursive 5 --rate-limit 3 -v 2',
    ]),
    ('Headless browser capture (runtime XHR/fetch requests)', [
        '# one-time setup (optional dependency, ~150MB browser download)',
        'pip install -r requirements-browser.txt && playwright install chromium',
        '# capture every request the page makes at runtime',
        'python simplereconurl.py -u https://target.com/ --profile browser',
        'python simplereconurl.py -u https://target.com/ --sources browser --no-passive -v 2',
        '# third-party requests (CDN/analytics) show up as external URLs at -v 3',
        'python simplereconurl.py -u https://target.com/ --sources browser -v 3',
        '# combine runtime capture with the static crawler',
        'python simplereconurl.py -u https://target.com/ --sources browser,spider -o json --outfile out.json',
    ]),
    ('Output formats', [
        'python simplereconurl.py -u https://target.com/ --output json --outfile result.json',
        'python simplereconurl.py -u https://target.com/ --output csv  --outfile result.csv',
        'python simplereconurl.py -u https://target.com/ --output txt  --outfile result.txt',
        'python simplereconurl.py -u https://target.com/ --no-banner > urls.txt',
    ]),
    ('Performance & rate-limiting', [
        'python simplereconurl.py -u https://target.com/ --threads 20',
        'python simplereconurl.py -u https://target.com/ --rate-limit 5 --timeout 15',
        'python simplereconurl.py -u https://target.com/ --profile discovery --rate-limit 3',
        'python simplereconurl.py -l seeds.txt --threads 40 --timeout 60',
    ]),
    ('Live verification (HTTP status/title/server/body hash)', [
        'python simplereconurl.py -u https://target.com/ --verify-live --timeout 10',
        'python simplereconurl.py -u https://target.com/ --profile fast --verify-live -o json --outfile live.json',
        'python simplereconurl.py -u https://target.com/ --verify-live -o csv --outfile live.csv',
    ]),
    ('Debug & verbosity', [
        'python simplereconurl.py -u https://target.com/ --sources wayback -v 4',
        'python simplereconurl.py -u https://target.com/ --profile fast --quiet',
        'python simplereconurl.py -u https://target.com/ -v 2     # show HTTP status codes',
        'python simplereconurl.py -u https://target.com/ -v 3     # also show external (out-of-scope) URLs',
    ]),
    ('Piping into httpx (HTTP probing)', [
        'python simplereconurl.py -u https://target.com/ --no-banner | httpx -silent',
        'python simplereconurl.py -u https://target.com/ --no-banner | httpx -silent -mc 200',
        'python simplereconurl.py -u https://target.com/ --no-banner | httpx -silent -status-code -title -tech-detect',
    ]),
    ('Piping into nuclei (vulnerability scanning)', [
        'python simplereconurl.py -u https://target.com/ --no-banner | httpx -silent | nuclei -t cves/ -silent',
        'python simplereconurl.py -u https://target.com/ --no-banner | nuclei -severity critical,high',
        'python simplereconurl.py -u https://target.com/ --profile discovery --no-banner | nuclei -t exposures/',
    ]),
    ('Piping into katana / gau (further crawling)', [
        'python simplereconurl.py -u https://target.com/ --no-banner | httpx -silent | katana -silent',
        'python simplereconurl.py -u https://target.com/ --no-banner | gau --threads 10',
    ]),
    ('Screenshots (gowitness / aquatone)', [
        'python simplereconurl.py -u https://target.com/ --no-banner | httpx -silent | gowitness scan single',
        'python simplereconurl.py -u https://target.com/ --no-banner | aquatone -out aquatone-report/',
    ]),
    ('Run-config presets (--config)', [
        'cp config/run_config.example.json myrun.json',
        '# edit myrun.json with your preferred options',
        'python simplereconurl.py -u https://target.com/ --config myrun.json',
        '# CLI flags override config values:',
        'python simplereconurl.py -u https://target.com/ --config myrun.json --output txt',
    ]),
    ('Asset discovery from a seed-URL list', [
        'python simplereconurl.py -l seeds.txt --output json --outfile all_urls.json --timeout 60',
        'python simplereconurl.py -l seeds.txt --profile discovery --verify-live --rate-limit 3',
        'cat seeds.txt | xargs -I{} python simplereconurl.py -u {} --no-banner | sort -u > all_unique.txt',
    ]),
    ('Continuous monitoring (diff against previous run)', [
        'python simplereconurl.py -u https://target.com/ --no-banner | sort -u > today.txt',
        'comm -13 <(sort -u yesterday.txt) today.txt   # show only new URLs',
    ]),
    ('SQLite persistence & change tracking (--db)', [
        'python simplereconurl.py -u https://target.com/ --db recon.db',
        '# subsequent run: print + store only newly discovered URLs',
        'python simplereconurl.py -u https://target.com/ --db recon.db --db-news',
        '# capture external (out-of-scope) URLs too',
        'python simplereconurl.py -u https://target.com/ --db recon.db --db-news -v 3 --verify-live',
        '# use a different DB file as the comparison/output store',
        'python simplereconurl.py -u https://target.com/ --db prod-assets.db --db-news -o json',
    ]),
    ('Inspect the database (--db-list)', [
        'python simplereconurl.py --db recon.db --db-list urls',
        'python simplereconurl.py --db recon.db --db-list extras',
        '# command log lives in config/system.db (no --db needed)',
        'python simplereconurl.py --db-list history',
        '# restrict to one seed URL',
        'python simplereconurl.py --db recon.db --db-list urls -u https://target.com/',
        '# pipe stored URLs straight into httpx',
        'python simplereconurl.py --db recon.db --db-list urls | httpx -silent',
    ]),
    ('Continuous monitoring (--watch / --watch-add)', [
        '# register a command on a cron schedule (stored in config/system.db)',
        'python simplereconurl.py -u https://target.com/ --profile fast --db target.db --quiet \\\n       --watch-add "0,15,30,45 * * * *"',
        '# run the scheduler daemon (no --db needed); due jobs run in parallel',
        'python simplereconurl.py --watch',
        '# manage registered jobs',
        'python simplereconurl.py --watch-list           # show jobs + their IDs',
        'python simplereconurl.py --watch-del 3          # delete job #3',
        'python simplereconurl.py --watch-clear          # delete all jobs',
    ]),
    ('string-x (strx) — modular pipeline automation [github.com/MrCl0wnLab/string-x]', [
        '# HTTP probe each discovered URL through strx',
        'python simplereconurl.py -u https://target.com/ --no-banner \\\n       | strx -st "echo {STRING}" -module "clc:http_probe" -pm',
        '# extract emails from every discovered page',
        'python simplereconurl.py -u https://target.com/ --no-banner \\\n       | strx -st "curl -sk {STRING}" -module "ext:email" -pm',
        '# notify Telegram channel with every newly discovered URL',
        'python simplereconurl.py -u https://target.com/ --db recon.db --db-news --no-banner \\\n       | strx -st "echo {STRING}" -module "con:telegram" -pm',
    ]),
]


def print_examples() -> None:
    import core.colors as C

    print(f'\n{C.bold(C.white("SimpleReconURL — Usage Examples"))}\n')
    for section, cmds in _EXAMPLES:
        print(f'{C.bold(C.cyan("# " + section))}')
        for cmd in cmds:
            if cmd.startswith('#'):
                # inline comment line inside a section
                print(f'  {C.yellow(cmd)}')
            else:
                print(f'  {C.gray(cmd)}')
        print()
