# -*- coding: utf-8 -*-
"""接头第五段/第六段，以及分纤盒配线链路排名。户数多的号小，户数相同则更长的号小。"""
from .ntal_graph import (
    LINK_LENGTH_TIE_M,
    ROLE_FAT,
    ROLE_SPLICE,
    other_end,
)


def hh_is_zero_or_empty(node):
    try:
        return abs(float((node or {}).get("hh") or 0.0)) < 1e-12
    except (TypeError, ValueError):
        return True


def edge_length_m(edge, work_crs):
    from .ntal_engine import _layer_crs, _transform_geom, _xform

    if (edge or {}).get("length") is not None:
        return float(edge["length"])
    layer = (edge or {}).get("layer")
    fid = (edge or {}).get("fid")
    if layer is None or fid is None:
        return 0.0
    feat = layer.getFeature(fid)
    if not feat.isValid():
        return 0.0
    geom = feat.geometry()
    if geom is None or geom.isEmpty():
        return 0.0
    moved = _transform_geom(geom, _xform(_layer_crs(layer), work_crs))
    if moved is None:
        moved = geom
    try:
        return float(moved.length())
    except Exception:
        return 0.0


def _walk_chain(start_eid, splice_id, dist_graph, dist_adj, node_map, edge_map, hard, scheme=None):
    fats = []
    seen = set()
    current_edge = start_eid
    current_from = splice_id
    while current_edge:
        if current_edge in seen:
            hard.append({
                "kind": "cycle",
                "message": "配线成环：{}".format(
                    (edge_map.get(current_edge) or {}).get("label") or current_edge
                ),
                "refs": [("edge", current_edge), ("node", current_from)],
            })
            return None
        seen.add(current_edge)
        nxt = other_end(dist_graph.get(current_edge) or {}, current_from)
        label = (edge_map.get(current_edge) or {}).get("label") or current_edge
        if nxt is None:
            hard.append({
                "kind": "dangling",
                "message": "一端空：{}".format(label),
                "refs": [("edge", current_edge), ("node", current_from)],
            })
            return None
        node = node_map.get(nxt)
        if node is None or node.get("role") != ROLE_FAT:
            hard.append({
                "kind": "bad_role",
                "message": "接头配线另一端不是分纤盒：{}".format(label),
                "refs": [("edge", current_edge)] + ([("node", nxt)] if nxt else []),
            })
            return None
        fats.append(nxt)
        outs = []
        for out_eid in dist_adj.get(nxt, []):
            if out_eid == current_edge:
                continue
            out_dest = other_end(dist_graph.get(out_eid) or {}, nxt)
            dest_node = node_map.get(out_dest) if out_dest else None
            if out_dest is None or (dest_node and dest_node.get("role") == ROLE_FAT):
                outs.append(out_eid)
            elif dest_node and dest_node.get("role") == ROLE_SPLICE and out_dest != splice_id:
                outs.append(out_eid)
        from .ntal_scheme import topology_of

        fat_max_out = topology_of(scheme).get("fat_max_out")
        if fat_max_out is not None and len(outs) > fat_max_out:
            hard.append({
                "kind": "fat_branch",
                "message": "分纤盒分叉（出 {} 条配线）：{}".format(
                    len(outs), node.get("label") or nxt
                ),
                "refs": [("node", nxt)] + [("edge", item) for item in outs],
            })
            return None
        if len(outs) == 1:
            current_from = nxt
            current_edge = outs[0]
            continue
        break
    if not fats:
        hard.append({
            "kind": "bad_role",
            "message": "接头配线另一端不是分纤盒：{}".format(
                (edge_map.get(start_eid) or {}).get("label") or start_eid
            ),
            "refs": [("edge", start_eid), ("node", splice_id)],
        })
        return None
    return fats


def collect_splice_chains(splice_ids, dist_graph, dist_adj, node_map, edge_map, hard, warn, warn_empty=False, scheme=None):
    """每个接头的每条出线走到串尾 = 一条链路。没有配线不占接头编号。"""
    claimed = {}
    chains = []
    skipped = set()
    for splice_id in splice_ids:
        outgoing = []
        for eid in dist_adj.get(splice_id, []):
            dest = other_end(dist_graph.get(eid) or {}, splice_id)
            if dest == splice_id:
                hard.append({
                    "kind": "self_loop",
                    "message": "配线两端接到同一接头：{}".format(
                        (edge_map.get(eid) or {}).get("label") or eid
                    ),
                    "refs": [("edge", eid), ("node", splice_id)],
                })
                continue
            outgoing.append(eid)
        if not outgoing:
            skipped.add(splice_id)
            if warn_empty:
                node = node_map.get(splice_id) or {}
                warn.append({
                    "kind": "splice_no_out",
                    "message": "接头后面没有配线，没有分纤盒可命名：{}".format(node.get("label") or splice_id),
                    "refs": [("node", splice_id)],
                })
            continue
        for eid in outgoing:
            fats = _walk_chain(eid, splice_id, dist_graph, dist_adj, node_map, edge_map, hard, scheme)
            if fats is None:
                continue
            blocked = False
            for fat_id in fats:
                if fat_id in claimed:
                    hard.append({
                        "kind": "fat_multi_in",
                        "message": "分纤盒被多条配线占用：{}".format(
                            (node_map.get(fat_id) or {}).get("label") or fat_id
                        ),
                        "refs": [("node", fat_id), ("node", splice_id)],
                    })
                    blocked = True
                    break
            if blocked:
                continue
            for fat_id in fats:
                claimed[fat_id] = splice_id
            chains.append({
                "splice_id": splice_id,
                "first_edge": eid,
                "fats": fats,
            })
    return chains, claimed, skipped


def rank_chains(chains, node_map, edge_map, work_crs, hard, link_base=1, link_mode="increment", box_mode="restart_01_per_chain"):
    """按户数（多的在前）、首段配线长（长的在前）编号。户数且长度都相同则硬错误。

    link_mode=increment：第五段 = link_base、link_base+1…
    link_mode=fixed：第五段都是 link_base（跟接头共用第五段）。
    box_mode=restart_01_per_chain：每条链第六段从 01 起。
    box_mode=continue_odf / continue_splice：第六段在这一组里连续加。
    """
    prepared = []
    for chain in chains:
        hh = 0.0
        zero = False
        for fat_id in chain["fats"]:
            node = node_map.get(fat_id) or {}
            if hh_is_zero_or_empty(node):
                hard.append({
                    "kind": "fat_hh_zero",
                    "message": "分纤盒户数为 0 或空：{}".format(node.get("label") or fat_id),
                    "refs": [("node", fat_id)],
                })
                zero = True
            try:
                hh += float(node.get("hh") or 0.0)
            except (TypeError, ValueError):
                hh += 0.0
        item = dict(chain)
        item["hh"] = 0.0 if zero else hh
        item["length"] = edge_length_m(edge_map.get(chain["first_edge"]), work_crs)
        prepared.append(item)
    prepared.sort(key=lambda item: (
        -float(item["hh"]),
        -float(item["length"]),
        item.get("first_edge") or "",
    ))
    for i in range(len(prepared) - 1):
        a = prepared[i]
        b = prepared[i + 1]
        if abs(a["hh"] - b["hh"]) < 1e-12 and abs(a["length"] - b["length"]) < LINK_LENGTH_TIE_M:
            hard.append({
                "kind": "link_tie",
                "message": "两条链路户数相同且到首盒距离差不到 1 毫米：{} / {}".format(
                    (edge_map.get(a["first_edge"]) or {}).get("label") or a["first_edge"],
                    (edge_map.get(b["first_edge"]) or {}).get("label") or b["first_edge"],
                ),
                "refs": [("edge", a["first_edge"]), ("edge", b["first_edge"])],
            })
    base = int(link_base or 1)
    if base < 1:
        base = 1
    for index, item in enumerate(prepared):
        item["link"] = base if link_mode == "fixed" else base + index
    splice_link = {}
    for item in prepared:
        sid = item["splice_id"]
        if sid not in splice_link or item["link"] < splice_link[sid]:
            splice_link[sid] = item["link"]
    fat_places = {}
    box_no = 0
    for item in prepared:
        if box_mode == "restart_01_per_chain":
            box_no = 0
        for seq, fat_id in enumerate(item["fats"]):
            box_no += 1
            fat_places[fat_id] = {
                "link": item["link"],
                "fat_no": box_no if box_mode != "restart_01_per_chain" else 1 + seq,
                "seq": seq + 1,
                "splice_id": item["splice_id"],
                "hh": item["hh"],
                "length": item["length"],
            }
    return prepared, splice_link, fat_places


def direct_chain_hh(chains, node_map, hard):
    """每个接头自己接出去的配线户数，不含下接接头。户数为 0 记硬错误。"""
    totals = {}
    seen_zero = set()
    for chain in chains:
        hh = 0.0
        zero = False
        for fat_id in chain["fats"]:
            node = node_map.get(fat_id) or {}
            if hh_is_zero_or_empty(node):
                zero = True
                if fat_id not in seen_zero:
                    seen_zero.add(fat_id)
                    hard.append({
                        "kind": "fat_hh_zero",
                        "message": "分纤盒户数为 0 或空：{}".format(node.get("label") or fat_id),
                        "refs": [("node", fat_id)],
                    })
            try:
                hh += float(node.get("hh") or 0.0)
            except (TypeError, ValueError):
                hh += 0.0
        sid = chain["splice_id"]
        totals[sid] = totals.get(sid, 0.0) + (0.0 if zero else hh)
    return totals


def assign_splice_numbers(root_id, children_map, subtree_hh, hard, node_map, mode="branch_hh"):
    """给一棵主干上的接头写第五段、第六段。

    第一个接头固定 01-01。没有分叉就顺着这条链：第五段不变，第六段按走过的顺序加。
    有分叉时，户数多的一支接着当前第五段编；户数一样则到下一接头的主干更长的接着编。
    户数少的新开第五段。新支的第六段接在已经编到的最大第六段后面。
    同一批等待开新段的分叉，户数多的第五段更小，不按先遇到谁。
    返回 {接头 id: (第五段, 第六段)}。
    """
    assigned = {}
    seg6 = [0]
    seg5_next = [1]
    reported = set()

    def report_tie(left, right):
        key = tuple(sorted((left["id"], right["id"])))
        if key in reported:
            return
        reported.add(key)
        left_node = node_map.get(left["id"]) or {}
        right_node = node_map.get(right["id"]) or {}
        hard.append({
            "kind": "link_tie",
            "message": "两条下接主干户数相同且到下一接头距离差不到 1 毫米：{} / {}".format(
                left_node.get("label") or left["id"],
                right_node.get("label") or right["id"],
            ),
            "refs": [("node", left["id"]), ("node", right["id"])],
        })

    def fork_rows(parent_id):
        rows = []
        for child_id, length, _eid in children_map.get(parent_id) or []:
            rows.append({
                "id": child_id,
                "length": float(length or 0.0),
                "hh": float(subtree_hh.get(child_id) or 0.0),
            })
        rows.sort(key=lambda item: (-item["hh"], -item["length"], item["id"] or ""))
        for index in range(len(rows) - 1):
            left = rows[index]
            right = rows[index + 1]
            if (
                abs(left["hh"] - right["hh"]) < 1e-12
                and abs(left["length"] - right["length"]) < LINK_LENGTH_TIE_M
            ):
                report_tie(left, right)
        return rows

    if mode in ("linear", "new_link_each"):
        assigned = {}
        n = [0]

        def walk(sid):
            if not sid or sid in assigned:
                return
            n[0] += 1
            assigned[sid] = (1, n[0]) if mode == "linear" else (n[0], 1)
            for row in fork_rows(sid):
                walk(row["id"])

        walk(root_id)
        return assigned

    def number_spine(start_id, seg5):
        sides = []
        current = start_id
        while current and current not in assigned:
            seg6[0] += 1
            assigned[current] = (int(seg5), seg6[0])
            kids = fork_rows(current)
            if not kids:
                break
            if len(kids) == 1:
                current = kids[0]["id"]
                continue
            sides.extend(kids[1:])
            current = kids[0]["id"]
        return sides

    def number_branch(start_id, seg5):
        sides = number_spine(start_id, seg5)
        sides.sort(key=lambda item: (-item["hh"], -item["length"], item["id"] or ""))
        for index in range(len(sides) - 1):
            left = sides[index]
            right = sides[index + 1]
            if (
                abs(left["hh"] - right["hh"]) < 1e-12
                and abs(left["length"] - right["length"]) < LINK_LENGTH_TIE_M
            ):
                report_tie(left, right)
        for side in sides:
            seg5_next[0] += 1
            number_branch(side["id"], seg5_next[0])

    if not root_id:
        return assigned
    number_branch(root_id, 1)
    return assigned
