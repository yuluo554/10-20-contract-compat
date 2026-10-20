# -*- coding: utf-8 -*-
"""反例门：4 条"看起来破、实际不破"的夹具，规则求值**不得报 breaking**。

反例的作用是**防止规则退化成"看到变化就报破"**——没有反例，误报率无门可守
（`plan/04` §二）。这里断言的是 findings 的 severity，不是 verdict：verdict 由方向决定，
severity 才是"这条命中算不算破例"的结论。

`union-add-type` 是最容易误报的一条：Avro union 新增分支确实改了 `type` 字符串，
但 resolving decoder 下旧数据仍可读（`detail=union_widened`）。规则表里
`R2.severity_by_detail.union_widened = non-breaking` 就是这条反例的落点。
"""

import os

import pytest

from contractcompat.parsers import parse
from contractcompat.policy import diff
from contractcompat.rules import evaluate, load_rule_table

import fixture_scan

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def evaluate_negative(slug, policy="backward"):
    sides = fixture_scan.scan_negatives()[slug]
    return evaluate(
        diff(parse(sides["old"]), parse(sides["new"])),
        load_rule_table(),
        policy=policy,
    )


def test_negatives_are_scanned_from_disk():
    """非空跑自证：反例清单必须真在盘上，否则下面的参数化用例什么也没证明。"""
    assert sorted(fixture_scan.scan_negatives()) == sorted(fixture_scan.NEGATIVE_SLUGS)


@pytest.mark.parametrize("slug", fixture_scan.NEGATIVE_SLUGS)
def test_negative_has_no_breaking_finding(slug):
    """四条反例的共同底线：**不得有 breaking**（可以是空，也可以全 non-breaking）。"""
    rows = evaluate_negative(slug)
    breaking = [row for row in rows if row["severity"] == "breaking"]
    assert breaking == [], "%s 被误报成 breaking: %s" % (
        slug, [(row["rule_id"], row["stable_path"], row["format_evidence"]) for row in breaking])


@pytest.mark.parametrize("slug", fixture_scan.NEGATIVE_SLUGS)
def test_negative_has_no_runtime_dependent_finding(slug):
    """反例也不该落到 `runtime-dependent`：它们不是"可能炸"，而是**确实不破**。"""
    rows = evaluate_negative(slug)
    assert [row for row in rows if row["severity"] == "runtime-dependent"] == []


def test_union_add_type_is_lowered_by_detail_not_by_ignoring_the_fact():
    """`union-add-type`：事实照常产出（`type_changed`），但 severity 按 `union_widened` 降级。

    **不许**为了反例好看把差异吞掉——那会让"这条夹具演了什么"无从核对。
    """
    rows = [row for row in evaluate_negative("union-add-type") if row["severity"]]
    assert len(rows) == 1, rows
    assert rows[0]["rule_id"] == "R2"
    assert rows[0]["severity"] == "non-breaking"
    assert rows[0]["format_evidence"] == "union_branch_added"
    assert rows[0]["evidence"]["detail"] == "union_widened"


def test_union_narrowing_is_still_breaking():
    """阳性对照：把 union 分支**删掉**（`union_narrowed`）时同一条规则必须报 breaking。

    这里用 `forward`：收窄的方向是 `BACKWARD_OK`，backward 恰好接受它（新写老读通），
    所以"破"只在不接受该方向的 policy 下成立。换 `--policy` 会换 severity 正是三值语义。
    没有这条对照，"union 加类型不破"可能只是"R2 从来不算破"——两种实现的输出一样。
    """
    old_payload = {
        "type": "record",
        "name": "Order",
        "namespace": "example.invalid.contracts",
        "fields": [{"name": "total_amount", "type": ["null", "long", "string"], "default": None}],
    }
    new_payload = {
        "type": "record",
        "name": "Order",
        "namespace": "example.invalid.contracts",
        "fields": [{"name": "total_amount", "type": ["null", "long"], "default": None}],
    }
    import json
    import tempfile

    directory = tempfile.mkdtemp(prefix="cc-union-")
    old_path = os.path.join(directory, "old.avsc")
    new_path = os.path.join(directory, "new.avsc")
    with open(old_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(old_payload))
    with open(new_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(new_payload))

    rows = [row for row in evaluate(diff(parse(old_path), parse(new_path)), load_rule_table(), policy="forward")
            if row["rule_id"] == "R2"]
    assert rows and rows[0]["severity"] == "breaking"
    assert rows[0]["format_evidence"] == "union_branch_removed"


def test_delete_reserved_negative_produces_no_findings_at_all():
    """删字段但号已 `reserved`：R1 不命中，R5 也不命中（proto 无 N/A 槽位）→ 空表。"""
    assert evaluate_negative("delete-reserved") == []


def test_rename_with_alias_only_yields_na_rows():
    """改名带 `aliases`：没有命中，只剩该格式的 N/A 结论（Avro → R5/R6）。"""
    rows = evaluate_negative("rename-with-alias")
    assert [row["rule_id"] for row in rows] == ["R5", "R6"]
    assert all(row["format_evidence"] == "N/A" for row in rows)


def test_add_optional_property_is_not_an_r3_hit():
    """加可选 property 不是 R3：只有"必填且无默认"才是 requiredness 破例。"""
    rows = [row for row in evaluate_negative("add-optional-property") if row["severity"]]
    assert rows == []
