"""
Per-target results store for SimpleReconURL.

A single `--db FILE` is used as both the comparison source (input) and the save
target (output). It holds **only recon results** (system/log data lives in the
fixed `config/system.db`, see core/system_db.py). The store is append-only;
rows are keyed by `seed` (the seed URL), so "known" lookups use `SELECT DISTINCT`
and the comparison baseline for `--db-news` is the union of everything ever
stored for a seed.

Schema (auto-created on first use)
----------------------------------
  urls    — every discovered URL, tagged with its source, plus optional
            live-check metadata (status/title/server/body_hash/response_ms)
  extras  — out-of-scope URLs found along the way (type 'url_external',
            populated only at -v 3)

Public API
----------
init_db(path)              — create schema if needed
save_result(path, result)  — persist one Engine result dict
load_known(path, seed)     — dict of sets of all previously seen values
filter_new(result, known)  — copy of result with only values absent from known
list_urls/list_extras      — read-only helpers for --db-list

Pure stdlib (`sqlite3`); no third-party dependency.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS urls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    seed        TEXT    NOT NULL,
    url         TEXT    NOT NULL,
    source      TEXT,
    first_seen  TEXT    NOT NULL,
    status      INTEGER,
    title       TEXT,
    server      TEXT,
    body_hash   TEXT,
    response_ms INTEGER
);

CREATE TABLE IF NOT EXISTS extras (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    seed       TEXT    NOT NULL,
    type       TEXT    NOT NULL,
    value      TEXT    NOT NULL,
    first_seen TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_url_seed   ON urls(seed);
CREATE INDEX IF NOT EXISTS idx_url_url    ON urls(url);
CREATE INDEX IF NOT EXISTS idx_extra_seed ON extras(seed, type);
"""

# Categories returned by load_known() and filtered by filter_new()
_KNOWN_KEYS = ('urls', 'urls_external', 'urls_assets')


def _connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str) -> None:
    """Create the schema in *path* if it doesn't already exist."""
    conn = sqlite3.connect(path)
    try:
        conn.execute('PRAGMA journal_mode = WAL')
        conn.executescript(_SCHEMA)
    finally:
        conn.close()


def save_result(path: str, result: dict) -> None:
    """Persist a single Engine result dict (results only) into the database at *path*."""
    init_db(path)

    seed: str          = result.get('seed', '')
    urls: set          = result.get('urls', set()) or set()
    live: dict         = result.get('live', {}) or {}
    url_sources: dict  = result.get('url_sources', {}) or {}
    extras: dict       = result.get('extras', {}) or {}
    ts = datetime.now(timezone.utc).isoformat()

    conn = _connect(path)
    try:
        with conn:
            for url in urls:
                info = live.get(url, {}) or {}
                conn.execute(
                    """INSERT INTO urls
                       (seed, url, source, first_seen,
                        status, title, server, body_hash, response_ms)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        seed, url, url_sources.get(url), ts,
                        info.get('status'),
                        info.get('title'),
                        info.get('server'),
                        info.get('body_hash'),
                        info.get('response_ms'),
                    ),
                )

            for key, kind in (('urls_external', 'url_external'), ('urls_assets', 'url_asset')):
                for val in (extras.get(key, set()) or set()):
                    conn.execute(
                        'INSERT INTO extras (seed, type, value, first_seen) VALUES (?, ?, ?, ?)',
                        (seed, kind, val, ts),
                    )
    finally:
        conn.close()


def load_known(path: str, seed: str) -> dict[str, set[str]]:
    """
    Return every value ever stored for *seed*, grouped by category.

    Keys: 'urls', 'urls_external'. Missing DB file (or any read error)
    yields empty sets, so a first run treats everything as new.
    """
    known: dict[str, set[str]] = {k: set() for k in _KNOWN_KEYS}
    try:
        init_db(path)
        conn = _connect(path)
    except sqlite3.Error:
        return known
    try:
        for row in conn.execute(
            'SELECT DISTINCT url FROM urls WHERE seed = ?', (seed,)
        ):
            known['urls'].add(row['url'])
        for row in conn.execute(
            "SELECT DISTINCT value FROM extras WHERE seed = ? AND type = 'url_external'", (seed,)
        ):
            known['urls_external'].add(row['value'])
        for row in conn.execute(
            "SELECT DISTINCT value FROM extras WHERE seed = ? AND type = 'url_asset'", (seed,)
        ):
            known['urls_assets'].add(row['value'])
    except sqlite3.Error:
        pass
    finally:
        conn.close()
    return known


def _list_query(path: str, sql: str, seed: str | None) -> list:
    """Run a read-only listing query, optionally filtered by seed. Empty on error."""
    try:
        conn = _connect(path)
    except sqlite3.Error:
        return []
    try:
        if seed:
            rows = conn.execute(sql + ' WHERE seed = ?' + _ORDER[sql], (seed,)).fetchall()
        else:
            rows = conn.execute(sql + _ORDER[sql]).fetchall()
        return [tuple(r) for r in rows]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


# Base SELECTs (without WHERE/ORDER) mapped to their ORDER BY clause
_SQL_URLS   = 'SELECT DISTINCT url, source FROM urls'
_SQL_EXTRAS = 'SELECT DISTINCT type, value FROM extras'
_ORDER = {
    _SQL_URLS:   ' ORDER BY url',
    _SQL_EXTRAS: ' ORDER BY type, value',
}


def list_urls(path: str, seed: str | None = None) -> list[tuple[str, str]]:
    """All distinct collected URLs as (url, source)."""
    return _list_query(path, _SQL_URLS, seed)


def list_extras(path: str, seed: str | None = None) -> list[tuple[str, str]]:
    """All distinct extras as (type, value) — external (out-of-scope) URLs."""
    return _list_query(path, _SQL_EXTRAS, seed)


def filter_new(result: dict, known: dict[str, set[str]]) -> dict:
    """
    Return a copy of *result* containing only values absent from *known*.

    Filters urls, prunes live metadata and url_sources to the surviving urls,
    and filters the external-URL extras. `seed` and `sources` are preserved
    unchanged.
    """
    known_urls          = known.get('urls', set())
    known_urls_external = known.get('urls_external', set())
    known_urls_assets   = known.get('urls_assets', set())

    new_urls = {u for u in (result.get('urls') or set()) if u not in known_urls}

    live = result.get('live', {}) or {}
    new_live = {u: info for u, info in live.items() if u in new_urls}

    url_sources = result.get('url_sources', {}) or {}
    new_url_sources = {u: s for u, s in url_sources.items() if u in new_urls}

    extras = result.get('extras', {}) or {}
    new_extras: dict[str, set] = {}
    filtered_external = {
        u for u in extras.get('urls_external', set()) if u not in known_urls_external
    }
    if filtered_external:
        new_extras['urls_external'] = filtered_external
    filtered_assets = {
        u for u in extras.get('urls_assets', set()) if u not in known_urls_assets
    }
    if filtered_assets:
        new_extras['urls_assets'] = filtered_assets

    # NB: this dict is rebuilt from a fixed key list and REPLACES the result
    # that reaches save_output(), so anything omitted here is silently dropped
    # from every output format. 'rounds'/'url_rounds' were being lost that way,
    # which made --db-news + --recursive drop the report's rounds section.
    return {
        'seed': result.get('seed', ''),
        'urls': new_urls,
        'live': new_live,
        'sources': result.get('sources', {}),
        'url_sources': new_url_sources,
        'extras': new_extras,
        'rounds': result.get('rounds', 1),
        'url_rounds': {
            u: r for u, r in (result.get('url_rounds', {}) or {}).items() if u in new_urls
        },
    }
