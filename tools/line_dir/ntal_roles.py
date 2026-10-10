# -*- coding: utf-8 -*-
"""光缆两端角色：只看端点吸附到的点，不看线中间折点。"""
from .ntal_graph import (
    ROLE_DIST,
    ROLE_DROP,
    ROLE_FAT,
    ROLE_OCC,
    ROLE_SPLICE,
    ROLE_TRUNK,
    ROLE_USER,
)

from .ntal_scheme import topology_of

ROLE_NAME = {
    ROLE_OCC: "光交",
    ROLE_SPLICE: "接头",
    ROLE_FAT: "分纤盒",
    ROLE_USER: "用户点",
}


def _pair(role_a, role_b):
    return frozenset(item for item in (role_a, role_b) if item)


def _role_names(role_a, role_b):
    left = ROLE_NAME.get(role_a) or "空"
    right = ROLE_NAME.get(role_b) or "空"
    return left, right


def classify_cable_pair(role_a, role_b, scheme=None):
    """光缆（合并后的主干/配线）。合法两端对由组网方案决定。

    返回 (role, severity, kind, message_tail)
    role: trunk / dist / None
    severity: None / hard / warn
    """
    if not role_a and not role_b:
        return None, "warn", "both_open", "两端都空"
    if not role_a or not role_b:
        return None, "hard", "dangling", "一端空"
    pair = _pair(role_a, role_b)
    topo = topology_of(scheme)
    if pair in topo["trunk_pairs"]:
        return ROLE_TRUNK, None, None, ""
    if pair in topo["dist_pairs"]:
        return ROLE_DIST, None, None, ""
    left, right = _role_names(role_a, role_b)
    return None, "hard", "bad_role", "{}接到{}".format(left, right)


def classify_drop_pair(role_a, role_b, scheme=None):
    """皮线。一头空 / 两头空都是软错误。合法两端对由组网方案决定。"""
    if not role_a and not role_b:
        return None, "warn", "both_open", "两端都空"
    if not role_a or not role_b:
        return None, "warn", "dangling", "一端空"
    pair = _pair(role_a, role_b)
    if pair in topology_of(scheme)["drop_pairs"]:
        return ROLE_DROP, None, None, ""
    left, right = _role_names(role_a, role_b)
    if pair == frozenset((ROLE_FAT,)):
        return None, "warn", "drop_both_fat", "两端都是分纤盒"
    if pair == frozenset((ROLE_USER,)):
        return None, "warn", "drop_both_user", "两端都是用户"
    return None, "warn", "bad_role", "{}接到{}".format(left, right)


def apply_role_label(edge, role, role_label):
    raw = (edge.get("label") or "").strip()
    title = role_label.get(role, role)
    parts = raw.split(" ", 1)
    if len(parts) == 2:
        edge["label"] = "{} {}".format(title, parts[1])
    else:
        edge["label"] = "{} {}".format(title, raw or edge.get("id") or "")
    edge["role"] = role
    return edge


def snap_and_classify_cables(cable_rows, node_rows, tolerance, hard, warn, role_label, scheme=None):
    """吸附光缆两端并判定主干/配线。歧义进硬错误。"""
    from .ntal_engine import _build_index, _snap_end

    index, by_int = _build_index(node_rows)
    node_map = {row["id"]: row for row in node_rows}
    trunk_rows = []
    dist_rows = []
    bindings = {}
    for edge in cable_rows:
        a, amb_a = _snap_end(edge["start"], index, by_int, tolerance)
        b, amb_b = _snap_end(edge["end"], index, by_int, tolerance)
        for amb, side in ((amb_a, "起点"), (amb_b, "终点")):
            if amb:
                hard.append({
                    "kind": "snap_ambig",
                    "message": "光缆{}同时靠近多个点：{}".format(side, edge["label"]),
                    "refs": [("edge", edge["id"])] + [("node", nid) for nid in amb],
                })
        ra = (node_map.get(a) or {}).get("role") if a else None
        rb = (node_map.get(b) or {}).get("role") if b else None
        role, severity, kind, tail = classify_cable_pair(ra, rb, scheme)
        bound = dict(edge)
        bound["a"] = a
        bound["b"] = b
        if role:
            apply_role_label(bound, role, role_label)
        else:
            bound["role"] = edge.get("role")
        bindings[edge["id"]] = bound
        if severity:
            hard.append({
                "kind": kind,
                "message": "{}：{}".format(tail, bound["label"]),
                "refs": [("edge", edge["id"])]
                + ([("node", a)] if a else [])
                + ([("node", b)] if b else []),
            }) if severity == "hard" else warn.append({
                "kind": kind,
                "message": "{}：{}".format(tail, bound["label"]),
                "refs": [("edge", edge["id"])]
                + ([("node", a)] if a else [])
                + ([("node", b)] if b else []),
            })
        if role == ROLE_TRUNK:
            trunk_rows.append(bound)
        elif role == ROLE_DIST:
            dist_rows.append(bound)
    return trunk_rows, dist_rows, bindings, node_map


def adj_from_rows(rows):
    graph = {}
    adj = {}
    for edge in rows:
        eid = edge["id"]
        graph[eid] = {
            "a": edge.get("a"),
            "b": edge.get("b"),
            "label": edge.get("label"),
        }
        start_id = edge.get("a")
        end_id = edge.get("b")
        if start_id:
            adj.setdefault(start_id, []).append(eid)
        if end_id and end_id != start_id:
            adj.setdefault(end_id, []).append(eid)
    return graph, adj
