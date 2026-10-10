# -*- coding: utf-8 -*-
from ...i18n import tr
"""每个下拉功能各自一份方案。组网结构固定；变的是赋值怎么写、后三段怎么编号。"""
from .ntal_graph import ROLE_FAT, ROLE_OCC, ROLE_SPLICE, ROLE_USER

SCHEME_CURRENT = "current"
SCHEME_LEGACY_HH = "legacy_hh"
DEFAULT_SCHEME = SCHEME_CURRENT

ACTION_KEYS = ("drop", "fat", "line", "splice_code", "fat_code", "cable_code")
ASSIGN_ACTIONS = ("drop", "fat", "line")
NAME_ACTIONS = ("splice_code", "fat_code", "cable_code")

ACTION_TITLES = {
    "drop": "赋值·皮线",
    "fat": "赋值·分纤盒",
    "line": "赋值·主干配线",
    "splice_code": "命名·接头",
    "fat_code": "命名·分纤盒",
    "cable_code": "命名·主干配线",
}

_OCC_SPLICE = frozenset((ROLE_OCC, ROLE_SPLICE))
_SPLICE_SPLICE = frozenset((ROLE_SPLICE,))
_SPLICE_FAT = frozenset((ROLE_SPLICE, ROLE_FAT))
_FAT_FAT = frozenset((ROLE_FAT,))
_FAT_USER = frozenset((ROLE_FAT, ROLE_USER))

CURRENT_TOPOLOGY = {
    "trunk_pairs": frozenset((_OCC_SPLICE, _SPLICE_SPLICE)),
    "dist_pairs": frozenset((_SPLICE_FAT, _FAT_FAT)),
    "drop_pairs": frozenset((_FAT_USER,)),
    "fat_max_in": 1,
    "fat_max_out": 1,
    "splice_max_in": 1,
    "occ_in_hard": True,
}

CURRENT_NUMBERING = {
    "odf_sort": "first_trunk_length",
    "splice_link": "branch_hh",
    "fat_link_start": "after_max_splice_link",
    "fat_box": "restart_01_per_chain",
    "rank_scope": "odf",
    "share_5th": False,
}


def _item(sid, label, tip, household=None, numbering=None):
    return {
        "id": sid,
        "label": label,
        "tip": tip,
        "household": dict(household or {}),
        "numbering": dict(numbering or CURRENT_NUMBERING),
    }


ACTION_SCHEMES = {
    "drop": (
        _item(
            "current",
            "当前：抄用户户数",
            "读用户点户数，写到连上的皮线。一个用户接多个分纤盒时该皮线不写。没挂上的皮线保持原值。",
            household={"drop_value": "user_hh", "drop_multi": "skip"},
        ),
        _item(
            "write_one",
            "每条皮线写 1",
            "合格皮线一律写 1，不读用户点户数字段的数值。一个用户接多个分纤盒时仍不写。没挂上的皮线保持原值。",
            household={"drop_value": "one", "drop_multi": "skip"},
        ),
        _item(
            "allow_multi",
            "多盒覆盖也写",
            "仍抄用户点户数。同一用户接到多个分纤盒时，每条合格皮线都写（各写一遍该用户户数）。同盒重复皮线仍不写。",
            household={"drop_value": "user_hh", "drop_multi": "write"},
        ),
    ),
    "fat": (
        _item(
            "current",
            "当前：皮线户数合计",
            "分纤盒户数 = 一端吸到该盒的皮线户数之和。先核用户点总户数和皮线字段总户数，对不上整批不写。",
            household={"fat_value": "sum_drop", "fat_check": "totals"},
        ),
        _item(
            "count_drops",
            "按皮线条数",
            "分纤盒写入所出皮线的条数，不加户数。仍先核用户点总户数和皮线字段总户数，对不上整批不写。",
            household={"fat_value": "count_drop", "fat_check": "totals"},
        ),
        _item(
            "no_total_check",
            "皮线合计（不核总户数）",
            "仍按所出皮线户数加总。用户点总户数和皮线字段对不上只报软错误，其余分纤盒照写。",
            household={"fat_value": "sum_drop", "fat_check": "none"},
        ),
    ),
    "line": (
        _item(
            "current",
            "当前：配线只写本盒",
            "主干不写户数。配线只写到达的那一个分纤盒。接头-盒1-盒2 时，第一段配线只写盒1。",
            household={"cable_accumulate": False, "write_trunk": False},
        ),
        _item(
            "legacy_hh",
            "下游累加（主干也写）",
            "按下游分纤盒户数累加，主干也写。组网不变。命名不受此项影响。",
            household={"cable_accumulate": True, "write_trunk": True},
        ),
        _item(
            "dist_sum",
            "配线下游累加（主干不写）",
            "配线按下游分纤盒户数累加。主干仍不写。组网不变。命名不受此项影响。",
            household={"cable_accumulate": True, "write_trunk": False},
        ),
    ),
    "splice_code": (
        _item(
            "current",
            "当前：分叉另开第五段",
            tr('第四段：光交出线按第一段主干短的号小，一样长再比角度。第一个接头 01-01。没分叉第五段一直 01，第六段按走过的顺序。分叉时户数多的接着当前第五段，少的新开第五段，第六段接最大号后面。'),
            numbering=dict(CURRENT_NUMBERING, splice_link="branch_hh", odf_sort="first_trunk_length"),
        ),
        _item(
            "linear",
            "一条链：第五段固定 01",
            "第四段与当前相同。整条 ODF 上所有接头第五段都是 01，第六段按主干走到的顺序 01、02、03（分叉也接着编，不新开第五段）。",
            numbering=dict(CURRENT_NUMBERING, splice_link="linear", odf_sort="first_trunk_length"),
        ),
        _item(
            "new_link",
            "每个接头一个第五段",
            "第四段与当前相同。每走到一个接头就新开第五段（01、02、03…），第六段固定 01。分叉仍按户数、到下一接头长度决定先后。",
            numbering=dict(CURRENT_NUMBERING, splice_link="new_link_each", odf_sort="first_trunk_length"),
        ),
        _item(
            "odf_angle",
            "ODF 先按出线角度",
            "后两段与「当前：分叉另开第五段」相同。第四段先比出线角度（参数里的方向/起始角），角度相同再比第一段主干长短。",
            numbering=dict(CURRENT_NUMBERING, splice_link="branch_hh", odf_sort="exit_angle"),
        ),
    ),
    "fat_code": (
        _item(
            "current",
            "当前：接在接头第五段后面",
            tr('同一 ODF 的配线放在一起排。第五段从该 ODF 接头第五段最大值 +1 起，户数多的号小，相同则到首盒线长更长的号小。每条链第六段从 01 起，离接头近的是 01。不跟接头共用第五段。'),
            numbering=dict(CURRENT_NUMBERING, fat_link_start="after_max_splice_link", fat_box="restart_01_per_chain", rank_scope="odf"),
        ),
        _item(
            "share_5th",
            "跟接头共用第五段",
            "分纤盒第五段 = 所接接头 CODE 的第五段。该接头下的配线按户数、到首盒线长排，第六段从 01 起连续编（多条配线接着编，不每条链都从 01 起）。",
            numbering=dict(CURRENT_NUMBERING, fat_link_start="splice_n4", fat_box="continue_splice", rank_scope="splice", share_5th=True),
        ),
        _item(
            "per_splice",
            "每个接头从 01 起",
            "每个接头自己的配线单独排，第五段从 01 起，不看同 ODF 其它接头用到几。每条链第六段从 01 起。",
            numbering=dict(CURRENT_NUMBERING, fat_link_start="restart_01", fat_box="restart_01_per_chain", rank_scope="splice"),
        ),
        _item(
            "continue_6th",
            "第六段整条 ODF 连续",
            "第五段仍从该 ODF 接头第五段最大值 +1 起、按户数排。第六段不按链归零，整条 ODF 从 01 一直加下去。",
            numbering=dict(CURRENT_NUMBERING, fat_link_start="after_max_splice_link", fat_box="continue_odf", rank_scope="odf"),
        ),
    ),
    "cable_code": (
        _item(
            "current",
            "当前：抄到达对象并换前缀",
            "顺着光交往外走。主干抄到达接头的 CODE，配线抄到达分纤盒的 CODE，只换光缆前缀和主窗口城市/PM。到达对象城市/PM 不一致不写。",
            household={"cable_name": "dest"},
        ),
        _item(
            "from_upstream",
            "抄上游对象并换前缀",
            "主干：离开的那个接头的 CODE（光交出来的第一段仍抄到达接头）。配线：离开的那个接头/分纤盒的 CODE。仍换光缆前缀。光交本身没有 CODE。",
            household={"cable_name": "from_upstream"},
        ),
        _item(
            "keep_dest",
            "到达对象原样写入",
            "主干抄到达接头、配线抄到达分纤盒，CODE 一个字不改（不换光缆前缀）。仍检查城市/PM 是否与主窗口一致。",
            household={"cable_name": "dest_raw"},
        ),
        _item(
            "last3",
            "只取到达对象后三段",
            "不管到达对象的前缀和城市/PM，只抄第四/五/六段，再用光缆前缀和主窗口城市/PM 重写。不检查到达对象城市/PM。",
            household={"cable_name": "last3"},
        ),
    ),
}

_ALIASES = {
    "current": SCHEME_CURRENT,
    "default": SCHEME_CURRENT,
    "当前": SCHEME_CURRENT,
    "legacy_hh": SCHEME_LEGACY_HH,
    "accumulate": SCHEME_LEGACY_HH,
    "旧户数": SCHEME_LEGACY_HH,
}


def _catalog(action):
    return ACTION_SCHEMES.get(action) or ACTION_SCHEMES["line"]


def _by_id(action):
    return {item["id"]: item for item in _catalog(action)}


def default_action_schemes():
    return {key: "current" for key in ACTION_KEYS}


def _normalize_id(action, scheme_id):
    text = str(scheme_id or "").strip()
    if text in _by_id(action):
        return text
    if text in _ALIASES:
        alias = _ALIASES[text]
        if alias in _by_id(action):
            return alias
        if action == "line" and alias == SCHEME_LEGACY_HH:
            return SCHEME_LEGACY_HH
    return "current"


def migrate_action_schemes(raw=None, scheme_id=None, accumulate=None):
    """旧配置只有一个 scheme / 累加勾选，拆到六个功能。未知 id 回落到当前。"""
    out = default_action_schemes()
    if accumulate is True or (
        isinstance(accumulate, str) and accumulate.strip().lower() in ("1", "true", "yes", "on")
    ):
        out["line"] = SCHEME_LEGACY_HH
    legacy = _ALIASES.get(str(scheme_id or "").strip(), str(scheme_id or "").strip())
    if legacy == SCHEME_LEGACY_HH:
        out["line"] = SCHEME_LEGACY_HH
    if isinstance(raw, dict):
        for key in ACTION_KEYS:
            if key in raw:
                out[key] = _normalize_id(key, raw.get(key))
    return out


def resolve_action_scheme(action, scheme_id=None, accumulate=None):
    action = action if action in ACTION_SCHEMES else "line"
    sid = _normalize_id(action, scheme_id)
    if action == "line" and sid == "current" and accumulate is True:
        sid = SCHEME_LEGACY_HH
    spec = dict(_by_id(action)[sid])
    spec["action"] = action
    spec["topology"] = CURRENT_TOPOLOGY
    return spec


def resolve_scheme_id(scheme_id=None, accumulate=None, action="line"):
    if isinstance(scheme_id, dict):
        if scheme_id.get("action"):
            action = scheme_id.get("action")
        scheme_id = scheme_id.get("id")
    return resolve_action_scheme(action, scheme_id, accumulate)["id"]


def resolve_scheme(scheme=None, scheme_id=None, accumulate=None, action=None):
    if isinstance(scheme, dict) and scheme.get("id") and scheme.get("numbering") is not None:
        spec = dict(scheme)
        spec.setdefault("topology", CURRENT_TOPOLOGY)
        spec.setdefault("household", {})
        spec.setdefault("action", action or scheme.get("action") or "line")
        return spec
    if isinstance(scheme, dict) and scheme.get("id"):
        action = action or scheme.get("action") or "line"
        scheme_id = scheme.get("id")
    elif scheme is not None and not isinstance(scheme, dict):
        scheme_id = scheme
    if action is None:
        text = str(scheme_id or "").strip()
        action = "line" if text in (SCHEME_LEGACY_HH, "accumulate", "旧户数") else "line"
    return resolve_action_scheme(action, scheme_id, accumulate)


def scheme_label(scheme=None, scheme_id=None, accumulate=None, action=None):
    return resolve_scheme(scheme, scheme_id, accumulate, action)["label"]


def scheme_tip(scheme=None, scheme_id=None, accumulate=None, action=None):
    return resolve_scheme(scheme, scheme_id, accumulate, action)["tip"]


def cable_accumulate(scheme=None, scheme_id=None, accumulate=None, action="line"):
    spec = resolve_scheme(scheme, scheme_id, accumulate, action="line")
    if accumulate is True and spec["id"] == "current" and scheme_id is None and scheme is None:
        return True
    return bool(spec.get("household", {}).get("cable_accumulate"))


def write_trunk_hh(scheme=None, scheme_id=None, accumulate=None):
    spec = resolve_scheme(scheme, scheme_id, accumulate, action="line")
    hh = spec.get("household") or {}
    if "write_trunk" in hh:
        return bool(hh["write_trunk"])
    return bool(hh.get("cable_accumulate"))


def topology_of(scheme=None, scheme_id=None, accumulate=None):
    return CURRENT_TOPOLOGY


def numbering_of(scheme=None, scheme_id=None, accumulate=None, action=None):
    return resolve_scheme(scheme, scheme_id, accumulate, action).get("numbering") or dict(CURRENT_NUMBERING)


def host_action_schemes(host):
    if host is None:
        return default_action_schemes()
    raw = getattr(host, "action_schemes", None)
    return migrate_action_schemes(
        raw,
        getattr(host, "scheme_id", None),
        getattr(host, "accumulate", None),
    )


def host_scheme(host, accumulate=None, action="line"):
    ids = host_action_schemes(host)
    acc = accumulate if accumulate is not None else getattr(host, "accumulate", None)
    return resolve_action_scheme(action, ids.get(action), acc)


def result_meta(scheme=None, scheme_id=None, accumulate=None, action=None):
    spec = resolve_scheme(scheme, scheme_id, accumulate, action)
    return {
        "scheme": spec["id"],
        "scheme_label": spec["label"],
        "scheme_action": spec.get("action") or action or "",
        "accumulate": bool(spec.get("household", {}).get("cable_accumulate")),
    }


def iter_scheme_choices(action="line"):
    for item in _catalog(action):
        yield item["id"], item["label"], item["tip"]


def iter_action_scheme_rows():
    for key in ACTION_KEYS:
        for sid, label, tip in iter_scheme_choices(key):
            yield key, sid, label, tip


def household_of(scheme=None, scheme_id=None, accumulate=None, action=None):
    return resolve_scheme(scheme, scheme_id, accumulate, action).get("household") or {}


def format_action_scheme_lines(raw=None, scheme_id=None, accumulate=None):
    ids = migrate_action_schemes(raw, scheme_id, accumulate)
    lines = []
    for key in ACTION_KEYS:
        spec = resolve_action_scheme(key, ids.get(key))
        lines.append("{}：{}".format(ACTION_TITLES[key], spec["label"]))
    return lines
