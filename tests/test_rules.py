# -*- coding: utf-8 -*-
"""规则表结构与覆盖矩阵（M0 已实现的部分）。

7 条规则 × 3 格式 = 21 格，`applies=false` 的格子必须有理由（`N/A` 是结论不是缺失）。
这条测试是"每条规则三格式各有用例"的**机械核对前提**——规则表缺格时先在这里红。
"""

import json
import os

import pytest

from contractcompat.errors import UsageError
from contractcompat.ir import FORMATS
from contractcompat.rules import (
    EXPECTED_RULE_IDS,
    SEVERITIES,
    default_rule_path,
    load_rule_table,
    rule_ids,
    validate_rule_table,
)


def test_rule_table_loads_and_has_seven_rules():
    table = load_rule_table()
    assert rule_ids(table) == EXPECTED_RULE_IDS
    assert len(table["rules"]) == 7


def test_every_rule_has_three_format_slots():
    table = load_rule_table()
    for rule in table["rules"]:
        assert set(rule["formats"]) == set(FORMATS), rule["rule_id"]


def test_applicable_slots_declare_evidence():
    table = load_rule_table()
    for rule in table["rules"]:
        for fmt, slot in rule["formats"].items():
            if slot["applies"]:
                assert slot["evidence"], "%s/%s 缺 evidence" % (rule["rule_id"], fmt)


def test_not_applicable_slots_declare_reason():
    """`N/A` 是显式结论：没有字段号这个概念，不等于"这个格式没这问题"。"""
    table = load_rule_table()
    na = [(rule["rule_id"], fmt) for rule in table["rules"] for fmt, slot in rule["formats"].items() if not slot["applies"]]
    assert ("R5", "avro") in na
    assert ("R5", "jsonschema") in na
    assert ("R6", "avro") in na
    for rule in table["rules"]:
        for fmt, slot in rule["formats"].items():
            if not slot["applies"]:
                assert slot["reason"], "%s/%s 的 N/A 缺理由" % (rule["rule_id"], fmt)


def test_coverage_matrix_is_twenty_one_cells():
    table = load_rule_table()
    cells = [(rule["rule_id"], fmt) for rule in table["rules"] for fmt in rule["formats"]]
    assert len(cells) == 21
    assert len(set(cells)) == 21


def test_severity_values_are_three():
    assert set(SEVERITIES) == {"breaking", "runtime-dependent", "non-breaking"}
    table = load_rule_table()
    for rule in table["rules"]:
        assert rule["default_severity"] in SEVERITIES


def test_runtime_dependent_rules_have_both_explanations():
    """红线③：runtime-dependent 必须带两段说明，缺一即违约。"""
    table = load_rule_table()
    templates = table["runtime_dependent_templates"]
    runtime_rules = [rule["rule_id"] for rule in table["rules"] if rule["default_severity"] == "runtime-dependent"]
    assert runtime_rules, "至少要有一条规则默认 runtime-dependent"
    for rule_id in runtime_rules:
        assert rule_id in templates, "%s 缺 runtime-dependent 说明模板" % rule_id
        assert templates[rule_id]["why_static_breaking"]
        assert templates[rule_id]["what_would_trigger"]


def test_validate_rejects_missing_format_slot():
    table = json.loads(json.dumps(load_rule_table()))
    del table["rules"][0]["formats"]["avro"]
    with pytest.raises(UsageError) as caught:
        validate_rule_table(table)
    assert "avro" in str(caught.value)


def test_validate_rejects_bad_severity():
    table = json.loads(json.dumps(load_rule_table()))
    table["rules"][0]["default_severity"] = "maybe-breaking"
    with pytest.raises(UsageError):
        validate_rule_table(table)


def test_validate_rejects_extra_rule():
    """规则集合写死：多一条或少一条都要红，否则"七类规则"这个承诺会被静默改掉。"""
    table = json.loads(json.dumps(load_rule_table()))
    table["rules"].append(dict(table["rules"][0], rule_id="R8", name="EXTRA"))
    with pytest.raises(UsageError):
        validate_rule_table(table)


def test_rule_path_is_repo_relative_not_absolute_in_report():
    """规则表路径可用于加载，但**绝不进报告**（绝对路径会让 digest 跨机不可复算）。"""
    path = default_rule_path()
    assert path.endswith("rule-table.json")


def test_packaged_mirror_matches_source():
    """包内镜像是**生成物**：与仓库根那份逐字节一致，否则 wheel 安装后口径与源码态不同。

    这条是"安装面"的一条：`pip install .` 后仓库根的 `rules/` 不在盘上，
    能加载的只有包内那份；两份漂移会让"本机跑得通、装好的包跑不通"或反过来。
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source = os.path.join(root, "rules", "rule-table.json")
    mirror = os.path.join(root, "src", "contractcompat", "data", "rule-table.json")
    with open(source, "rb") as handle:
        source_bytes = handle.read()
    with open(mirror, "rb") as handle:
        mirror_bytes = handle.read()
    assert source_bytes == mirror_bytes, "包内镜像与仓库根规则表不一致：改完源文件要同步镜像"


def test_evaluate_not_implemented_yet():
    from contractcompat.rules import evaluate

    with pytest.raises(NotImplementedError):
        evaluate([])
