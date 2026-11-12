# -*- coding: utf-8 -*-
"""Line-direction walk on a graph of line ends. No QGIS imports.

Nodes are snapped line-end clusters. All start nodes act as one source.
"""
import heapq
import math
from collections import defaultdict

_ROOT = -1


def _edge_step(eid, edge_map):
    edge = edge_map.get(eid) or {}
    try:
        step = float(edge.get("length") or 0.0)
    except (TypeError, ValueError):
        step = 0.0
    if step <= 0:
        try:
            step = math.hypot(edge["start"][0] - edge["end"][0], edge["start"][1] - edge["end"][1])
        except (KeyError, TypeError, IndexError):
            step = 0.0
    return step if step > 0 else 1e-6


def _blocks(entry, items):
    """Biconnected blocks of the part of the graph reachable from entry.

    items are (eid, u, v) with u != v; parallel lines are separate items.
    Returns [(block_entry, [item, ...]), ...]; block_entry is the block's
    vertex closest to entry, so flow can only come into the block there.
    """
    adj = defaultdict(list)
    for item in items:
        _eid, u, v = item
        adj[u].append((v, item))
        adj[v].append((u, item))
    disc = {entry: 0}
    low = {entry: 0}
    counter = 1
    edge_stack = []
    blocks = []
    stack = [(entry, None, iter(adj.get(entry, ())))]
    while stack:
        node, via, it = stack[-1]
        advanced = False
        for other, item in it:
            if via is not None and item[0] == via:
                continue
            if other not in disc:
                disc[other] = low[other] = counter
                counter += 1
                edge_stack.append(item)
                stack.append((other, item[0], iter(adj.get(other, ()))))
                advanced = True
                break
            if disc[other] < disc[node]:
                low[node] = min(low[node], disc[other])
                edge_stack.append(item)
        if advanced:
            continue
        stack.pop()
        if not stack:
            continue
        parent = stack[-1][0]
        low[parent] = min(low[parent], low[node])
        if low[node] >= disc[parent]:
            block = []
            while edge_stack:
                item = edge_stack.pop()
                block.append(item)
                if item[0] == via:
                    break
            blocks.append((parent, block))
    return blocks


def _distances(entry, items, edge_map):
    adj = defaultdict(list)
    for eid, u, v in items:
        adj[u].append((v, eid))
        adj[v].append((u, eid))
    best = {entry: 0.0}
    parent = {}
    heap = [(0.0, 0, entry)]
    seq = 1
    done = set()
    while heap:
        dist, _n, node = heapq.heappop(heap)
        if node in done:
            continue
        done.add(node)
        for other, eid in adj.get(node, ()):
            ndist = dist + _edge_step(eid, edge_map)
            if ndist < best.get(other, 1e300) - 1e-12:
                best[other] = ndist
                parent[other] = eid
                heapq.heappush(heap, (ndist, seq, other))
                seq += 1
    return best, parent


def _walk_ring(entry, block, edge_map, forward, pseudo):
    """A ring with no end on it: the nearer start wins, the meeting line stays open."""
    nodes = set()
    for _eid, u, v in block:
        nodes.add(u)
        nodes.add(v)
    if len(nodes) <= 2:
        # Only parallel lines between the entry and one other point.
        for eid, u, _v in block:
            forward[eid] = u == entry
        return
    # A block with three or more points stays connected without any one pair
    # of points' lines, so every line off the shortest-path tree is reached
    # from both sides.
    best, parent = _distances(entry, block, edge_map)
    tree = set(parent.values())
    for eid, u, v in block:
        if eid in tree:
            forward[eid] = best.get(u, 1e300) <= best.get(v, 1e300)
        else:
            pseudo.append(eid)


def _orient(entry, items, terminals, edge_map, forward, pseudo, cut_ends, ambiguous, interior):
    """Orient every line reachable from entry, block by block.

    A bridge (no ring around it) flows away from the start; branches are
    normal. An end only matters on a ring, and only when it is the single
    place the ring can be cut: that end sits on a junction, not in the
    middle of a line, and no other end on the same ring could be the cut.
    The ring opens there and both sides run toward it.

    Anything else on a ring has no direction. No end, several ends, or an
    end lying on a line instead of a junction: those lines stay out of
    ``forward`` and are reported so a temporary layer can be written.
    Guessing the farther end would look like a clean result.
    """
    interior = interior or set()
    tasks = [(entry, list(items))]
    tried = set()
    while tasks:
        start, part = tasks.pop()
        for block_entry, block in _blocks(start, part):
            if len(block) == 1:
                eid, u, _v = block[0]
                forward[eid] = u == block_entry
                continue
            nodes = set()
            for _eid, u, v in block:
                nodes.add(u)
                nodes.add(v)
            candidates = [
                node for node in nodes
                if node != block_entry and node in terminals and node not in tried
            ]
            inside = any(eid in interior for eid, _u, _v in block)
            # Exactly one junction-end, and no end sitting mid-line.
            if len(candidates) == 1 and not inside:
                tried.update(candidates)
                cuts = set(candidates)
                cut_ends.update(cuts)
                tasks.append((block_entry, _split_at(block, cuts)))
                continue
            # Several possible cuts, or an end that is not on a junction.
            if len(candidates) > 1 or inside:
                for eid, _u, _v in block:
                    ambiguous.append(eid)
                continue
            _walk_ring(block_entry, block, edge_map, forward, pseudo)


def _split_at(block, cuts):
    split = []
    for eid, u, v in block:
        if u in cuts:
            u = ("cut", u, eid)
        if v in cuts:
            v = ("cut", v, eid)
        split.append((eid, u, v))
    return split


def _walk(roots, edges, end_nodes, terminals=None, interior_edges=None):
    """从全部起点同时往外走。全部起点看成同一个源头。

    每个线端点是一个连接点，分叉的每一支都顺着往外走，不算错误。
    终点只在成环、并且能唯一断开的时候起作用：环上正好一个终点，
    落在线的接头上，环就在那里断开，两边的线各自朝终点走。
    不成环的地方终点不起作用。
    环上没有终点时，近的起点先到，两头碰面的那条线分不出方向，叫伪成环。
    环上有多个终点，或终点落在线中间而不是接头上，整环都分不出方向。

    interior_edges：终点落在线的中间（没贴到任一端点）的线。
    返回 (oriented, self_loops, pseudo, cut_ends, ambiguous)。
    """
    edge_map = {edge["id"]: edge for edge in edges}
    roots = set(roots or ())
    terminals = set(terminals or ()) - roots

    def alias(node):
        return _ROOT if node in roots else node

    items = []
    self_loops = []
    pseudo = []
    for edge in edges:
        eid = edge["id"]
        a, b = end_nodes[eid]
        if a == b:
            self_loops.append(eid)
            continue
        u, v = alias(a), alias(b)
        if u == v:
            # Both ends sit on start points: no side to come from.
            pseudo.append(eid)
            continue
        items.append((eid, u, v))
    forward = {}
    cut_ends = set()
    ambiguous = []
    if roots:
        _orient(
            _ROOT, items, terminals, edge_map, forward, pseudo, cut_ends,
            ambiguous, interior_edges or set(),
        )
    oriented = {}
    for eid in self_loops:
        a, _b = end_nodes[eid]
        oriented[eid] = (a, a)
    for eid, flag in forward.items():
        a, b = end_nodes[eid]
        oriented[eid] = (a, b) if flag else (b, a)
    ambiguous = [eid for eid in ambiguous if eid not in oriented]
    amb_set = set(ambiguous)
    pseudo = [eid for eid in pseudo if eid not in oriented and eid not in amb_set]
    return oriented, self_loops, pseudo, cut_ends, ambiguous
