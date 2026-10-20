# -*- coding: utf-8 -*-
"""报告：规范 JSON（唯一机读形态）+ Markdown 渲染视图 + ``--verify``。

纪律：
  * **渲染层零判定**——本模块只读传进来的结论，不做任何比较；
  * 报告不写时间戳 / 绝对路径 / 主机名 / 用户名（会让同一输入跨机产生不同字节）；
  * Markdown 只是 JSON 的渲染视图，**不参与 digest**；
  * 序列化一律走 ``canonical.dumps``（全仓唯一 ``json.dumps`` 调用点）。
"""

from __future__ import absolute_import

import os

from . import __version__
from .canonical import DIGEST_KEY, digest, dumps, loads, verify_report
from .errors import UsageError

__all__ = [
    "REPORT_SCHEMA_VERSION",
    "FINDING_KEYS",
    "build",
    "to_json",
    "to_markdown",
    "render",
    "verify_file",
]

REPORT_SCHEMA_VERSION = 1

#: finding 的固定键集合。**不适用的字段保留键并写 null**：
#: 键集合稳定比"省略键"更重要（下游按固定列读取，多一个少一个都是破坏）。
FINDING_KEYS = (
    "rule_id",
    "rule_name",
    "stable_path",
    "severity",
    "format_evidence",
    "direction",
    "blast_radius",
    "repair_action",
    "repair_hint",
    "evidence",
    "why_static_breaking",
    "what_would_trigger",
)

SUMMARY_KEYS = (
    "findings_total",
    "breaking",
    "runtime_dependent",
    "non_breaking",
    "ir_unsupported",
)


def _empty_finding():
    return dict((key, None) for key in FINDING_KEYS)


def _as_plain(item):
    """接受 ``Unsupported`` 对象或已序列化的 dict，统一成报告里的三键对象。"""
    if hasattr(item, "to_json"):
        return item.to_json()
    return {
        "construct": item.get("construct"),
        "json_pointer": item.get("json_pointer"),
        "reason": item.get("reason"),
    }


def build(
    policy,
    old_name,
    new_name,
    findings=(),
    notes=(),
    ir_unsupported=(),
    verdict="compatible",
    mapping=None,
):
    """组装报告对象（未加 digest）。所有参数都是**已算好的结论**，本函数不做判定。"""
    normalized = []
    for item in findings:
        row = _empty_finding()
        row.update(dict((key, item.get(key)) for key in FINDING_KEYS if key in item))
        normalized.append(row)
    # 报告内排序是判据的一部分：同一输入两次运行必须字节一致
    normalized.sort(key=lambda row: (row.get("rule_id") or "", row.get("stable_path") or ""))
    counts = dict((key, 0) for key in SUMMARY_KEYS)
    for row in normalized:
        severity = row.get("severity")
        if severity == "breaking":
            counts["breaking"] += 1
        elif severity == "runtime-dependent":
            counts["runtime_dependent"] += 1
        elif severity == "non-breaking":
            counts["non_breaking"] += 1
    counts["findings_total"] = len(normalized)
    counts["ir_unsupported"] = len(ir_unsupported)

    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "tool": "contractcompat",
        "version": __version__,
        "policy": policy,
        "verdict": verdict,
        "inputs": {"old": old_name, "new": new_name},
        "ir_unsupported": [_as_plain(item) for item in ir_unsupported],
        "findings": normalized,
        "summary": counts,
        "notes": list(notes),
    }
    if mapping is not None:
        report["buf_mapping"] = mapping
    report[DIGEST_KEY] = digest(report)
    return report


def to_json(report):
    """规范 JSON 文本（含结尾换行）。"""
    return dumps(report)


def _cell(value):
    if value is None:
        return "—"
    text = str(value).replace("|", "\\|").replace("\n", " ")
    return text


def to_markdown(report):
    """渲染视图。**不做任何判定**：只把 report 里已有的值摆出来。"""
    lines = []
    lines.append("# 跨格式契约兼容性判定")
    lines.append("")
    lines.append(
        "- policy: `%s` ｜ verdict: **%s**" % (report.get("policy"), report.get("verdict"))
    )
    inputs = report.get("inputs") or {}
    lines.append("- 输入: old=`%s` ｜ new=`%s`" % (inputs.get("old"), inputs.get("new")))
    lines.append("- tool: %s %s" % (report.get("tool"), report.get("version")))
    lines.append("")
    findings = report.get("findings") or []
    lines.append("## 判定表（%d 条）" % len(findings))
    lines.append("")
    if findings:
        lines.append("| rule_id | stable_path | severity | direction | blast_radius | repair |")
        lines.append("|---|---|---|---|---|---|")
        for row in findings:
            lines.append(
                "| %s | %s | %s | %s | %s | %s |"
                % (
                    _cell(row.get("rule_id")),
                    _cell(row.get("stable_path")),
                    _cell(row.get("severity")),
                    _cell(row.get("direction")),
                    _cell(row.get("blast_radius")),
                    _cell(row.get("repair_action")),
                )
            )
    else:
        lines.append("（无命中）")
    lines.append("")

    explained = [row for row in findings if row.get("why_static_breaking") or row.get("what_would_trigger")]
    if explained:
        lines.append("## runtime-dependent 说明")
        lines.append("")
        for row in explained:
            lines.append(
                "- `%s` @ `%s` — 静态必破：%s ｜ 触发条件：%s"
                % (
                    row.get("rule_id"),
                    row.get("stable_path"),
                    row.get("why_static_breaking") or "—",
                    row.get("what_would_trigger") or "—",
                )
            )
        lines.append("")

    unsupported = report.get("ir_unsupported") or []
    if unsupported:
        lines.append("## 不可表达的构造（ir_unsupported）")
        lines.append("")
        for item in unsupported:
            lines.append(
                "- `%s` @ `%s` — %s"
                % (item.get("construct"), item.get("json_pointer"), item.get("reason"))
            )
        lines.append("")

    notes = report.get("notes") or []
    if notes:
        lines.append("## 说明")
        lines.append("")
        for note in notes:
            lines.append("- %s" % note)
        lines.append("")

    lines.append("---")
    lines.append("digest: `%s`（Markdown 是 JSON 的渲染视图，不参与 digest）" % report.get(DIGEST_KEY))
    return "\n".join(lines) + "\n"


def render(report, fmt):
    """唯一出口：按格式渲染。未知格式**显式拒绝**（不静默回落到 md）。"""
    if fmt == "json":
        return to_json(report)
    if fmt == "md":
        return to_markdown(report)
    raise UsageError("未知输出格式: %r（允许 md / json）" % fmt)


def verify_file(path):
    """读回一份报告并做**自洽校验**（重算 digest）。

    返回 ``(ok, differences)``；``differences`` 非空时每条带 ``json_path``，
    定位到被改动的叶子字段（先比内容，后比 digest）。
    """
    if not os.path.isfile(path):
        raise UsageError("待校验报告不存在: %s" % path)
    with open(path, "r", encoding="utf-8-sig") as handle:
        text = handle.read()
    report = loads(text)
    return verify_report(report, baseline=None)
