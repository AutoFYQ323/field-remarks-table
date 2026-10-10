# -*- coding: utf-8 -*-
import sys
from collections import defaultdict
from contextlib import contextmanager


ROLE_OCC = "occ"
ROLE_SPLICE = "splice"
ROLE_FAT = "fat"
ROLE_TRUNK = "trunk"
ROLE_DIST = "dist"
ROLE_CABLE = "cable"
ROLE_DROP = "drop"
ROLE_USER = "user"
LINK_LENGTH_TIE_M = 0.001

HARD_CYCLE = "cycle"
HARD_FAT_BRANCH = "fat_branch"
HARD_FAT_MULTI_IN = "fat_multi_in"
HARD_SPLICE_MULTI_IN = "splice_multi_in"
HARD_OCC_IN = "occ_in"
HARD_SELF_LOOP = "self_loop"

WARN_DANGLING = "dangling"
WARN_UNREACHED_EDGE = "unreached_edge"
WARN_UNREACHED_NODE = "unreached_node"
WARN_OCC_NO_OUT = "occ_no_out"
WARN_BOTH_OPEN = "both_open"


@contextmanager
def deep_recursion(limit=20000):
    """长链路逐点递归，临时放宽递归上限。"""
    old = sys.getrecursionlimit()
    if old < limit:
        sys.setrecursionlimit(limit)
    try:
        yield
    finally:
        sys.setrecursionlimit(old)


def other_end(edge, node_id):
    if edge.get("a") == node_id:
        return edge.get("b")
    if edge.get("b") == node_id:
        return edge.get("a")
    return None


def _issue(kind, message, refs=None):
    return {"kind": kind, "message": message, "refs": list(refs or [])}


def analyze_graph(nodes, edges, occ_ids, accumulate=True, scheme=None):
    """Orient from OCC roots and put FAT households onto edges.

    accumulate 只决定线上户数怎么加。进线/出线条数是否报错看组网方案。
    accumulate=True: 线上户数 = 到达分纤盒 + 下游所有出线（旧规则）。
    accumulate=False: 线上户数 = 到达的那一个分纤盒（新规则）。
    """
    from .ntal_scheme import topology_of

    topo = topology_of(scheme)
    issues = []
    adj = defaultdict(list)
    for eid, edge in edges.items():
        if edge.get("a"):
            adj[edge["a"]].append(eid)
        if edge.get("b") and edge.get("b") != edge.get("a"):
            adj[edge["b"]].append(eid)

    oriented = {}
    has_in = set()

    def orient(eid, fr, to):
        oriented[eid] = (fr, to)
        has_in.add(to)

    def dfs(nid, via_edge, stack):
        if nid not in nodes:
            return
        if nid in stack:
            issues.append(_issue(
                HARD_CYCLE,
                "成环：{}".format(nodes[nid].get("label") or nid),
                [("node", nid)],
            ))
            return
        stack.add(nid)
        for eid in adj.get(nid, []):
            if eid == via_edge:
                continue
            edge = edges[eid]
            other = other_end(edge, nid)
            label = edge.get("label") or eid
            if eid in oriented:
                continue
            if other is None:
                issues.append(_issue(
                    WARN_DANGLING,
                    "一端空：{}".format(label),
                    [("edge", eid), ("node", nid)],
                ))
                continue
            if other == nid:
                issues.append(_issue(
                    HARD_SELF_LOOP,
                    "线两端接到同一点：{}".format(label),
                    [("edge", eid), ("node", nid)],
                ))
                continue
            parent = other_end(edges[via_edge], nid) if via_edge else None
            if other in stack:
                if other != parent:
                    issues.append(_issue(
                        HARD_CYCLE,
                        "成环：{} ↔ {}".format(nodes[nid].get("label") or nid, label),
                        [("edge", eid), ("node", nid), ("node", other)],
                    ))
                continue
            other_role = (nodes.get(other) or {}).get("role")
            if other_role == ROLE_OCC:
                orient(eid, other, nid)
                continue
            if other in has_in:
                orient(eid, nid, other)
                continue
            orient(eid, nid, other)
            dfs(other, eid, stack)
        stack.remove(nid)

    with deep_recursion():
        for occ_id in occ_ids:
            if occ_id in nodes:
                dfs(occ_id, None, set())

    incoming = defaultdict(list)
    outgoing = defaultdict(list)
    for eid, pair in oriented.items():
        fr, to = pair
        outgoing[fr].append(eid)
        incoming[to].append(eid)

    for nid, node in nodes.items():
        role = node.get("role")
        label = node.get("label") or nid
        fat_max_in = topo.get("fat_max_in")
        fat_max_out = topo.get("fat_max_out")
        splice_max_in = topo.get("splice_max_in")
        if role == ROLE_FAT and fat_max_in is not None and len(incoming[nid]) > fat_max_in:
            refs = [("node", nid)] + [("edge", eid) for eid in incoming[nid]]
            issues.append(_issue(
                HARD_FAT_MULTI_IN,
                "分纤盒进入 {} 条线：{}".format(len(incoming[nid]), label),
                refs,
            ))
        if role == ROLE_FAT and fat_max_out is not None and len(outgoing[nid]) > fat_max_out:
            refs = [("node", nid)] + [("edge", eid) for eid in outgoing[nid]]
            issues.append(_issue(
                HARD_FAT_BRANCH,
                "分纤盒分叉（出 {} 条线）：{}".format(len(outgoing[nid]), label),
                refs,
            ))
        if role == ROLE_SPLICE and splice_max_in is not None and len(incoming[nid]) > splice_max_in:
            refs = [("node", nid)] + [("edge", eid) for eid in incoming[nid]]
            issues.append(_issue(
                HARD_SPLICE_MULTI_IN,
                "接头进入 {} 条线：{}".format(len(incoming[nid]), label),
                refs,
            ))
        if role == ROLE_OCC and incoming[nid] and topo.get("occ_in_hard", True):
            refs = [("node", nid)] + [("edge", eid) for eid in incoming[nid]]
            issues.append(_issue(
                HARD_OCC_IN,
                "光交被当作下游：{}".format(label),
                refs,
            ))
        if role == ROLE_OCC and not outgoing[nid]:
            issues.append(_issue(
                WARN_OCC_NO_OUT,
                "光交没有出线：{}".format(label),
                [("node", nid)],
            ))

    for eid, edge in edges.items():
        if eid in oriented:
            continue
        a, b = edge.get("a"), edge.get("b")
        label = edge.get("label") or eid
        if not a and not b:
            issues.append(_issue(
                WARN_BOTH_OPEN,
                "两端都空：{}".format(label),
                [("edge", eid)],
            ))
        elif a and b:
            issues.append(_issue(
                WARN_UNREACHED_EDGE,
                "未挂上（未从光交通到）：{}".format(label),
                [("edge", eid)],
            ))
        elif a or b:
            issues.append(_issue(
                WARN_DANGLING,
                "一端空：{}".format(label),
                [("edge", eid)],
            ))

    reached_nodes = set()
    for fr, to in oriented.values():
        reached_nodes.add(fr)
        reached_nodes.add(to)
    for occ_id in occ_ids:
        if occ_id in nodes:
            reached_nodes.add(occ_id)
    for nid, node in nodes.items():
        if nid in reached_nodes:
            continue
        issues.append(_issue(
            WARN_UNREACHED_NODE,
            "未挂上：{}".format(node.get("label") or nid),
            [("node", nid)],
        ))

    values = {}
    memo = {}

    def edge_value(eid, stack):
        if eid in memo:
            return memo[eid]
        if eid in stack:
            return 0.0
        stack.add(eid)
        _fr, to = oriented[eid]
        dest = nodes.get(to) or {}
        total = float(dest.get("hh") or 0) if dest.get("role") == ROLE_FAT else 0.0
        if accumulate:
            for out_eid in outgoing.get(to, []):
                total += edge_value(out_eid, stack)
        stack.remove(eid)
        memo[eid] = total
        return total

    with deep_recursion():
        for eid in oriented:
            values[eid] = edge_value(eid, set())

    hard_kinds = {
        HARD_CYCLE, HARD_FAT_BRANCH, HARD_FAT_MULTI_IN,
        HARD_SPLICE_MULTI_IN, HARD_OCC_IN, HARD_SELF_LOOP,
    }
    hard = [item for item in issues if item["kind"] in hard_kinds]
    warn = [item for item in issues if item["kind"] not in hard_kinds]
    return {
        "oriented": oriented,
        "values": values,
        "incoming": dict(incoming),
        "outgoing": dict(outgoing),
        "hard": hard,
        "warn": warn,
        "reached_nodes": reached_nodes,
    }


def analyze_drops(links):
    """Group FAT-user drop links: exclude duplicate and multi-FAT users, sum the rest.

    links: [{drop_id, fat_id, user_id, hh}]
    """
    by_pair = defaultdict(list)
    by_user_fats = defaultdict(set)
    by_user_links = defaultdict(list)
    for link in links:
        by_pair[(link["fat_id"], link["user_id"])].append(link)
        by_user_fats[link["user_id"]].add(link["fat_id"])
        by_user_links[link["user_id"]].append(link)

    dup_users = set()
    dup_rows = []
    for (fat_id, user_id), items in by_pair.items():
        if len(items) <= 1:
            continue
        dup_users.add(user_id)
        dup_rows.append({
            "fat_id": fat_id,
            "user_id": user_id,
            "drop_ids": [item["drop_id"] for item in items],
            "drop_count": len(items),
            "hh": items[0].get("hh") or 0.0,
        })

    multi_users = set()
    multi_rows = []
    for user_id, fats in by_user_fats.items():
        if len(fats) <= 1:
            continue
        multi_users.add(user_id)
        multi_rows.append({
            "user_id": user_id,
            "fat_ids": sorted(fats),
            "fat_count": len(fats),
            "drop_count": len(by_user_links[user_id]),
            "hh": (by_user_links[user_id][0].get("hh") or 0.0),
        })

    excluded = dup_users | multi_users
    fat_sums = {}
    fat_user_ids = defaultdict(set)
    for link in links:
        if link["user_id"] in excluded:
            continue
        fat_user_ids[link["fat_id"]].add(link["user_id"])
    hh_by_user = {}
    for link in links:
        hh_by_user[link["user_id"]] = float(link.get("hh") or 0.0)
    fat_user_counts = {}
    for fat_id, users in fat_user_ids.items():
        fat_user_counts[fat_id] = len(users)
        fat_sums[fat_id] = sum(hh_by_user.get(uid, 0.0) for uid in users)
    return {
        "dup_users": dup_users,
        "dup_rows": dup_rows,
        "multi_users": multi_users,
        "multi_rows": multi_rows,
        "excluded": excluded,
        "fat_sums": fat_sums,
        "fat_user_counts": fat_user_counts,
    }
