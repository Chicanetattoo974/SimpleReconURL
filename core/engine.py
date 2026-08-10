import asyncio
import sys
from argparse import Namespace
from dataclasses import dataclass, field
from urllib.parse import urlparse

import core.colors as colors
from core.dedup import DeduplicatedSet
from core.profiles import get_profile, profile_options
from core.progress import NullProgress, Progress
from sources import PASSIVE_SOURCES, ACTIVE_SOURCES
from sources.base import Target
from sources._page_extractor import PageExtractor
from output.formatter import save_output

ALL_PASSIVE_SOURCES: dict = PASSIVE_SOURCES
ALL_ACTIVE_SOURCES: dict  = ACTIVE_SOURCES

# Extensions that yield nothing when fetched and parsed as HTML, so promoting
# them to seeds in a --recursive round is pure wasted traffic. .js is in the
# list on purpose: mining bundles is the spider's job and it does it properly.
_NON_HTML_EXT = (
    '.css', '.js', '.mjs', '.map', '.json', '.xml', '.txt', '.csv',
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.bmp', '.avif',
    '.woff', '.woff2', '.ttf', '.eot', '.otf',
    '.pdf', '.zip', '.gz', '.tgz', '.tar', '.rar', '.7z', '.exe', '.dmg',
    '.mp4', '.mp3', '.webm', '.avi', '.mov', '.wav', '.ogg',
)


def _unit_key(scope: str, target: Target) -> str:
    """The input a source of this SCOPE actually distinguishes.

    Two targets with the same key produce a byte-identical query for that
    source, so the second run is skipped by the --recursive round loop.
    'host' collapses to the seed host because every host-scoped source already
    queries the domain as a whole (`*.host`, `site:`, `domain:`), so a newly
    found subdomain was covered by the very first query.
    """
    if scope == 'url':
        return target.url
    if scope == 'origin':
        parsed = urlparse(target.url)
        return f'{parsed.scheme}://{parsed.netloc}'.lower()
    return target.host


@dataclass
class _RunState:
    """Mutable accumulators for one seed, shared across all --recursive rounds."""
    dedup: DeduplicatedSet
    gate: asyncio.Semaphore
    source_counts: dict = field(default_factory=dict)
    # In-scope URLs the seed filter skipped because they cannot contain links.
    # They stay in the main result set; this only records which were never visited.
    assets_skipped: set = field(default_factory=set)
    extras: dict = field(default_factory=lambda: {'urls_external': set()})
    url_sources: dict = field(default_factory=dict)   # url -> first source that reported it
    url_rounds: dict = field(default_factory=dict)    # url -> round it first appeared in
    seen_units: dict = field(default_factory=dict)    # source name -> unit keys already run
    seen_seeds: set = field(default_factory=set)      # urls already used as a round target

    def mark(self, name: str, scope: str, target: Target) -> bool:
        """Register (source, target) as scheduled. False if it already ran."""
        seen = self.seen_units.setdefault(name, set())
        key = _unit_key(scope, target)
        if key in seen:
            return False
        seen.add(key)
        return True


def _normalize_seed(raw: str) -> str | None:
    """Accept a bare host or a full URL; assume https:// when no scheme is given."""
    raw = raw.strip()
    if not raw:
        return None
    candidate = raw if '://' in raw else f'https://{raw}'
    parsed = urlparse(candidate)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        return None
    return candidate


def load_seed_urls(url: str | None = None, list_file: str | None = None, stdin: bool = False) -> list[str]:
    raw_targets: list[str] = []
    if url:
        raw_targets.append(url.strip())
    if list_file:
        try:
            with open(list_file, 'r') as fh:
                for line in fh:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        raw_targets.append(line)
        except FileNotFoundError:
            print(colors.format_msg(f'[!] File not found: {list_file}'))
            sys.exit(1)
    if stdin or (not url and not list_file and not sys.stdin.isatty()):
        for line in sys.stdin:
            line = line.strip()
            if line and not line.startswith('#'):
                raw_targets.append(line)

    valid: list[str] = []
    seen: set[str] = set()
    for t in raw_targets:
        normalized = _normalize_seed(t)
        if normalized is None:
            print(colors.format_msg(f'[!] Invalid URL skipped: {t}'))
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        valid.append(normalized)
    return valid


class Engine:
    def __init__(self, args: Namespace) -> None:
        self.args = args
        self.verbose: int = getattr(args, 'verbose', 0) or 0
        self.quiet: bool = getattr(args, 'quiet', False)
        # Replaced per recursive round; stays inert the rest of the time.
        self._progress: Progress = NullProgress()

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def log(self, msg: str) -> None:
        if not self.quiet:
            # These go to stdout, the progress line to stderr, usually the same
            # terminal: erase it first or the two get spliced together.
            self._progress.clear()
            print(colors.format_msg(msg))

    def vlog(self, level: int, msg: str) -> None:
        if self.verbose >= level and not self.quiet:
            self._progress.clear()
            print(colors.format_msg(msg))

    # ------------------------------------------------------------------
    # Source selection
    # ------------------------------------------------------------------

    def _abort(self, msg: str) -> None:
        """Stop the run with a message that survives --quiet/--no-banner.

        Source selection mistakes must never fall through to "run everything":
        this tool sends real traffic at a target, so a typo silently launching
        every active module is a safety problem, not a convenience. Printed
        directly (not via self.log) because that one is suppressed in exactly
        the quiet/pipe mode where the mistake is hardest to notice.
        """
        print(colors.format_msg(f'[!] {msg}'), file=sys.stderr)
        sys.exit(2)

    def _select_sources(self) -> tuple[dict, dict]:
        # --profile takes precedence over --sources
        profile_name: str | None = getattr(self.args, 'profile', None)
        if profile_name:
            profile = get_profile(profile_name)
            if profile is None:
                from core.profiles import profile_names
                self._abort(
                    f'Unknown profile: {profile_name!r}. '
                    f'Available: {", ".join(profile_names())}'
                )
            else:
                sources = profile.get('sources', 'all')
                # Apply profile-level option defaults (only if not explicitly set
                # by CLI). Routed through apply_run_config so a profile's
                # "options" block supports every key a run-config does, instead
                # of the single hardcoded rate_limit it used to recognise: an
                # unrecognised option was applied silently as a no-op.
                from core.run_config import apply_run_config
                apply_run_config(self.args, profile_options(profile_name))
                if sources == 'all' or sources is None:
                    passive, active = ALL_PASSIVE_SOURCES, ALL_ACTIVE_SOURCES
                else:
                    requested = set(sources)
                    passive = {k: v for k, v in ALL_PASSIVE_SOURCES.items() if k in requested}
                    active = {k: v for k, v in ALL_ACTIVE_SOURCES.items() if k in requested}
        elif self.args.sources is not None:
            # NB: `is not None`, not truthiness. `--sources ''` (an unset shell
            # variable expanding to nothing) used to be falsy and fall through
            # to "run every source", silently launching the active modules at
            # the target. An explicitly empty list now means exactly that:
            # no optional sources, only the always-on page extractor.
            requested = {s.strip() for s in self.args.sources.split(',') if s.strip()}
            unknown = requested - set(ALL_PASSIVE_SOURCES) - set(ALL_ACTIVE_SOURCES)
            if unknown:
                self._abort(
                    f'Unknown source(s): {", ".join(sorted(unknown))}. '
                    'Run --list-sources to see the available ones.'
                )
            passive = {k: v for k, v in ALL_PASSIVE_SOURCES.items() if k in requested}
            active = {k: v for k, v in ALL_ACTIVE_SOURCES.items() if k in requested}
        else:
            passive, active = ALL_PASSIVE_SOURCES, ALL_ACTIVE_SOURCES

        # Apply --exclude (works regardless of how sources were selected)
        exclude = {
            s.strip()
            for s in (getattr(self.args, 'exclude', '') or '').split(',')
            if s.strip()
        }
        if exclude:
            passive = {k: v for k, v in passive.items() if k not in exclude}
            active = {k: v for k, v in active.items() if k not in exclude}

        return passive, active

    # ------------------------------------------------------------------
    # Single-source runner (async, exception-safe)
    # ------------------------------------------------------------------

    async def _run_source(
        self,
        name: str,
        source,
        target: Target,
        st: '_RunState',
        round_no: int = 1,
        log_each: bool = True,
    ) -> None:
        try:
            self._progress.start(target.url)
            async with st.gate:
                found = await source.fetch(target)
            new_items = st.dedup.update(found)
            # Accumulated, not assigned: with --recursive a source can run over
            # several targets and every round must add to its tally.
            st.source_counts[name] = st.source_counts.get(name, 0) + len(new_items)
            if log_each:
                if new_items:
                    self.log(f'[*] [{name}] +{len(new_items)} urls')
                else:
                    self.vlog(1, f'[!] [{name}] 0 new urls')
            # Merge out-of-scope elements collected by this source
            for key in st.extras:
                st.extras[key].update(source.extras.get(key, set()))
            # Record URL → originating source / round (first contributor wins)
            for u in found:
                st.url_sources.setdefault(u, name)
                st.url_rounds.setdefault(u, round_no)
        except Exception as exc:
            self.vlog(1, f'[x] [{name}] error: {exc}')
            st.source_counts.setdefault(name, 0)
        finally:
            # In the finally block so a source that blew up still advances the
            # bar; otherwise one failure freezes the progress short of 100%.
            self._progress.advance(len(st.dedup.as_set()))

    # ------------------------------------------------------------------
    # Recursive rounds (--recursive)
    # ------------------------------------------------------------------

    def _next_seeds(self, st: '_RunState', limit: int) -> list[str]:
        """Pick which freshly found URLs are worth fetching in the next round."""
        candidates = []
        for url in sorted(st.dedup.as_set()):
            if url in st.seen_seeds:
                continue
            path = (urlparse(url).path or '').lower()
            if path.endswith(_NON_HTML_EXT):
                # Still part of the results; recorded only so the run can report
                # which in-scope URLs were found but never visited.
                st.assets_skipped.add(url)
                continue
            candidates.append(url)
        if limit > 0:
            candidates = candidates[:limit]
        st.seen_seeds.update(candidates)
        return candidates

    async def _collect_round(
        self,
        seeds: list[str],
        seed_host: str,
        selected: list[tuple],
        make_source,
        st: '_RunState',
        round_no: int,
        rounds: int,
    ) -> int:
        """Run every selected source over the new seeds, skipping repeat inputs.

        The scope anchor stays the original seed host, so _filter_urls() keeps
        classifying results exactly as it does on round 1; only the URL varies.
        """
        before = len(st.dedup.as_set())
        plan = [
            (name, cls, target)
            for name, cls in selected
            for target in (Target(url=u, host=seed_host) for u in seeds)
            if st.mark(name, getattr(cls, 'SCOPE', 'host'), target)
        ]
        if not plan:
            return 0
        self.vlog(1, f'[*] Round {round_no}: {len(plan)} source run(s) scheduled')
        # len(plan) is the exact denominator, so the percentage is real rather
        # than an estimate. Disabled by --quiet/--no-progress or a non-TTY stderr.
        self._progress = Progress(
            round_no=round_no,
            rounds=rounds,
            total=len(plan),
            baseline=before,
            enabled=not self.quiet and not getattr(self.args, 'no_progress', False),
        )
        try:
            await asyncio.gather(
                *[
                    self._run_source(name, make_source(cls), target, st, round_no, log_each=False)
                    for name, cls, target in plan
                ],
                return_exceptions=True,
            )
        finally:
            self._progress.finish()
            self._progress = NullProgress()
        return len(st.dedup.as_set()) - before

    # ------------------------------------------------------------------
    # Per-target enumeration
    # ------------------------------------------------------------------

    async def run_target(self, seed_url: str) -> dict:
        target = Target.from_url(seed_url)

        self.log(f"\n{'-'*60}")
        self.log(f'[*] Enumerating: {seed_url}')
        self.log(f"{'-'*60}")

        passive_sources, active_sources = self._select_sources()
        rate_limit: int = getattr(self.args, 'rate_limit', 0) or 0
        proxy: str | None = getattr(self.args, 'proxy', None)
        user_agent: str = getattr(self.args, 'user_agent', 'SimpleReconURL/1') or 'SimpleReconURL/1'
        rounds: int = max(1, int(getattr(self.args, 'recursive', 1) or 1))
        max_seeds: int = max(0, int(getattr(self.args, 'recursive_max_seeds', 500) or 0))

        st = _RunState(
            dedup=DeduplicatedSet(),
            # Bounds how many source runs are in flight at once. Round 1 never
            # exceeds it in practice; a recursive round can schedule hundreds.
            gate=asyncio.Semaphore(max(1, getattr(self.args, 'threads', 8) or 8)),
        )
        st.seen_seeds.add(seed_url)

        def _make_source(cls):
            return cls(
                timeout=self.args.timeout,
                rate_limit=rate_limit,
                verbose=self.verbose,
                proxy=proxy,
                user_agent=user_agent,
            )

        # ── Round 1: the original three-phase pipeline, order preserved ──
        # Kept phased (page first, awaited alone) rather than folded into the
        # generic round runner: 'page' completing before the others is what
        # makes url_sources attribution deterministic.
        selected: list[tuple] = [('page', PageExtractor)]

        self.log('[*] Extracting URLs from the seed page...')
        st.mark('page', PageExtractor.SCOPE, target)
        await self._run_source('page', _make_source(PageExtractor), target, st, 1)

        # ── Passive sources ──────────────────────────────────────────
        if not self.args.no_passive:
            self.log('[*] Running passive sources...')
            selected += list(passive_sources.items())
            tasks = []
            for name, cls in passive_sources.items():
                st.mark(name, cls.SCOPE, target)
                tasks.append(self._run_source(name, _make_source(cls), target, st, 1))
            await asyncio.gather(*tasks, return_exceptions=True)

        # ── Active sources ──────────────────────────────────────────
        if active_sources:
            self.log('[*] Running active sources...')
            selected += list(active_sources.items())
            active_tasks = []
            for name, cls in active_sources.items():
                st.mark(name, cls.SCOPE, target)
                active_tasks.append(self._run_source(name, _make_source(cls), target, st, 1))
            await asyncio.gather(*active_tasks, return_exceptions=True)

        # ── Rounds 2..N: feed the newly found URLs back as seeds ─────
        rounds_done = 1
        for round_no in range(2, rounds + 1):
            seeds = self._next_seeds(st, max_seeds)
            if not seeds:
                self.log(f'[*] Round {round_no}/{rounds}: no new seed urls, stopping early')
                break
            self.log(f'[*] Round {round_no}/{rounds}: {len(seeds)} new seed url(s)...')
            gained = await self._collect_round(
                seeds, target.host, selected, _make_source, st, round_no, rounds
            )
            rounds_done = round_no
            self.log(f'[+] Round {round_no}/{rounds}: +{gained} urls')
            # Deliberately no "stop when gained == 0": under --recursive-max-seeds
            # a barren round can still leave queued seeds unexplored. Running out
            # of seeds is the only correct termination signal, and it is
            # guaranteed because _next_seeds() never returns a URL twice.

        urls = st.dedup.as_set()
        extras = st.extras
        if rounds > 1:
            self.log(f'\n[+] Total unique URLs found: {len(urls)} ({rounds_done} round(s))')
            # Only meaningful with recursion: without it no seed filtering runs,
            # so nothing was ever skipped.
            if st.assets_skipped:
                self.log(
                    f'[+] {len(st.assets_skipped)} asset url(s) found, not crawled'
                    + ('' if self.verbose >= 3 else ' (-v 3 to list them)')
                )
        else:
            self.log(f'\n[+] Total unique URLs found: {len(urls)}')

        # ── Live URL verification ───────────────────────────────────
        # Runs once, over the union of every round.
        live_results: dict = {}
        if self.args.verify_live and urls:
            from verify.live_check import verify_live
            self.log('[*] Verifying live URLs...')
            live_results = await verify_live(
                urls,
                timeout=self.args.timeout,
                quiet=self.quiet,
                concurrency=self.args.threads * 5,
                proxy=getattr(self.args, 'proxy', None),
            )
            live_count = sum(1 for v in live_results.values() if v.get('status'))
            self.log(f'[+] Live URLs: {live_count}/{len(urls)}')

        # ── Extras: drop anything that turned out to be in-scope or the seed itself ──
        extras['urls_external'] -= urls
        extras['urls_external'].discard(seed_url)
        # Unlike urls_external, this bucket is a *subset* of urls: these are
        # in-scope results that were simply never fetched. Kept separate so the
        # report can label the two differently.
        if st.assets_skipped:
            extras['urls_assets'] = set(st.assets_skipped)

        include_extras = self.verbose >= 3

        return {
            'seed': seed_url,
            'urls': urls,
            'live': live_results,
            'sources': st.source_counts,
            'url_sources': st.url_sources,
            'extras': extras if include_extras else {},
            # Additive keys: consumers that predate --recursive ignore them, so
            # the output formats and the --db schema stay untouched.
            'rounds': rounds_done,
            'url_rounds': st.url_rounds,
        }

    # ------------------------------------------------------------------
    # Main entrypoint
    # ------------------------------------------------------------------

    async def run(self) -> None:
        targets = load_seed_urls(
            url=self.args.url,
            list_file=self.args.list,
            stdin=getattr(self.args, 'stdin', False),
        )

        if not targets:
            print(colors.format_msg('[!] No valid targets found.'))
            sys.exit(1)

        db_path: str | None = getattr(self.args, 'db', None)
        db_news: bool = getattr(self.args, 'db_news', False)

        # Log this invocation to the fixed system DB (config/system.db)
        from core import system_db
        system_db.log_command(' '.join(sys.argv), targets=','.join(targets))

        all_results: list[dict] = []
        for seed_url in targets:
            result = await self.run_target(seed_url)
            if db_path:
                from output import db
                if db_news:
                    # Read the baseline BEFORE saving this run, then surface and
                    # persist only values not seen in any prior run.
                    known = db.load_known(db_path, result['seed'])
                    result = db.filter_new(result, known)
                    db.save_result(db_path, result)
                    self.log(
                        f'[+] [db-news] {len(result["urls"])} new url(s) '
                        f'since last run -> {db_path}'
                    )
                else:
                    db.save_result(db_path, result)
                    self.log(f'[+] [db] saved {len(result["urls"])} url(s) to {db_path}')
            all_results.append(result)

        save_output(
            results=all_results,
            fmt=self.args.output,
            outfile=getattr(self.args, 'outfile', None),
            quiet=self.quiet,
            network_map=getattr(self.args, 'network_map', False),
            network_html_file=getattr(self.args, 'network_html', None),
        )
