# -*- coding: utf-8 -*-
"""规范 JSON / digest / 篡改定位。

这些断言是"报告可复算"的地基：M5 的 golden 与 `--verify` 全部依赖它们。
"""

import copy
import json

import pytest

from contractcompat import __version__
from contractcompat.canonical import (
    DIGEST_KEY,
    digest,
    dumps,
    loads,
    structural_diff,
    verify_report,
)
from contractcompat.errors import CanonicalError


def sample_report():
    return {
        "schema_version": 1,
        "tool": "contractcompat",
        "version": __version__,
        "policy": "backward",
        "verdict": "breaking",
        "inputs": {"old": "old.avsc", "new": "new.avsc"},
        "ir_unsupported": [],
        "findings": [
            {
                "rule_id": "R1",
                "stable_path": "6",
                "severity": "breaking",
                "direction": "NONE_OK",
            }
        ],
        "summary": {"findings_total": 1, "breaking": 1, "runtime_dependent": 0, "non_breaking": 0},
        "notes": [],
    }


def test_dumps_is_deterministic_and_canonical():
    report = sample_report()
    first = dumps(report)
    second = dumps(copy.deepcopy(report))
    assert first == second
    assert first.endswith("\n") and not first.endswith("\n\n")
    # 键序固定（sort_keys），中文不转义
    assert first.index('"findings"') < first.index('"inputs"')  # 字母序：findings < inputs
    assert first.index('"inputs"') < first.index('"notes"')
    chinese = dumps({"名字": "契约兼容"})
    assert "契约兼容" in chinese and "\\u" not in chinese


def test_dumps_rejects_unserializable():
    with pytest.raises(CanonicalError):
        dumps({"bad": object()})


def test_loads_requires_object_top_level():
    with pytest.raises(CanonicalError):
        loads("[1, 2, 3]")
    with pytest.raises(CanonicalError):
        loads("{not json")


def test_digest_excludes_itself():
    report = sample_report()
    first = digest(report)
    report_with_digest = dict(report)
    report_with_digest[DIGEST_KEY] = first
    # 写回 digest 这个动作不得改变 digest（否则是自指）
    assert digest(report_with_digest) == first
    assert first == digest(report)


def test_digest_changes_when_content_changes():
    report = sample_report()
    before = digest(report)
    report["findings"][0]["severity"] = "non-breaking"
    assert digest(report) != before


def test_verify_self_consistency_catches_tamper():
    report = sample_report()
    report[DIGEST_KEY] = digest(report)
    ok, differences = verify_report(report)
    assert ok and differences == []

    tampered = copy.deepcopy(report)
    tampered["findings"][0]["severity"] = "non-breaking"
    ok, differences = verify_report(tampered)
    assert not ok
    assert [item["json_path"] for item in differences] == [DIGEST_KEY]


def test_verify_with_baseline_localizes_field():
    """给了 baseline 时**先比内容再比 digest**：定位必须落到叶子字段，而不是只说 digest 不对。"""
    baseline = sample_report()
    baseline[DIGEST_KEY] = digest(baseline)
    tampered = copy.deepcopy(baseline)
    tampered["findings"][0]["severity"] = "non-breaking"
    tampered[DIGEST_KEY] = digest(tampered)  # 连 digest 一起重算：仍要能定位

    ok, differences = verify_report(tampered, baseline=baseline)
    assert not ok
    assert [item["json_path"] for item in differences] == ["findings[0].severity"]
    assert differences[0]["expected"] == "breaking"
    assert differences[0]["actual"] == "non-breaking"


def test_structural_diff_reports_missing_and_unexpected():
    differences = structural_diff({"a": 1}, {"b": 2})
    kinds = sorted(item["kind"] for item in differences)
    assert kinds == ["missing", "unexpected"]


def test_structural_diff_reports_length_change():
    differences = structural_diff({"items": [1]}, {"items": [1, 2]})
    assert [(item["json_path"], item["kind"]) for item in differences] == [("items", "length")]


def test_roundtrip_through_loads():
    report = sample_report()
    assert loads(dumps(report)) == report


def test_dumps_matches_upstream_json_for_simple_document():
    """规范化参数是冻结契约：改成别的 indent / sort 会让全部 golden 失效。"""
    assert dumps({"b": 1, "a": 2}) == json.dumps({"a": 2, "b": 1}, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
