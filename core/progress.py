"""Single-line live progress for the --recursive rounds.

The recursive rounds run their sources with log_each=False on purpose, so
nothing at all is printed between "Round 2/3: N new seed url(s)" and the
round's final tally. On a large target that is minutes of silence. This module
draws one line that is rewritten in place with '\\r', so the scrollback the
user already has on screen is never erased:

    [*] 2/3 [########------------] 43% | 128/296 | 1841 urls (+412) | /blog/post-1

Two things here are load-bearing:

* **It writes to stderr, and only when stderr is a TTY.** Writing to stdout
  would corrupt `simplereconurl.py ... | httpx`, a documented use case; going
  to stderr instead means that pipe keeps working *and* still shows progress,
  since only stdout was redirected. The isatty() gate is what keeps
  `... > log.txt 2>&1` from collecting thousands of '\\r' fragments.

* **The TTY gate must not be colors.enabled().** That flag is also turned off
  by --no-color and by NO_COLOR, and in those cases progress should still be
  drawn, just without color. Color is decided separately, per render.
"""
from __future__ import annotations

import shutil
import sys
import time

import core.colors as colors

# Minimum gap between two renders. 300-ish concurrent tasks would otherwise
# produce hundreds of writes per second, all of them invisible to a human.
_MIN_INTERVAL = 0.1

# 16 rather than 20 on purpose: with the labels, a 20-wide bar pushed the line
# to 82 chars and a standard 80-column terminal lost the bar entirely.
_BAR_WIDTH = 16
_ERASE_LINE = '\r\x1b[K'   # carriage return + erase from cursor to end of line


def _display_url(url: str) -> str:
    """Shorten a URL to its path+query, which is the part that actually varies.

    Within a round the host is nearly always the same, so spending scarce line
    width on it just pushes out the informative half. Falls back to the full
    URL when there is no meaningful path (e.g. an origin root).
    """
    from urllib.parse import urlsplit
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    path = parts.path or '/'
    if parts.query:
        path = f'{path}?{parts.query}'
    if path in ('', '/'):
        return parts.netloc or url
    return path


class Progress:
    """A rewritable one-line progress indicator for a single recursive round.

    Inert unless stderr is a TTY and *enabled* is True, in which case every
    method is a cheap no-op, so callers never need to guard their calls.
    """

    def __init__(
        self,
        round_no: int,
        rounds: int,
        total: int,
        baseline: int,
        enabled: bool = True,
        stream=None,
    ) -> None:
        self.round_no = round_no
        self.rounds = rounds
        self.total = max(0, total)
        # URL count before this round started, so "+N" means "new this round".
        self.baseline = baseline
        self.done = 0
        self.urls = baseline
        self.current = ''
        self._drawn = False
        self._last_render = 0.0
        self._stream = stream if stream is not None else sys.stderr
        self.enabled = bool(enabled) and self._stream_is_tty()

    def _stream_is_tty(self) -> bool:
        try:
            return bool(self._stream.isatty())
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Line building
    # ------------------------------------------------------------------

    def _bar(self, pct: int) -> str:
        filled = round(_BAR_WIDTH * pct / 100)
        return '[' + '#' * filled + '-' * (_BAR_WIDTH - filled) + ']'

    def _compose(self, width: int) -> str:
        """Build the line, dropping parts by priority when width is tight.

        Every counter carries a label, because the two fractions mean very
        different things and are indistinguishable without one: 'tasks' counts
        source runs scheduled for this round, 'urls' counts unique URLs found
        across the whole run. The labels cost width, so the line is composed as
        a ladder of decreasing verbosity and the widest form that fits wins.
        The counters are the point of the feature, so they are last to go.
        """
        pct = int(self.done * 100 / self.total) if self.total else 100
        new = self.urls - self.baseline
        head = f'[*] round {self.round_no}/{self.rounds}'
        bar = self._bar(pct)
        tasks = f'tasks {self.done}/{self.total}'
        urls = f'urls {self.urls} (+{new} new)'

        base = f'{head} {bar} {pct:3d}% | {tasks} | {urls}'
        if self.current:
            candidate = f'{base} | now {self.current}'
            if len(candidate) <= width:
                return candidate
            # Truncate the URL into whatever room is left before dropping it.
            room = width - len(base) - 8   # 7 for ' | now ' plus 1 for the '…'
            if room >= 10:
                return f'{base} | now …{self.current[-room:]}'

        for line in (
            base,                                                  # drop the URL
            f'{head} {pct:3d}% | {tasks} | {urls}',                # drop the bar
            f'[*] {self.round_no}/{self.rounds} {pct:3d}% | '      # drop the words
            f'{self.done}/{self.total} | {self.urls} (+{new})',
        ):
            if len(line) <= width:
                return line
        return f'{self.done}/{self.total} {self.urls}u'[:width]

    def _render(self, force: bool = False) -> None:
        if not self.enabled:
            return
        now = time.monotonic()
        if not force and (now - self._last_render) < _MIN_INTERVAL:
            return
        self._last_render = now
        width = max(20, shutil.get_terminal_size(fallback=(80, 24)).columns - 1)
        line = self._compose(width)
        if colors.enabled():
            line = colors.format_msg(line)
        try:
            self._stream.write('\r' + line + '\x1b[K')
            self._stream.flush()
        except Exception:
            self.enabled = False
            return
        self._drawn = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Erase the line if one is drawn, so other output can print cleanly.

        Called by Engine.log()/vlog() before every write: those go to stdout,
        which is usually the same terminal, and would otherwise be spliced
        into the middle of the progress line.
        """
        if not self.enabled or not self._drawn:
            return
        try:
            self._stream.write(_ERASE_LINE)
            self._stream.flush()
        except Exception:
            self.enabled = False
        self._drawn = False

    def start(self, url: str) -> None:
        """A task began; show its URL so the line moves even on slow sources."""
        if not self.enabled:
            return
        self.current = _display_url(url)
        self._render()

    def advance(self, urls: int) -> None:
        """A task finished. *urls* is the running total collected so far."""
        if not self.enabled:
            return
        self.done += 1
        self.urls = urls
        self._render(force=self.done >= self.total)

    def finish(self) -> None:
        """Clear the line for good, right before the round's summary prints."""
        self.clear()


class NullProgress(Progress):
    """Always-off Progress, so callers can stay branch-free."""

    def __init__(self) -> None:
        super().__init__(round_no=0, rounds=0, total=0, baseline=0, enabled=False)
