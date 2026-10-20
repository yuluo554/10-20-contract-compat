# -*- coding: utf-8 -*-
"""归因四态与 deploy-order 契约（M5 落地面）。

归因只由三元组决定：``(direction 判定, deploy_order, 该格式的字段可寻址性)``
（``data/README.md`` §4.6）。本文件锁住四件事：

  * 四种 ``--deploy-order`` **各断言一次**（不是一条参数化打天下）；
  * ``REPLAY_ONLY`` 只在显式 ``replay`` 出现；
  * 缺 ``--deploy-order`` → ``null`` + ``deploy_order_not_given``（不猜默认顺序）；
  * 归因层**只补** ``blast_radius``：direction / severity / repair_* 一个都不改动，
    N/A 行保持 ``null``，``runtime-dependent`` 不被压平。
"""

import copy
import os

import pytest

from contractcompat.blast import (
    ADDRESSABILITY,
    BLAST_RADII,
    DEPLOY_ORDERS,
    NOT_GIVEN_NOTE,
    REPAIR_ACTIONS,
    attribute,
    validate_deploy_order,
)
from contractcompat.errors import UsageError
from contractcompat.parsers import parse
from contractcompat.policy import diff
from contractcompat.rules import evaluate, load_rule_table

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FIXTURE_SUFFIX = {"proto": "pb", "avro": "avsc", "jsonschema": "json"}


def fixture_path(directory, slug, side, fmt):
    return os.path.join(
        ROOT, "data", "fixtures", directory, "%s-%s.%s" % (slug, side, FIXTURE_SUFFIX[fmt])
    )


def evaluate_pair(directory, slug, fmt, policy="backward"):
    old = parse(fixture_path(directory, slug, "old", fmt))
    new = parse(fixture_path(directory, slug, "new", fmt))
    return evaluate(diff(old, new), load_rule_table(), policy=policy)


# ── 契约面 ────────────────────────────────────────────────────────────────


def test_four_deploy_orders():
    assert set(DEPLOY_ORDERS) == {"consumers-first", "producers-first", "simultaneous", "replay"}


def test_four_blast_radii():
    assert set(BLAST_RADII) == {"OLD_CONSUMER", "NEW_CONSUMER", "BOTH", "REPLAY_ONLY"}


def test_five_repair_actions():
    assert set(REPAIR_ACTIONS) == {"reserve", "alias", "add-default", "add-branch", "bump-and-version"}


def test_unknown_deploy_order_rejected():
    with pytest.raises(UsageError):
        validate_deploy_order("consumers-last")


def test_none_deploy_order_is_allowed():
    assert validate_deploy_order(None) is None


def test_addressability_covers_all_three_formats():
    """三元组第三维：三格式各有一条可寻址性口径（缺一格就是不认识该格式）。"""
    assert set(ADDRESSABILITY) == {"proto", "avro", "jsonschema"}


# ── 缺省不猜 ──────────────────────────────────────────────────────────────


def test_missing_deploy_order_does_not_guess():
    """不给 --deploy-order 时归因字段留 null 并显式说明——**不替用户挑一个默认顺序**。

    默认值会被当成结论用，而这正是本题要消除的误判。
    """
    findings = [{"rule_id": "R1", "stable_path": "6", "severity": "breaking", "blast_radius": None}]
    result, notes = attribute(findings, None)
    assert result[0]["blast_radius"] is None
    assert notes == [NOT_GIVEN_NOTE]


def test_missing_deploy_order_applies_to_every_hit():
    rows = evaluate_pair("avro", "r1-field-removed", "avro")
    assert all("blast_radius" not in row for row in rows), "规则层不填 blast_radius（K4）"
    result, notes = attribute(rows, None)
    assert notes == [NOT_GIVEN_NOTE]
    assert [row["blast_radius"] for row in result] == [None] * len(rows)


# ── 四态 × 四种部署顺序：各断言一次 ────────────────────────────────────────


def _r1_rows():
    """同一破例：Avro 删字段（R1）。四种顺序都拿它断言，证明"归因随顺序变"。"""
    rows = evaluate_pair("avro", "r1-field-removed", "avro")
    hits = [row for row in rows if row["rule_id"] == "R1"]
    assert len(hits) == 1, hits
    return rows


def test_consumers_first_attributes_old_consumer():
    """consumers-first：老消费者仍在线上，读到新生产者写出的数据 → OLD_CONSUMER。"""
    rows, notes = attribute(_r1_rows(), "consumers-first")
    hit = [row for row in rows if row["rule_id"] == "R1"][0]
    assert hit["blast_radius"] == "OLD_CONSUMER"
    assert notes == []


def test_producers_first_attributes_new_consumer():
    """producers-first：新消费者已上线，还在读老生产者写出的数据 → NEW_CONSUMER。"""
    rows, _ = attribute(_r1_rows(), "producers-first")
    hit = [row for row in rows if row["rule_id"] == "R1"][0]
    assert hit["blast_radius"] == "NEW_CONSUMER"


def test_simultaneous_attributes_both():
    """simultaneous：两侧版本同时在位，两个方向都暴露 → BOTH。"""
    rows, _ = attribute(_r1_rows(), "simultaneous")
    hit = [row for row in rows if row["rule_id"] == "R1"][0]
    assert hit["blast_radius"] == "BOTH"


def test_replay_attributes_replay_only():
    """replay：只有历史数据重放时炸 → REPLAY_ONLY（显式给出才出现）。"""
    rows, _ = attribute(_r1_rows(), "replay")
    hit = [row for row in rows if row["rule_id"] == "R1"][0]
    assert hit["blast_radius"] == "REPLAY_ONLY"


def test_replay_only_never_appears_without_replay():
    """`REPLAY_ONLY` 只在显式 replay 时出现——其余三种顺序一个都不许有。"""
    for order in ("consumers-first", "producers-first", "simultaneous"):
        rows, _ = attribute(_r1_rows(), order)
        assert all(row["blast_radius"] != "REPLAY_ONLY" for row in rows), order


def test_same_finding_changes_radius_with_order():
    """同一破例在三种实时顺序下拿到三个不同的归因——"归因随部署顺序改变"的机械形态。"""
    radii = set()
    for order in ("consumers-first", "producers-first", "simultaneous"):
        rows, _ = attribute(_r1_rows(), order)
        radii.add([row for row in rows if row["rule_id"] == "R1"][0]["blast_radius"])
    assert radii == {"OLD_CONSUMER", "NEW_CONSUMER", "BOTH"}


@pytest.mark.parametrize("fmt,directory", [("proto", "proto"), ("jsonschema", "jsonschema")])
def test_four_states_hold_in_other_formats(fmt, directory):
    """三格式同一口径：删字段在另一格式也按同一张表归因（覆盖三元组的第三维）。"""
    rows = evaluate_pair(directory, "r1-field-removed", fmt)
    hits = [row for row in rows if row["rule_id"] == "R1"]
    assert len(hits) == 1, hits
    for order, expected in (
        ("consumers-first", "OLD_CONSUMER"),
        ("producers-first", "NEW_CONSUMER"),
        ("simultaneous", "BOTH"),
        ("replay", "REPLAY_ONLY"),
    ):
        result, _ = attribute(copy.deepcopy(rows), order)
        hit = [row for row in result if row["rule_id"] == "R1"][0]
        assert hit["blast_radius"] == expected, (fmt, order)


# ── 归因层只补一列 ────────────────────────────────────────────────────────


def test_na_rows_keep_null_blast_radius():
    """N/A 行（severity=None）不参与归因：`null` 是"该格式无此概念"，不是"没人会炸"。"""
    rows = evaluate_pair("avro", "r1-field-removed", "avro")
    na_rows = [row for row in rows if row["severity"] is None]
    assert na_rows, "Avro 下 R5/R6 必须是 N/A 行"
    result, _ = attribute(rows, "consumers-first")
    for row in result:
        if row["severity"] is None:
            assert row["blast_radius"] is None, row
        else:
            assert row["blast_radius"] == "OLD_CONSUMER", row


def test_runtime_dependent_entry_is_not_flattened():
    """`runtime-dependent` 在归因里保留三值语义：severity/两段说明原样，只有 blast_radius 变化。"""
    rows = evaluate_pair("avro", "r4-enum-narrowed", "avro", policy="forward")
    hit = [row for row in rows if row["rule_id"] == "R4"][0]
    assert hit["severity"] == "runtime-dependent"
    why, trigger = hit["why_static_breaking"], hit["what_would_trigger"]
    result, _ = attribute(rows, "simultaneous")
    after = [row for row in result if row["rule_id"] == "R4"][0]
    assert after["severity"] == "runtime-dependent"
    assert after["why_static_breaking"] == why and after["what_would_trigger"] == trigger
    assert after["blast_radius"] == "BOTH"


def test_attribute_does_not_recompute_direction_or_overwrite_repair():
    """归因层只补 `blast_radius`：direction / repair_action / repair_hint 一个都不改。"""
    rows = evaluate_pair("avro", "r1-field-removed", "avro")
    snapshot = [
        (row["rule_id"], row["direction"], row["repair_action"], row["repair_hint"]) for row in rows
    ]
    result, _ = attribute(rows, "producers-first")
    after = [
        (row["rule_id"], row["direction"], row["repair_action"], row["repair_hint"]) for row in result
    ]
    assert after == snapshot


def test_unknown_format_is_not_attributed():
    """三元组第三维:不认识的格式不猜可寻址性 → 留 null + 说明。"""
    findings = [
        {
            "rule_id": "R1",
            "stable_path": "x",
            "severity": "breaking",
            "evidence": {"format": "thrift"},
        }
    ]
    result, notes = attribute(findings, "consumers-first")
    assert result[0]["blast_radius"] is None
    assert notes == ["format_not_addressable"]


# ── repair_action 三格式语法落点 ──────────────────────────────────────────


@pytest.mark.parametrize(
    "directory,fmt,expected_action,expected_prefix",
    [
        ("proto", "proto", "reserve", "reserved 2;"),
        ("avro", "avro", "reserve", '"aliases": ["total_amount"]'),
        ("jsonschema", "jsonschema", "reserve", '"default":'),
    ],
)
def test_r1_repair_hint_matches_format_syntax(directory, fmt, expected_action, expected_prefix):
    """修复动作必须落在该格式的语法上：Protobuf `reserved 2;`、Avro `"aliases"`、
    JSON Schema `"default"`（题面模块④的验收条目；文本来自规则表，不是散落的 if）。"""
    rows = evaluate_pair(directory, "r1-field-removed", fmt)
    hit = [row for row in rows if row["rule_id"] == "R1"][0]
    assert hit["repair_action"] == expected_action
    assert hit["repair_hint"].startswith(expected_prefix), hit["repair_hint"]
