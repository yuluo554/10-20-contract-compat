# -*- coding: utf-8 -*-
"""破例规则库：加载 ``rules/rule-table.json``（数据）并求值。

**规则表是数据不是代码**：命中条件、severity 默认值、修复动作都在表里，
本模块只做"加载 + 结构校验 + 按表求值"。这样"每条规则三格式各有用例"可被机械核对，
且不会出现第二套口径散落在 if 里。

求值分三步，每一步都只用已算好的事实（不做第二遍比较）：

  1. ``policy.diff`` 的差异项按 ``kind``（少数按 ``detail``）归到 R1–R7；
  2. severity 三值：先问"当前 policy 接不接受这个方向"（``policy.allows``），
     接受 → 表里的 ``severity_when_allowed``；不接受 → 规则默认值，``severity_by_detail``
     可按事实细节改写（如 Avro union 加类型 = ``union_widened`` → ``non-breaking``）；
  3. 命中行之外，为规则表里 ``applies=false`` 的格式槽位**补 N/A 行**（带理由）——
     `N/A` 是结论不是缺格，省略就等于宣称"这个格式没这问题"。

``R5`` 另有一条**文件级**求值面：字段号在旧 schema 的某个 message 上退休后，
被新 schema 的**另一个 message** 用不同字段名复用 → 命中（buf 不查这一格）。
数据来自 IR 的 ``meta["messages"]``（``parsers/proto.py`` 已收全量）。

本模块**不渲染**（分层约束：判定层不 import ``report``）。
"""

from __future__ import absolute_import

import json
import os

from .errors import UsageError
from .ir import FORMATS
from .policy import allows

__all__ = [
    "SEVERITIES",
    "EXPECTED_RULE_IDS",
    "KIND_RULES",
    "default_rule_path",
    "load_rule_table",
    "validate_rule_table",
    "rule_ids",
    "evaluate",
]

SEVERITIES = ("breaking", "runtime-dependent", "non-breaking")

EXPECTED_RULE_IDS = ("R1", "R2", "R3", "R4", "R5", "R6", "R7")

#: 事实（``policy.diff`` 的 ``kind``）→ 规则。**一个事实只归一条规则**。
#: ``field_added`` 不在表里：只有"必填且无默认"（``direction == BACKWARD_OK``）才算 R3 的证据，
#: 新增可选字段不是破例（反例 ``add-optional-property`` 正是靠这一条不误报）。
KIND_RULES = {
    "field_removed": "R1",
    "type_changed": "R2",
    "cardinality_changed": "R3",
    "enum_narrowed": "R4",
    "enum_widened": "R4",
    "enum_renumbered": "R4",
    "enum_changed": "R4",
    "field_number_reused": "R5",
    "reserved_conflict": "R5",
    "oneof_moved": "R6",
    "default_changed": "R7",
}

#: 数据目录相对仓库根的约定位置；**不写绝对路径**（包安装后也能靠这一层推导）。
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def default_rule_path():
    """规则表路径：优先仓库内 ``rules/``（唯一可编辑副本）；安装后回落到包内镜像。

    环境变量 ``CONTRACTCOMPAT_RULES`` 可覆盖（测试与"改规则再跑"用），但**报告里不写这个路径**。
    顺序固定：env → 仓库根 `rules/` → 包内 `data/`（wheel 安装后唯一存在的那份）。
    """
    override = os.environ.get("CONTRACTCOMPAT_RULES")
    if override:
        return override
    repo_copy = os.path.join(_REPO_ROOT, "rules", "rule-table.json")
    if os.path.isfile(repo_copy):
        return repo_copy
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "rule-table.json")


def load_rule_table(path=None):
    path = path or default_rule_path()
    if not os.path.isfile(path):
        raise UsageError("规则表不存在: %s" % path)
    with open(path, "r", encoding="utf-8-sig") as handle:
        try:
            table = json.load(handle)
        except ValueError as error:
            raise UsageError("规则表不是合法 JSON: %s（%s）" % (path, error))
    validate_rule_table(table)
    return table


def validate_rule_table(table):
    """结构校验：7 条规则、每条 3 个格式槽位、severity 三值合法。

    这是"覆盖矩阵可机械核对"的前提——缺一条规则时这里先红，而不是等某条用例悄悄不过。
    """
    if not isinstance(table, dict) or not isinstance(table.get("rules"), list):
        raise UsageError("规则表结构非法：缺 rules 数组")
    if table.get("severity_when_allowed", "non-breaking") not in SEVERITIES:
        raise UsageError("severity_when_allowed 非法: %r" % (table.get("severity_when_allowed"),))
    seen = []
    for rule in table["rules"]:
        rule_id = rule.get("rule_id")
        seen.append(rule_id)
        if rule.get("default_severity") not in SEVERITIES:
            raise UsageError("%s 的 default_severity 非法: %r" % (rule_id, rule.get("default_severity")))
        for detail, severity in (rule.get("severity_by_detail") or {}).items():
            if severity not in SEVERITIES:
                raise UsageError("%s 的 severity_by_detail[%s] 非法: %r" % (rule_id, detail, severity))
        formats = rule.get("formats") or {}
        for fmt in FORMATS:
            slot = formats.get(fmt)
            if not isinstance(slot, dict):
                raise UsageError("%s 缺 %s 槽位" % (rule_id, fmt))
            if slot.get("applies") and not slot.get("evidence"):
                raise UsageError("%s/%s 标 applies=true 但缺 evidence" % (rule_id, fmt))
            if not slot.get("applies") and not slot.get("reason"):
                raise UsageError("%s/%s 标 applies=false 但缺 reason（N/A 必须给理由）" % (rule_id, fmt))
            for key in ("evidence_by_kind", "evidence_by_detail"):
                for hook, evidence in (slot.get(key) or {}).items():
                    if not evidence:
                        raise UsageError("%s/%s 的 %s[%s] 为空" % (rule_id, fmt, key, hook))
    if tuple(seen) != EXPECTED_RULE_IDS:
        raise UsageError("规则集合必须是 %s，实际 %s" % (list(EXPECTED_RULE_IDS), seen))
    _validate_runtime_templates(table)
    return table


def _may_be_runtime_dependent(rule, table):
    """这条规则是否**可能**产出 runtime-dependent（含"被 policy 拒绝时"的默认值）。"""
    if rule.get("default_severity") == "runtime-dependent":
        return True
    if table.get("severity_when_allowed") == "runtime-dependent":
        return True
    return "runtime-dependent" in (rule.get("severity_by_detail") or {}).values()


def _validate_runtime_templates(table):
    """红线③：凡是可能产出 runtime-dependent 的规则，两段说明模板缺一即违约。

    这条校验放在**数据侧**（不是等某条用例跑出来才发现）：模板缺失时报告会输出一个
    没有解释的 runtime-dependent 条目，那正是"把三值压平"的另一种形态。
    """
    templates = table.get("runtime_dependent_templates") or {}
    for rule in table["rules"]:
        if not _may_be_runtime_dependent(rule, table):
            continue
        rule_id = rule["rule_id"]
        template = templates.get(rule_id)
        if not template:
            raise UsageError("%s 可能产出 runtime-dependent，但缺说明模板" % rule_id)
        if not template.get("why_static_breaking") or not template.get("what_would_trigger"):
            raise UsageError("%s 的 runtime-dependent 模板缺 why_static_breaking / what_would_trigger" % rule_id)


def rule_ids(table):
    return tuple(rule["rule_id"] for rule in table["rules"])


# ── 求值 ──────────────────────────────────────────────────────────────────


def evaluate(differences, table=None, policy="backward", history=()):
    """差异项 → 规则命中（``list[dict]``，键面 = ``report.FINDING_KEYS``）。

    参数口径：

      * ``differences``：``policy.diff`` 的返回（``DiffResult`` 更好——它带着两侧 IR，
        跨 message 的 R5 求值要用；普通 list 也能求值，只是跳过文件级那一格）；
      * ``policy``：severity 是**相对当前 policy** 的判定（``data/README.md`` §4.4）：
        被该 policy 接受的方向不标破；``none`` 不判定 → 一律 ``non-breaking``；
      * ``history``：``[(label, differences)]``，``*-transitive`` 档把历史版本也算进来——
        否则"历史版本导致的 breaking"会在报告里没有对应条目（verdict=breaking 而 findings 空）。

    命中顺序固定 ``(rule_id, stable_path)``，同一命中的 N/A 行紧跟其后。

    两条**不随命中数变化**的结论：

      * ``policy="none"`` 不判定 → 所有命中 ``non-breaking``（差异照常列出，退出码另由
        ``--policy none`` 保证 0）；
      * 输入格式下 ``applies=false`` 的规则槽位**各出一行 N/A**（带理由），与该格式有没有
        命中无关——"这个格式没有这个概念"是结论，不是"没命中"。
    """
    table = table or load_rule_table()
    by_id = dict((rule["rule_id"], rule) for rule in table["rules"])
    groups = [("", differences)]
    for entry in history or ():
        if isinstance(entry, tuple) and len(entry) == 2:
            groups.append((entry[0] or "", entry[1]))
        else:
            groups.append(("", entry))

    findings = []
    for label, group in groups:
        for item in _hits(group):
            rule_id = _rule_of(item)
            if rule_id is None:
                continue
            findings.append(_finding(item, by_id[rule_id], table, policy, label))
    findings.extend(_not_applicable_rows(table, _input_format(differences)))
    findings.sort(key=_sort_key)
    return findings


def _input_format(differences):
    """输入格式：优先取 ``DiffResult.old.format``（普通 list 没有这个锚点时看首项）。"""
    old_ir = getattr(differences, "old", None)
    fmt = getattr(old_ir, "format", None)
    if fmt in FORMATS:
        return fmt
    for item in differences:
        if item.get("format") in FORMATS:
            return item["format"]
    return None


def _hits(differences):
    """差异项 + 文件级 R5 命中（跨 message 字段号复用）。"""
    items = list(differences)
    return items + _cross_message_hits(differences)


def _rule_of(item):
    kind = item.get("kind")
    if kind == "field_added":
        # 只有"必填且无默认"才是 R3：可选新增不是破例（反例 add-optional-property）
        return "R3" if item.get("direction") == "BACKWARD_OK" else None
    return KIND_RULES.get(kind)


def _severity(item, rule, table, policy):
    """三值 severity：policy 接受的方向不标破；否则按规则表（含 detail 改写）。"""
    if allows(policy, item.get("direction")):
        return table.get("severity_when_allowed", "non-breaking")
    detail = item.get("detail")
    by_detail = rule.get("severity_by_detail") or {}
    if detail in by_detail:
        return by_detail[detail]
    return rule["default_severity"]


def _format_evidence(item, slot):
    """证据形态取自规则表；``enum_widened`` / ``wire_compatible`` 一类细节有专门说法。"""
    kind = item.get("kind")
    if kind in (slot.get("evidence_by_kind") or {}):
        return slot["evidence_by_kind"][kind]
    detail = item.get("detail")
    if detail in (slot.get("evidence_by_detail") or {}):
        return slot["evidence_by_detail"][detail]
    return slot["evidence"]


def _repair_hint(hint, item):
    """修复动作模板只填**已知**的值；填不进去的占位符原样保留（不编一个假值）。"""
    if not hint:
        return hint
    values = {
        "number": item.get("number"),
        "old_name": item.get("field"),
        "new_name": item.get("new") if item.get("kind") == "field_number_reused" else item.get("field"),
    }
    for key, value in values.items():
        if value is not None:
            hint = hint.replace("{%s}" % key, str(value))
    return hint


def _finding(item, rule, table, policy, history_label):
    severity = _severity(item, rule, table, policy)
    slot = rule["formats"][item.get("format")]
    evidence = {
        "kind": item.get("kind"),
        "detail": item.get("detail"),
        "format": item.get("format"),
        "old": item.get("old"),
        "new": item.get("new"),
        "reason": item.get("reason"),
    }
    if history_label:
        evidence["history"] = history_label
    row = {
        "rule_id": rule["rule_id"],
        "rule_name": rule["name"],
        "stable_path": item.get("stable_path") or "",
        "severity": severity,
        "format_evidence": _format_evidence(item, slot),
        "direction": item.get("direction"),
        "repair_action": rule["repair_action"],
        "repair_hint": _repair_hint(slot.get("repair_hint"), item),
        "evidence": evidence,
    }
    if severity == "runtime-dependent":
        template = (table.get("runtime_dependent_templates") or {}).get(rule["rule_id"]) or {}
        if not template.get("why_static_breaking") or not template.get("what_would_trigger"):
            raise UsageError(
                "%s 产出 runtime-dependent 但规则表缺两段说明（不得输出没有解释的三值条目）"
                % rule["rule_id"]
            )
        row["why_static_breaking"] = template["why_static_breaking"]
        row["what_would_trigger"] = template["what_would_trigger"]
    else:
        row["why_static_breaking"] = None
        row["what_would_trigger"] = None
    return row


def _not_applicable_rows(table, ir_format):
    """``applies=false`` 的格式槽位：显式 ``N/A`` 行 + 理由（**不得省略**）。

    与命中无关：R5/R6 在 Avro / JSON Schema 下**永远**是 N/A——那是"该格式没有字段号 /
    oneof 这个概念"，不是"这次没命中"。省略就等于宣称"这个格式没这问题"。
    """
    rows = []
    if ir_format is None:
        return rows
    for rule in table["rules"]:
        slot = rule["formats"].get(ir_format)
        if not slot or slot.get("applies"):
            continue
        rows.append(
            {
                "rule_id": rule["rule_id"],
                "rule_name": rule["name"],
                "stable_path": None,
                "severity": None,
                "format_evidence": "N/A",
                "direction": None,
                "repair_action": None,
                "repair_hint": slot.get("repair_hint"),
                "evidence": {
                    "kind": None,
                    "detail": None,
                    "format": ir_format,
                    "reason": slot["reason"],
                    "note": "N/A（该格式无此概念，规则不适用）",
                },
                "why_static_breaking": None,
                "what_would_trigger": None,
            }
        )
    return rows


def _sort_key(row):
    # 命中行排在它自己的 N/A 行前面（N/A 是同一命中的"另一格式"结论）
    return (
        row.get("rule_id") or "",
        row.get("stable_path") or "",
        1 if row.get("format_evidence") == "N/A" else 0,
    )


# ── R5 的文件级面：跨 message 字段号复用 ───────────────────────────────────


def _message_index(ir):
    """``{message: {number: name}}``；没有 ``meta["messages"]``（非 proto）时返回空。"""
    index = {}
    for message in (getattr(ir, "meta", None) or {}).get("messages") or ():
        fields = index.setdefault(message.get("name") or "", {})
        for field in message.get("fields") or ():
            number = field.get("number")
            if number is not None:
                fields[int(number)] = field.get("name")
    return index


def _cross_message_hits(differences):
    """旧 message 上退休的字段号被**另一个 message** 用不同名字接手 → R5 命中。

    只看事实：旧侧某 message 的号在新侧**不再属于该 message**（同 message 换主人由
    ``diff`` 层报，这里不重复），且新侧有另一个 message 持有同号、字段名不同。
    两个 message 都用 1 号是 Protobuf 的常态，所以"名字相同"不算复用——
    只有"号留下来了、含义换了"才算。
    """
    old_ir = getattr(differences, "old", None)
    new_ir = getattr(differences, "new", None)
    if old_ir is None or new_ir is None:
        return []
    if getattr(old_ir, "format", None) != "proto" or getattr(new_ir, "format", None) != "proto":
        return []
    old_index = _message_index(old_ir)
    new_index = _message_index(new_ir)
    if not old_index or not new_index:
        return []

    hits = []
    for old_message in sorted(old_index):
        for number in sorted(old_index[old_message]):
            if number in new_index.get(old_message, {}):
                continue  # 同一 message 仍持有该号：交给 diff 层
            old_name = old_index[old_message][number]
            for new_message in sorted(new_index):
                if new_message == old_message:
                    continue
                new_name = new_index[new_message].get(number)
                if new_name is None or new_name == old_name:
                    continue
                hits.append(
                    {
                        "kind": "field_number_reused",
                        "format": "proto",
                        "field": new_name,
                        "number": number,
                        "stable_path": "%s.%d" % (old_message, number),
                        "direction": "NONE_OK",
                        "old": old_name,
                        "new": new_name,
                        "detail": "cross_message_reuse",
                        "reason": "字段号 %s 从 message %s 退休后，被 message %s 的 %s 复用"
                        "（跨 message；旧号未 reserved）"
                        % (number, old_message, new_message, new_name),
                    }
                )
                break
    return hits
