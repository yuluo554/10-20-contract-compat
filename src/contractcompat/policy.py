# -*- coding: utf-8 -*-
"""方向性判定核：七档 policy + 差异项方向判定。

口径（七档语义、buf 四档映射）唯一定义在 ``data/README.md`` §4.1 / §4.2；
本模块只实现它，并在 ``MAPPING_NOTES`` 里保留"只表达最接近、不宣称等价"的声明。

两层严格分开：

  * ``diff`` 只产出**事实**：新增/删除/类型变/基数变/默认值变/enum 收窄/oneof 移动/字段号复用，
    每项带 ``direction ∈ DIRECTIONS``。换 ``--policy`` 不改变 direction。
  * ``judge`` 把 direction × 七档映射成 ``verdict ∈ VERDICTS``；``none`` 恒 compatible；
    ``*-transitive`` 对每个历史版本重复 ``diff + judge``。

``diff`` 返回 :class:`DiffResult`——一个 list 子类，额外带着本次比较的两份 IR。
这样 ``judge(differences, policy, history)`` 才能在 transitive 档对历史版本重算 diff，
而调用方拿到的仍然是"差异项列表"（M4 的规则求值可直接遍历）。
"""

from __future__ import absolute_import

from .errors import UsageError

__all__ = [
    "POLICIES",
    "TRANSITIVE",
    "DIRECTIONS",
    "VERDICTS",
    "MAPPING_NOTES",
    "DiffResult",
    "resolve_policy",
    "mapping_table",
    "diff",
    "judge",
]

POLICIES = (
    "backward",
    "backward-transitive",
    "forward",
    "forward-transitive",
    "full",
    "full-transitive",
    "none",
)

TRANSITIVE = tuple(name for name in POLICIES if name.endswith("-transitive"))

#: 差异项的方向是**事实**，policy 是**选择**：换 policy 不改变 direction。
DIRECTIONS = ("BACKWARD_OK", "FORWARD_OK", "BOTH_OK", "NONE_OK")

VERDICTS = ("compatible", "breaking")

#: buf 四档映射。必须逐行带"关系说明"，且整表必须含"只表达最接近、不宣称等价"
#: （`data/README.md` §4.2 的使用规则；`tests/test_policy.py` 逐行断言）。
MAPPING_NOTES = (
    "本表只表达最接近，不宣称等价：buf 的档位是'检查哪些规则'，"
    "本题的 policy 是'允许哪个方向'，两者维度不同，因而不等价。"
)

_MAPPING_ROWS = (
    {
        "policy": "backward",
        "buf_tier": "WIRE（JSON 视图取 WIRE_JSON）",
        "relation": "buf 的档 = 检查哪些规则；本题的 policy = 允许哪个方向。二者维度不同，不等价",
        "buf_note": "buf 只判 Protobuf 线上字节，不含 Avro / JSON Schema",
    },
    {
        "policy": "forward",
        "buf_tier": "无直接对应",
        "relation": "buf 不区分方向，只判'是否破坏'；本题显式区分方向",
        "buf_note": "因此本档没有可对齐的 buf 档位",
    },
    {
        "policy": "full",
        "buf_tier": "WIRE + WIRE_JSON 同时通过",
        "relation": "最接近的近似，不等价：buf 的'档'是检查范围，不是方向",
        "buf_note": "full 要求两个方向都成立，buf 没有方向概念",
    },
    {
        "policy": "none",
        "buf_tier": "—",
        "relation": "buf 无'只列差异不判定'档",
        "buf_note": "本档只输出差异与证据，verdict 恒 compatible",
    },
)


class DiffResult(list):
    """差异项列表 + 本次比较的两份 IR（transitive 判定的输入）。

    继承 ``list`` 是刻意的：调用方（规则求值、报告、golden）只把它当差异项序列用；
    ``old`` / ``new`` 只是判定核内部重算历史比较时的锚点，不参与序列化。
    """

    def __init__(self, items=(), old=None, new=None):
        list.__init__(self, items)
        self.old = old
        self.new = new

    def __repr__(self):
        return "DiffResult(%d items)" % len(self)


def resolve_policy(name, history=None):
    """校验 policy 与 ``--history`` 的组合；不合规抛 :class:`UsageError`（退出码 2）。

    ``*-transitive`` 缺 ``--history`` **必须拒绝**——降级为单版本会把"与历史不兼容"
    静默报成"兼容"，这正是本工具要消除的误判。
    """
    if name not in POLICIES:
        raise UsageError("未知 policy: %r（允许 %s）" % (name, ", ".join(POLICIES)))
    versions = list(history or ())
    if name in TRANSITIVE and not versions:
        raise UsageError("%s 需要 --history（至少一个历史版本文件）；不降级为单版本比较" % name)
    if name not in TRANSITIVE and versions:
        raise UsageError("%s 不接受 --history（只有 *-transitive 档使用历史版本）" % name)
    return name


def mapping_table():
    """返回 buf 四档映射表的行 + 总声明，供 ``--explain-mapping`` 渲染。"""
    return {"notes": MAPPING_NOTES, "rows": [dict(row) for row in _MAPPING_ROWS]}


# ── 差异项：只产出事实 ────────────────────────────────────────────────────


def _short(value):
    """把差异项里的旧/新值压成稳定的一行（报告与 golden 都要逐字节可复算）。"""
    if isinstance(value, dict):
        return "{" + ", ".join("%s: %r" % (key, value[key]) for key in sorted(value)) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_short(item) for item in value) + "]"
    return repr(value)


def _item(kind, ir_format, field, direction, reason, number=None, old=None, new=None, detail=None):
    if direction not in DIRECTIONS:
        raise AssertionError("direction 非法: %r" % (direction,))
    return {
        "kind": kind,
        "format": ir_format,
        "field": field.name if field is not None else None,
        "number": number,
        "stable_path": field.stable_path() if field is not None else "",
        "direction": direction,
        "old": old,
        "new": new,
        "detail": detail,
        "reason": reason,
    }


def _sort_key(item):
    number = item.get("number")
    return (
        0 if number is not None else 1,
        number if number is not None else 0,
        item.get("stable_path") or "",
        item.get("kind") or "",
    )


def diff(old_ir, new_ir):
    """产出差异项（事实），每项带 ``direction``；不读 policy、不写报告。"""
    if old_ir.format != new_ir.format:
        raise UsageError(
            "old/new 格式不同（%s vs %s）；跨格式比较没有判定语义" % (old_ir.format, new_ir.format)
        )
    if old_ir.format == "proto":
        items = _diff_proto(old_ir, new_ir)
    elif old_ir.format == "avro":
        items = _diff_avro(old_ir, new_ir)
    else:
        items = _diff_jsonschema(old_ir, new_ir)
    items.sort(key=_sort_key)
    return DiffResult(items, old=old_ir, new=new_ir)


def _added_direction(field):
    """新增字段：required 且无默认 → 旧数据读不了；其余双向可读。"""
    if field.cardinality == "required" and not field.default_present:
        return "BACKWARD_OK"
    return "BOTH_OK"


def _diff_proto(old_ir, new_ir):
    out = []
    old_by_number = dict((field.number, field) for field in old_ir.fields if field.number is not None)
    new_by_number = dict((field.number, field) for field in new_ir.fields if field.number is not None)

    for old_field in old_ir.fields:
        if old_field.number is None:
            continue
        new_field = new_by_number.get(old_field.number)
        if new_field is None:
            if old_field.number in new_ir.reserved_numbers or old_field.name in new_ir.reserved_names:
                continue  # 号已保留：删除是安全动作，不是 R1
            out.append(
                _item(
                    "field_removed",
                    "proto",
                    old_field,
                    "FORWARD_OK",
                    "字段号 %s 消失且未 reserved；老消费者读不到新数据里的该字段" % old_field.number,
                    number=old_field.number,
                    old=old_field.type,
                )
            )
            continue
        if new_field.number in new_ir.reserved_numbers:
            out.append(
                _item(
                    "reserved_conflict",
                    "proto",
                    new_field,
                    "NONE_OK",
                    "字段号 %s 同时出现在 fields 与 reserved 中（schema 自相矛盾）" % new_field.number,
                    number=new_field.number,
                    new=new_field.name,
                )
            )
            continue
        if new_field.name != old_field.name:
            out.append(
                _item(
                    "field_number_reused",
                    "proto",
                    new_field,
                    "NONE_OK",
                    "字段号 %s 换了主人（%s → %s）；旧数据会被按新含义解释"
                    % (new_field.number, old_field.name, new_field.name),
                    number=new_field.number,
                    old=old_field.name,
                    new=new_field.name,
                )
            )
            continue
        out.extend(_diff_field(old_field, new_field, "proto"))

    for new_field in new_ir.fields:
        if new_field.number is None or new_field.number in old_by_number:
            continue
        if new_field.number in new_ir.reserved_numbers:
            out.append(
                _item(
                    "reserved_conflict",
                    "proto",
                    new_field,
                    "NONE_OK",
                    "新字段号 %s 落进同一 schema 的 reserved 区间（schema 自相矛盾）"
                    % new_field.number,
                    number=new_field.number,
                    new=new_field.name,
                )
            )
            continue
        out.append(
            _item(
                "field_added",
                "proto",
                new_field,
                _added_direction(new_field),
                "新增字段 %s（%s）；%s"
                % (
                    new_field.name,
                    new_field.cardinality,
                    "无默认值，旧数据无法满足新读者" if _added_direction(new_field) == "BACKWARD_OK" else "双向可读",
                ),
                number=new_field.number,
                new=new_field.type,
            )
        )
    return out


def _diff_avro(old_ir, new_ir):
    out = []
    new_by_name = dict((field.name, field) for field in new_ir.fields)
    alias_to_new = {}
    for field in new_ir.fields:
        for alias in field.aliases:
            alias_to_new.setdefault(alias, field)

    matched = set()
    for old_field in old_ir.fields:
        new_field = new_by_name.get(old_field.name) or alias_to_new.get(old_field.name)
        if new_field is None:
            if old_field.name in new_ir.reserved_names:
                continue
            out.append(
                _item(
                    "field_removed",
                    "avro",
                    old_field,
                    "FORWARD_OK",
                    "字段 %s 从新 schema 消失且无 alias 承接；旧数据进入新消费者时可被忽略，反向缺字段"
                    % old_field.name,
                    old=old_field.type,
                )
            )
            continue
        matched.add(new_field.name)
        out.extend(_diff_field(old_field, new_field, "avro"))

    for new_field in new_ir.fields:
        if new_field.name in matched:
            continue
        out.append(
            _item(
                "field_added",
                "avro",
                new_field,
                _added_direction(new_field),
                "新增字段 %s（%s）；%s"
                % (
                    new_field.name,
                    new_field.cardinality,
                    "无默认值，旧数据无法满足新读者" if _added_direction(new_field) == "BACKWARD_OK" else "双向可读",
                ),
                new=new_field.type,
            )
        )
    return out


def _diff_jsonschema(old_ir, new_ir):
    out = []
    old_by_name = dict((field.name, field) for field in old_ir.fields)
    new_by_name = dict((field.name, field) for field in new_ir.fields)

    for old_field in old_ir.fields:
        new_field = new_by_name.get(old_field.name)
        if new_field is None:
            if old_field.name in new_ir.reserved_names:
                continue
            out.append(
                _item(
                    "field_removed",
                    "jsonschema",
                    old_field,
                    "FORWARD_OK",
                    "属性 %s 从 properties 消失；旧数据多出的属性对新读者可忽略，新数据缺属性对老读者不可读"
                    % old_field.name,
                    old=old_field.type,
                )
            )
            continue
        out.extend(_diff_field(old_field, new_field, "jsonschema"))

    for new_field in new_ir.fields:
        if new_field.name in old_by_name:
            continue
        out.append(
            _item(
                "field_added",
                "jsonschema",
                new_field,
                _added_direction(new_field),
                "新增属性 %s（%s）；%s"
                % (
                    new_field.name,
                    new_field.cardinality,
                    "在 required 中且无默认值，旧数据无法满足新读者"
                    if _added_direction(new_field) == "BACKWARD_OK"
                    else "不在 required 中，双向可读",
                ),
                new=new_field.type,
            )
        )
    return out


def _diff_field(old_field, new_field, ir_format):
    """同一字段上的事实：类型 / 基数 / 默认值 / enum / oneof。"""
    out = []
    oneof_handled = False

    if old_field.oneof_membership != new_field.oneof_membership:
        direction = _oneof_direction(old_field, new_field)
        out.append(
            _item(
                "oneof_moved",
                ir_format,
                new_field,
                direction,
                "oneof 归属变化（%s → %s）"
                % (
                    old_field.oneof_membership or "无",
                    new_field.oneof_membership or "无",
                ),
                old=old_field.oneof_membership,
                new=new_field.oneof_membership,
            )
        )
        oneof_handled = True

    old_oneof = _is_oneof_type(old_field.type)
    new_oneof = _is_oneof_type(new_field.type)
    if old_oneof and new_oneof:
        # oneOf/anyOf 的分支替换按 R6（分支移动）记，不再重复记一条类型变。
        if _branch_set(old_field.type) != _branch_set(new_field.type) and not oneof_handled:
            direction = _set_direction(_branch_set(old_field.type), _branch_set(new_field.type))
            out.append(
                _item(
                    "oneof_moved",
                    "jsonschema",
                    new_field,
                    direction,
                    "oneOf 分支集合变化（%s → %s）" % (old_field.type, new_field.type),
                    old=old_field.type,
                    new=new_field.type,
                )
            )
        oneof_handled = True

    if old_field.type != new_field.type and not (old_oneof and new_oneof):
        direction, detail = _type_direction(old_field.type, new_field.type, ir_format)
        out.append(
            _item(
                "type_changed",
                ir_format,
                new_field,
                direction,
                "字段类型变化（%s → %s）" % (old_field.type, new_field.type),
                old=old_field.type,
                new=new_field.type,
                detail=detail,
            )
        )

    if old_field.cardinality != new_field.cardinality:
        out.append(
            _item(
                "cardinality_changed",
                ir_format,
                new_field,
                _cardinality_direction(old_field.cardinality, new_field.cardinality),
                "字段基数变化（%s → %s）" % (old_field.cardinality, new_field.cardinality),
                old=old_field.cardinality,
                new=new_field.cardinality,
            )
        )

    if (old_field.default_present, old_field.default_value) != (
        new_field.default_present,
        new_field.default_value,
    ):
        out.append(
            _item(
                "default_changed",
                ir_format,
                new_field,
                "BOTH_OK",
                "默认值变化（%s → %s）；读写两侧都可解析，写侧语义变化需人工确认"
                % (
                    _default_text(old_field),
                    _default_text(new_field),
                ),
                old={"present": old_field.default_present, "value": old_field.default_value},
                new={"present": new_field.default_present, "value": new_field.default_value},
            )
        )

    enum_kind, enum_direction, enum_detail = _enum_direction(old_field, new_field)
    if enum_kind is not None:
        out.append(
            _item(
                enum_kind,
                ir_format,
                new_field,
                enum_direction,
                enum_detail,
                old=[value.name for value in old_field.enum_values],
                new=[value.name for value in new_field.enum_values],
            )
        )
    return out


def _default_text(field):
    if not field.default_present:
        return "无默认"
    return _short(field.default_value)


def _is_oneof_type(type_name):
    return isinstance(type_name, str) and (type_name.startswith("oneOf(") or type_name.startswith("anyOf("))


def _branch_set(type_name):
    if not _is_oneof_type(type_name):
        return frozenset()
    inside = type_name[type_name.index("(") + 1 : type_name.rindex(")")]
    return frozenset(part.strip() for part in inside.split(",") if part.strip())


def _set_direction(old_set, new_set):
    if old_set == new_set:
        return "BOTH_OK"
    if old_set < new_set:
        return "FORWARD_OK"  # 新 schema 接受更多：新读旧通，旧读新可能不通
    if new_set < old_set:
        return "BACKWARD_OK"
    return "NONE_OK"


def _oneof_direction(old_field, new_field):
    old_membership = old_field.oneof_membership
    new_membership = new_field.oneof_membership
    if old_membership is None and new_membership is not None:
        return "BACKWARD_OK"  # 字段进入 oneof：新数据互斥，旧数据可能同时带上多个
    if old_membership is not None and new_membership is None:
        return "BOTH_OK"  # 字段离开 oneof：线上字节不变，互斥语义变宽
    if _is_oneof_type(old_field.type) and _is_oneof_type(new_field.type):
        return _set_direction(_branch_set(old_field.type), _branch_set(new_field.type))
    return "BOTH_OK"  # oneof 改名：线上不携带组名


_PROTO_WIRE_GROUPS = {
    "int32": "varint",
    "int64": "varint",
    "uint32": "varint",
    "uint64": "varint",
    "bool": "varint",
    "sint32": "zigzag",
    "sint64": "zigzag",
    "fixed32": "fixed32",
    "sfixed32": "fixed32",
    "float": "fixed32",
    "fixed64": "fixed64",
    "sfixed64": "fixed64",
    "double": "fixed64",
    "string": "length",
    "bytes": "length",
}

_AVRO_PROMOTIONS = {
    "int": ("long", "float", "double"),
    "long": ("float", "double"),
    "float": ("double",),
    "string": ("bytes",),
}


def _type_direction(old_type, new_type, ir_format):
    """返回 ``(direction, detail)``；调用方只在类型确实不同时调用。"""
    if _is_union(old_type) and _is_union(new_type):
        old_set = _union_set(old_type)
        new_set = _union_set(new_type)
        direction = _set_direction(old_set, new_set)
        detail = {
            "FORWARD_OK": "union_widened",
            "BACKWARD_OK": "union_narrowed",
            "BOTH_OK": "union_reordered",
            "NONE_OK": "union_changed",
        }[direction]
        return direction, detail

    if ir_format == "proto":
        old_group = _PROTO_WIRE_GROUPS.get(old_type)
        new_group = _PROTO_WIRE_GROUPS.get(new_type)
        if old_group is not None and old_group == new_group:
            return "BOTH_OK", "wire_compatible"
        return "NONE_OK", "wire_incompatible"

    if ir_format == "avro":
        if new_type in _AVRO_PROMOTIONS.get(old_type, ()):
            return "FORWARD_OK", "promotion"
        if old_type in _AVRO_PROMOTIONS.get(new_type, ()):
            return "BACKWARD_OK", "promotion"
        return "NONE_OK", "incompatible"

    if ir_format == "jsonschema":
        if old_type == "integer" and new_type == "number":
            return "FORWARD_OK", "widened"
        if old_type == "number" and new_type == "integer":
            return "BACKWARD_OK", "narrowed"
        return "NONE_OK", "incompatible"

    return "NONE_OK", "unknown_format"


def _is_union(type_name):
    return isinstance(type_name, str) and type_name.startswith("union(")


def _union_set(type_name):
    inside = type_name[type_name.index("(") + 1 : type_name.rindex(")")]
    return frozenset(part.strip() for part in inside.split(",") if part.strip())


def _cardinality_direction(old_cardinality, new_cardinality):
    """只对"存在性/可空性"这一维判定；repeated 的装载形态变化按不兼容处理。"""
    if old_cardinality == "optional" and new_cardinality == "required":
        return "BACKWARD_OK"
    if old_cardinality == "required" and new_cardinality == "optional":
        return "FORWARD_OK"
    if old_cardinality == "nullable" and new_cardinality == "required":
        return "BACKWARD_OK"
    if old_cardinality == "required" and new_cardinality == "nullable":
        return "FORWARD_OK"
    if old_cardinality == "optional" and new_cardinality == "nullable":
        return "FORWARD_OK"
    if old_cardinality == "nullable" and new_cardinality == "optional":
        return "BACKWARD_OK"
    return "NONE_OK"


def _enum_direction(old_field, new_field):
    """返回 ``(kind, direction, reason)``；没有 enum 事实时 ``kind`` 为 None。"""
    old_values = old_field.enum_values
    new_values = new_field.enum_values
    if not old_values and not new_values:
        return None, None, None
    if not old_values or not new_values:
        return "enum_changed", "NONE_OK", "一侧有 enum 取值、另一侧没有；取值集合不可比"

    old_names = tuple(value.name for value in old_values)
    new_names = tuple(value.name for value in new_values)
    old_set = frozenset(old_names)
    new_set = frozenset(new_names)
    # 按名字比较编号映射：JSON Schema 的编号恒 None，纯顺序变化不算事实；
    # Avro / Protobuf 的顺序变化会改编号映射，那是真的 renumber。
    old_numbers = dict((value.name, value.number) for value in old_values)
    new_numbers = dict((value.name, value.number) for value in new_values)

    if old_set == new_set:
        if old_numbers != new_numbers:
            return "enum_renumbered", "NONE_OK", "enum 取值名相同但编号变化；旧数据的编号含义被改写"
        return None, None, None
    if new_set < old_set:
        removed = sorted(old_set - new_set)
        return "enum_narrowed", "BACKWARD_OK", "enum 取值集合收窄（删除 %s）；旧数据可能含被删取值" % (", ".join(removed) or "—")
    if old_set < new_set:
        added = sorted(new_set - old_set)
        return "enum_widened", "FORWARD_OK", "enum 取值集合扩大（新增 %s）" % (", ".join(added) or "—")
    return "enum_changed", "NONE_OK", "enum 取值集合既非收窄也非扩大（同时增删）"


# ── 七档聚合：direction × policy → verdict ─────────────────────────────────


def _policy_allows(policy_name, direction):
    if policy_name in ("backward", "backward-transitive"):
        return direction in ("BACKWARD_OK", "BOTH_OK")
    if policy_name in ("forward", "forward-transitive"):
        return direction in ("FORWARD_OK", "BOTH_OK")
    return direction == "BOTH_OK"  # full / full-transitive


def _history_differences(differences, history):
    """把历史版本转成差异项列表：接受 IR（重算 diff）或已算好的差异列表。"""
    groups = []
    new_ir = getattr(differences, "new", None)
    for entry in history:
        if isinstance(entry, (list, tuple)) and (not entry or isinstance(entry[0], dict)):
            groups.append(list(entry))
            continue
        if new_ir is None:
            raise UsageError("transitive 判定需要 diff 结果携带 new IR（请用 policy.diff 的返回值）")
        groups.append(list(diff(entry, new_ir)))
    return groups


def judge(differences, policy, history=()):
    """把差异项的方向 × 七档映射成 ``compatible | breaking``。

    ``history`` 只在 ``*-transitive`` 档生效：可传历史 ``ContractIR``（本函数逐版本重算
    ``diff``），也可传已算好的差异项列表。缺 ``--history`` 的拒绝由
    :func:`resolve_policy` 在 CLI 入口完成——这里不重复判一次。
    """
    if policy not in POLICIES:
        raise UsageError("未知 policy: %r（允许 %s）" % (policy, ", ".join(POLICIES)))
    if policy == "none":
        return "compatible"

    groups = [list(differences)]
    if policy in TRANSITIVE:
        groups.extend(_history_differences(differences, history or ()))

    for group in groups:
        for item in group:
            if not _policy_allows(policy, item.get("direction")):
                return "breaking"
    return "compatible"
