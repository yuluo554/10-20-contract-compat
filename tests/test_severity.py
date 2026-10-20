# -*- coding: utf-8 -*-
"""`severity` 三值语义（红线③的定义处 = `data/README.md` §4.4）。

`severity` 是**相对当前 policy** 的判定，不是"看到变化就报破"：

  * 该 policy 接受这个方向 → 不标破（表里的 `severity_when_allowed`）；
  * 该 policy 不接受 → 规则默认值，`severity_by_detail` 可按事实细节改写；
  * `runtime-dependent` **必须**带 `why_static_breaking` + `what_would_trigger` 两段，
    且 `--ignore-runtime-dependent` 只改退出码、**不删条目**。

本文件是"三值没被压平"的可证伪形态：每一条都同时断言"条目在"与"解释在"。
"""

import io
import os

import pytest

from contractcompat.cli import _exit_code, main
from contractcompat.parsers import parse
from contractcompat.policy import diff
from contractcompat.report import build
from contractcompat.rules import SEVERITIES, evaluate, load_rule_table

import fixture_scan

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fixture_path(directory, slug, side, fmt):
    suffix = {"proto": "pb", "avro": "avsc", "jsonschema": "json"}[fmt]
    return os.path.join(ROOT, "data", "fixtures", directory, "%s-%s.%s" % (slug, side, suffix))


def run(argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    return main(argv, stdout=stdout, stderr=stderr), stdout.getvalue(), stderr.getvalue()


def evaluate_pair(directory, slug, fmt, policy="backward"):
    old = parse(fixture_path(directory, slug, "old", fmt))
    new = parse(fixture_path(directory, slug, "new", fmt))
    return evaluate(diff(old, new), load_rule_table(), policy=policy)


# ── 三值本身 ───────────────────────────────────────────────────────────────


def test_severity_is_always_one_of_three_or_null():
    """三值之外只允许 `null`（N/A 行不是命中，不参与计数）。"""
    found, _ = fixture_scan.scan_rule_fixtures()
    for rule_id, fmt, _slug, old_path, new_path in [
        (rule["rule_id"], fmt, None, None, None) for rule in load_rule_table()["rules"] for fmt in ("proto", "avro", "jsonschema")
    ]:
        olds = found.get(rule_id, {}).get(fmt, {}).get("old", [])
        news = found.get(rule_id, {}).get(fmt, {}).get("new", [])
        for old, new in zip(olds, news):
            for row in evaluate(diff(parse(old), parse(new)), load_rule_table(), policy="backward"):
                assert row["severity"] is None or row["severity"] in SEVERITIES, row


def test_runtime_dependent_always_carries_both_explanations():
    """红线③的机械形态：凡是 `runtime-dependent` 的行，两段说明都不能是空/None。"""
    found, _ = fixture_scan.scan_rule_fixtures()
    runtime_rows = 0
    for rule_id in found:
        for fmt in found[rule_id]:
            for old, new in zip(found[rule_id][fmt].get("old", []), found[rule_id][fmt].get("new", [])):
                for row in evaluate(diff(parse(old), parse(new)), load_rule_table(), policy="backward"):
                    if row["severity"] != "runtime-dependent":
                        continue
                    runtime_rows += 1
                    assert row["why_static_breaking"], row
                    assert row["what_would_trigger"], row
    # 非空跑自证：至少有一条真的走到了 runtime-dependent 分支
    assert runtime_rows >= 1


def test_enum_narrowed_is_runtime_dependent_when_the_policy_rejects_the_direction():
    """enum 收窄是红线③点名的典型：在**该方向不被接受**的 policy 下必须是独立一档。

    收窄的 direction 是 `BACKWARD_OK`（新写老读通）。`forward*` 不接受它 → 静态必破；
    是否真炸取决于历史数据里有没有被删取值 → 正好是 `runtime-dependent`。
    """
    for directory, fmt in (("proto", "proto"), ("avro", "avro"), ("jsonschema", "jsonschema")):
        rows = [row for row in evaluate_pair(directory, "r4-enum-narrowed", fmt, "forward") if row["rule_id"] == "R4"]
        assert len(rows) == 1, rows
        assert rows[0]["severity"] == "runtime-dependent"
        assert rows[0]["why_static_breaking"] and rows[0]["what_would_trigger"]


def test_enum_narrowed_is_not_breaking_when_the_policy_accepts_the_direction():
    """同一份收窄在 `backward` 下**不标破**：§4.4 的条件①是"静态上不满足当前 policy"。

    这不是放水：新 schema 写不出被删取值，所以 backward 的读路径确实成立。
    """
    rows = [row for row in evaluate_pair("avro", "r4-enum-narrowed", "avro", "backward") if row["rule_id"] == "R4"]
    assert [row["severity"] for row in rows] == ["non-breaking"]


def test_oneof_moved_is_runtime_dependent():
    """JSON Schema 的 `oneOf` 分支替换是 `NONE_OK`：backward 下也静态必破 → runtime-dependent。"""
    rows = [row for row in evaluate_pair("jsonschema", "r6-oneof-moved", "jsonschema") if row["rule_id"] == "R6"]
    assert [row["severity"] for row in rows] == ["runtime-dependent"]
    assert rows[0]["why_static_breaking"] and rows[0]["what_would_trigger"]


def test_default_changed_is_non_breaking():
    rows = [row for row in evaluate_pair("avro", "r7-default-changed", "avro") if row["rule_id"] == "R7"]
    assert [row["severity"] for row in rows] == ["non-breaking"]


def test_severity_depends_on_policy_not_only_on_the_fact():
    """同一事实换 policy 会换 severity——三值语义里"静态必破"本来就是相对判定式说的。"""
    backward = [row for row in evaluate_pair("proto", "r4-enum-narrowed", "proto", "backward") if row["rule_id"] == "R4"]
    forward = [row for row in evaluate_pair("proto", "r4-enum-narrowed", "proto", "forward") if row["rule_id"] == "R4"]
    assert backward[0]["severity"] == "non-breaking"
    assert forward[0]["severity"] == "runtime-dependent"


def test_policy_none_never_marks_anything_breaking():
    """`none` 只列差异不判定：所有命中都是 non-breaking（退出码另有 `--policy none` 保证）。"""
    for row in evaluate_pair("avro", "r1-field-removed", "avro", "none"):
        assert row["severity"] in (None, "non-breaking"), row


# ── 三值 × 退出码 × 报告 ───────────────────────────────────────────────────


def test_runtime_dependent_entry_survives_ignore_flag_in_json():
    """可关判定强度，不可让条目消失：`--ignore-runtime-dependent` 后条目与说明仍在。"""
    old = fixture_path("jsonschema", "r6-oneof-moved", "old", "jsonschema")
    new = fixture_path("jsonschema", "r6-oneof-moved", "new", "jsonschema")
    code, out, _ = run([old, new, "--format", "json", "--ignore-runtime-dependent"])
    assert code == 0
    from contractcompat.canonical import loads

    payload = loads(out)
    rows = [row for row in payload["findings"] if row["rule_id"] == "R6" and row["severity"]]
    assert len(rows) == 1
    assert rows[0]["severity"] == "runtime-dependent"
    assert rows[0]["why_static_breaking"] and rows[0]["what_would_trigger"]
    assert payload["summary"]["runtime_dependent"] == 1


def test_runtime_dependent_exits_one_by_default():
    old = fixture_path("jsonschema", "r6-oneof-moved", "old", "jsonschema")
    new = fixture_path("jsonschema", "r6-oneof-moved", "new", "jsonschema")
    code, out, _ = run([old, new])
    assert code == 1
    assert "runtime-dependent 说明" in out  # md 视图里也要有那两段


def test_exit_code_prefers_severity_over_verdict_fallback():
    """有 severity 分类时以 severity 为准；回落分支只在"一条都没分类"时兜底。

    这条锁住 M3 的过渡分支不会反过来盖住 M4 的结论：一份 `verdict=breaking`
    但命中全是 `non-breaking` 的报告必须退出 0（那正是"策略接受了这个方向"）。
    """
    classified = build(
        "forward",
        "a.avsc",
        "b.avsc",
        findings=[{"rule_id": "R1", "stable_path": "x", "severity": "non-breaking"}],
        verdict="breaking",
    )
    assert _exit_code(classified, True) == 0

    unclassified = build(
        "backward",
        "a.avsc",
        "b.avsc",
        findings=[{"rule_id": None, "stable_path": "x", "severity": None}],
        verdict="breaking",
    )
    assert _exit_code(unclassified, True) == 1, "全部 severity 为 null 时不能返回 0"


@pytest.mark.parametrize("fmt", ["md", "json"])
def test_runtime_dependent_entry_appears_in_both_outputs(fmt):
    """`data/README.md` §4.4 的硬要求：条目必须出现在 md 与 json 两种输出里。"""
    old = fixture_path("jsonschema", "r6-oneof-moved", "old", "jsonschema")
    new = fixture_path("jsonschema", "r6-oneof-moved", "new", "jsonschema")
    code, out, _ = run([old, new, "--format", fmt])
    assert code == 1
    assert "R6" in out
    assert "runtime-dependent" in out
    assert "静态必破" in out or "why_static_breaking" in out
