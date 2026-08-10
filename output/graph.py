"""
Page-link graph builder.

Converts a per-target result dict (as produced by Engine.run_target()) into a
node/edge structure suitable for graph visualization (vis-network, cytoscape,
gephi, etc.). Models the seed URL and every discovered URL as a flat star:
seed -> page (in-scope) or seed -> external (out-of-scope link encountered
along the way). True page-to-page adjacency isn't tracked by the sources
today, so this is "what was found from this seed," not a literal crawl graph.

Pure function — no I/O, no global state.
"""
from __future__ import annotations


_STATUS_COLORS = {
    '2xx': '#4caf50',  # green
    '3xx': '#ff9800',  # orange
    '4xx': '#f44336',  # red
    '5xx': '#9c27b0',  # purple
    'none': '#9e9e9e', # gray (unreachable / not probed)
}

_TYPE_COLORS = {
    'seed':     '#1976d2',  # blue
    'page':     '#9e9e9e',  # gray default (overridden by status)
    'external': '#757575',  # darker gray — out-of-scope link, not followed
}


def _status_color(status) -> str:
    if status is None:
        return _STATUS_COLORS['none']
    try:
        s = int(status)
    except (TypeError, ValueError):
        return _STATUS_COLORS['none']
    if 200 <= s < 300:
        return _STATUS_COLORS['2xx']
    if 300 <= s < 400:
        return _STATUS_COLORS['3xx']
    if 400 <= s < 500:
        return _STATUS_COLORS['4xx']
    if 500 <= s < 600:
        return _STATUS_COLORS['5xx']
    return _STATUS_COLORS['none']


def build_network_graph(result: dict) -> dict:
    """
    Build a page-link graph from a per-target result dict.

    Returns:
        {
          'nodes': [{'id', 'label', 'type', 'color', ...}, ...],
          'edges': [{'from', 'to', 'relation'}, ...],
          'stats': {'seeds', 'pages', 'externals', 'edges'},
        }
    """
    seed: str = result.get('seed', '')
    urls: set = result.get('urls', set()) or set()
    live: dict = result.get('live', {}) or {}
    url_sources: dict = result.get('url_sources', {}) or {}
    extras: dict = result.get('extras', {}) or {}
    external_urls: set = extras.get('urls_external', set()) or set()

    nodes: list[dict] = []
    edges: list[dict] = []
    seen_ids: set[str] = set()

    def add_node(node_id: str, **attrs) -> None:
        if not node_id or node_id in seen_ids:
            return
        seen_ids.add(node_id)
        attrs['id'] = node_id
        nodes.append(attrs)

    def add_edge(src: str, dst: str, relation: str) -> None:
        if not src or not dst or src == dst:
            return
        edges.append({'from': src, 'to': dst, 'relation': relation})

    # ── Root seed node ────────────────────────────────────────────────
    add_node(
        seed,
        label=seed,
        type='seed',
        color=_TYPE_COLORS['seed'],
        group=seed,
    )

    # ── Page nodes + links_to edges ──────────────────────────────────
    for url in sorted(urls):
        info = live.get(url, {}) or {}
        status = info.get('status')
        add_node(
            url,
            label=url,
            type='page',
            color=_status_color(status),
            status=status,
            title=info.get('title', '') or '',
            server=info.get('server', '') or '',
            source=url_sources.get(url, '') or '',
            group=seed,
        )
        add_edge(seed, url, 'links_to')

    # ── External (out-of-scope) URL nodes ────────────────────────────
    for url in sorted(external_urls):
        add_node(url, label=url, type='external', color=_TYPE_COLORS['external'])
        add_edge(seed, url, 'links_to_external')

    # ── Stats ────────────────────────────────────────────────────────
    counts: dict = {'seeds': 0, 'pages': 0, 'externals': 0}
    for n in nodes:
        t = n.get('type', '')
        key = {'seed': 'seeds', 'page': 'pages', 'external': 'externals'}.get(t)
        if key:
            counts[key] += 1
    counts['edges'] = len(edges)

    return {'nodes': nodes, 'edges': edges, 'stats': counts}


def merge_graphs(graphs: list[dict]) -> dict:
    """Combine multiple per-target graphs into a single graph (dedup nodes)."""
    nodes_by_id: dict[str, dict] = {}
    edges: list[dict] = []
    seen_edges: set[tuple] = set()

    for g in graphs:
        for n in g.get('nodes', []):
            nid = n.get('id')
            if nid and nid not in nodes_by_id:
                nodes_by_id[nid] = n
        for e in g.get('edges', []):
            key = (e.get('from'), e.get('to'), e.get('relation'))
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append(e)

    merged_nodes = list(nodes_by_id.values())
    counts: dict = {'seeds': 0, 'pages': 0, 'externals': 0}
    for n in merged_nodes:
        t = n.get('type', '')
        key = {'seed': 'seeds', 'page': 'pages', 'external': 'externals'}.get(t)
        if key:
            counts[key] += 1
    counts['edges'] = len(edges)

    return {'nodes': merged_nodes, 'edges': edges, 'stats': counts}
