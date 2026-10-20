# -*- coding: utf-8 -*-
"""报告渲染：确定性、零判定、无绝对路径。

M5 才接上真实 findings；本文件现在锁住"渲染层不做判定"与"md 不参与 digest"，
两条都是发布期的常见返工点。
"""

import copy

import pytest

from contractcompat.errors import UsageError
from contractcompat.report import FINDING_KEYS, build, render, to_json, to_markdown


def sample():
    return build(
        "backward",
        "order-v1.avsc",
        "order-v2.avsc",
        findings=[
            {
                "rule_id": "R4",
                "rule_name": "ENUM_NARROWED",
                "stable_path": "status",
                "severity": "runtime-dependent",
                "direction": "NONE_OK",
                "format_evidence": "symbol_removed",
                "why_static_breaking": "枚举取值集合被收窄",
                "what_would_trigger": "数据流里出现被删取值时",
            }
        ],
        notes=["deploy_order_not_given"],
    )


def test_render_is_deterministic():
    report = sample()
    assert to_json(report) == to_json(copy.deepcopy(report))
    assert to_markdown(report) == to_markdown(copy.deepcopy(report))


def test_markdown_is_not_part_of_digest():
    report = sample()
    before = report["digest"]
    to_markdown(report)
    assert report["digest"] == before


def test_markdown_contains_key_sections():
    text = to_markdown(sample())
    assert "# 跨格式契约兼容性判定" in text
    assert "R4" in text
    assert "runtime-dependent 说明" in text
    assert "deploy_order_not_given" in text


def test_markdown_has_no_absolute_paths():
    """报告不写绝对路径：md 里出现盘符或 /home/ 即视为泄露（会让同一输入跨机不同字节）。"""
    text = to_markdown(sample())
    assert "C:\\" not in text and "C:/" not in text
    assert "/home/" not in text and "Users" not in text


def test_finding_keys_are_fixed_and_nullable():
    report = sample()
    row = report["findings"][0]
    assert tuple(row) == FINDING_KEYS or set(row) == set(FINDING_KEYS)
    # 不适用的字段保留键并写 null（键集合稳定比"省略键"更重要）
    assert row["blast_radius"] is None
    assert row["repair_hint"] is None


def test_render_rejects_unknown_format():
    with pytest.raises(UsageError):
        render(sample(), "yaml")


def test_markdown_changes_when_conclusion_changes():
    """渲染层零判定：它自己不算，但必须忠实反映传入的结论。"""
    report = sample()
    before = to_markdown(report)
    report["findings"][0]["severity"] = "breaking"
    assert to_markdown(report) != before
    assert "breaking" in to_markdown(report)


def test_summary_counts_are_computed_from_findings():
    report = sample()
    assert report["summary"]["runtime_dependent"] == 1
    assert report["summary"]["breaking"] == 0


def test_unsupported_constructs_are_rendered():
    report = build(
        "backward",
        "a.json",
        "b.json",
        ir_unsupported=[{"construct": "patternProperties", "json_pointer": "/patternProperties", "reason": "无法枚举"}],
    )
    text = to_markdown(report)
    assert "patternProperties" in text
    assert "不可表达的构造" in text


def test_empty_findings_render_cleanly():
    report = build("backward", "a.avsc", "b.avsc")
    text = to_markdown(report)
    assert "（无命中）" in text
    assert report["digest"]
