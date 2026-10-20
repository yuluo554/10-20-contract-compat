# -*- coding: utf-8 -*-
"""CLI 参数面 + 退出码矩阵（0/1/2/3 的路径在 M0 就要真跑）。

M0 的判定核还没实现，所以"能出 0/1"的路径靠 **report.build + _exit_code** 直接验，
"2/3"的路径走 CLI 真入口。这样退出码契约现在就有证据，不必等到 M5。

**不用 `pytest.raises(SystemExit)` 兜 argparse**：`main()` 已把 `SystemExit` 转成返回码，
测试断言的是"用户会看到的退出码"，不是内部抛了什么。
"""

import io
import json
import os

import pytest

from contractcompat import __version__, report
from contractcompat.canonical import DIGEST_KEY, digest, dumps, loads
from contractcompat.cli import _assemble_report, _exit_code, build_parser, main
from contractcompat.parsers import parse as parse_schema
from contractcompat.report import build

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNSUPPORTED_FIXTURE = os.path.join(
    ROOT, "data", "fixtures", "jsonschema", "ir-unsupported-patternproperties-new.json"
)


def run(argv, tmp_path=None):
    stdout, stderr = io.StringIO(), io.StringIO()
    code = main(argv, stdout=stdout, stderr=stderr)
    return code, stdout.getvalue(), stderr.getvalue()


def write_avro(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


# ── 参数面 ────────────────────────────────────────────────────────────────


def test_help_exits_zero():
    code, out, _ = run(["--help"])
    assert code == 0
    assert "退出码" in out
    assert "--explain-mapping" in out


def test_version_prints_version():
    code, out, _ = run(["--version"])
    assert code == 0
    assert __version__ in out
    assert "compat" in out


def test_parser_accepts_all_documented_flags():
    parser = build_parser()
    args = parser.parse_args(
        [
            "old.avsc",
            "new.avsc",
            "--policy",
            "full-transitive",
            "--format",
            "json",
            "--deploy-order",
            "consumers-first",
            "--history",
            "v1.avsc",
            "--explain-mapping",
            "--require-complete-ir",
            "--ignore-runtime-dependent",
        ]
    )
    assert args.policy == "full-transitive"
    assert args.output_format == "json"
    assert args.history == ["v1.avsc"]
    assert args.strict_runtime_dependent is False


def test_strict_runtime_dependent_is_on_by_default():
    args = build_parser().parse_args(["a.avsc", "b.avsc"])
    assert args.strict_runtime_dependent is True


def test_conflicting_runtime_flags_rejected():
    code, _, err = run(["a.avsc", "b.avsc", "--strict-runtime-dependent", "--ignore-runtime-dependent"])
    assert code == 2
    assert err


# ── 退出码 2：用法 / 输入错误 ───────────────────────────────────────────────


def test_missing_arguments_exit_two():
    code, _, err = run([])
    assert code == 2
    assert "缺少输入文件" in err


def test_unknown_policy_exit_two(tmp_path):
    old = write_avro(tmp_path, "a.avsc", {"type": "record", "name": "A", "fields": []})
    code, _, err = run([old, old, "--policy", "sideways"])
    assert code == 2
    assert "invalid choice" in err or "policy" in err


def test_transitive_without_history_exit_two(tmp_path):
    old = write_avro(tmp_path, "a.avsc", {"type": "record", "name": "A", "fields": []})
    code, _, err = run([old, old, "--policy", "backward-transitive"])
    assert code == 2
    assert "--history" in err


def test_nonexistent_input_exit_two(tmp_path):
    missing = str(tmp_path / "ghost.avsc")
    code, _, err = run([missing, missing])
    assert code == 2
    assert "不存在" in err


def test_broken_json_exit_two(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text('{"properties": ', encoding="utf-8")
    code, _, err = run([str(path), str(path)])
    assert code == 2


def test_verify_with_positional_args_is_contradictory(tmp_path):
    code, _, err = run(["a.avsc", "b.avsc", "--verify", "report.json"])
    assert code == 2
    assert "--verify" in err


# ── 退出码 3：环境 / 能力不满足 ─────────────────────────────────────────────


def test_proto_text_requires_protoc_exit_three(tmp_path):
    """`.proto` 文本输入且没有描述符 → 能力不足（3），不是"你写错了"（2）。"""
    path = tmp_path / "a.proto"
    path.write_text('syntax = "proto3";\nmessage A { string id = 1; }\n', encoding="utf-8")
    code, _, err = run([str(path), str(path)])
    assert code == 3
    assert "descriptor_set_out" in err


def test_avro_mapping_not_implemented_exit_three(tmp_path):
    """骨架期：解析体未实现时**必须退出 3**，绝不能返回 0（否则"没检查"被读成"检查通过"）。"""
    path = write_avro(tmp_path, "a.avsc", {"type": "record", "name": "A", "fields": []})
    code, _, err = run([str(path), str(path)])
    assert code == 3
    assert "尚未实现" in err or "M2" in err


# ── 退出码 0 / 1：由 summary 决定（不经解析器，直接验装配层）─────────────────


def finding(severity, rule_id="R1", path="6"):
    return {
        "rule_id": rule_id,
        "rule_name": "FIELD_REMOVED",
        "stable_path": path,
        "severity": severity,
        "direction": "NONE_OK",
    }


def test_exit_zero_when_no_breaking():
    report = build("backward", "a.avsc", "b.avsc", findings=[finding("non-breaking")])
    assert _exit_code(report, True) == 0


def test_exit_one_when_breaking():
    report = build("backward", "a.avsc", "b.avsc", findings=[finding("breaking")])
    assert _exit_code(report, True) == 1


def test_runtime_dependent_counts_by_default():
    report = build("backward", "a.avsc", "b.avsc", findings=[finding("runtime-dependent", "R4")])
    assert _exit_code(report, True) == 1


def test_ignore_runtime_dependent_only_changes_exit_code():
    """可关判定强度，**不可让条目消失**：报告里仍必须有一条 runtime-dependent。"""
    report = build("backward", "a.avsc", "b.avsc", findings=[finding("runtime-dependent", "R4")])
    assert _exit_code(report, False) == 0
    assert report["summary"]["runtime_dependent"] == 1
    assert report["findings"][0]["severity"] == "runtime-dependent"


def test_policy_none_is_always_compatible():
    report = build("none", "a.avsc", "b.avsc", findings=[finding("breaking")])
    assert _exit_code(report, True) == 0


# ── --verify ───────────────────────────────────────────────────────────────


def test_verify_passes_on_untampered_report(tmp_path):
    report = build("backward", "a.avsc", "b.avsc", findings=[finding("breaking")])
    path = tmp_path / "report.json"
    path.write_text(dumps(report), encoding="utf-8")
    code, out, _ = run(["--verify", str(path)])
    assert code == 0
    assert "一致" in out


def test_verify_detects_tamper_and_locates_field(tmp_path):
    report = build("backward", "a.avsc", "b.avsc", findings=[finding("breaking")])
    path = tmp_path / "report.json"
    path.write_text(dumps(report), encoding="utf-8")

    tampered = json.loads(path.read_text(encoding="utf-8"))
    tampered["findings"][0]["severity"] = "non-breaking"
    path.write_text(dumps(tampered), encoding="utf-8")

    code, _, err = run(["--verify", str(path)])
    assert code == 1
    assert "不一致" in err


def test_verify_reports_digest_path_when_only_digest_is_stale(tmp_path):
    """改内容但不重算 digest：定位必须指向 digest 那一项（并提示先看别的差异）。"""
    report = build("backward", "a.avsc", "b.avsc", findings=[finding("breaking")])
    report["findings"][0]["severity"] = "non-breaking"
    path = tmp_path / "report.json"
    path.write_text(dumps(report), encoding="utf-8")
    code, _, err = run(["--verify", str(path)])
    assert code == 1
    assert DIGEST_KEY in err


def test_verify_missing_report_exit_two(tmp_path):
    code, _, err = run(["--verify", str(tmp_path / "nope.json")])
    assert code == 2
    assert "不存在" in err


def test_verify_does_not_modify_target(tmp_path):
    report = build("backward", "a.avsc", "b.avsc", findings=[finding("breaking")])
    path = tmp_path / "report.json"
    path.write_text(dumps(report), encoding="utf-8")
    before = path.read_bytes()
    run(["--verify", str(path)])
    assert path.read_bytes() == before  # 校验不得写入（失败路径零副作用）


# ── 报告键面 ───────────────────────────────────────────────────────────────


def test_report_has_fixed_key_order_and_digest():
    report = build("backward", "a.avsc", "b.avsc", findings=[finding("breaking")])
    text = dumps(report)
    assert "\"tool\"" in text and "\"digest\"" in text
    assert report[DIGEST_KEY] == digest(report)
    body = dict((key, value) for key, value in report.items() if key != DIGEST_KEY)
    assert len(dumps(body)) > 0


def test_report_findings_are_sorted():
    first = finding("breaking", path="9")
    second = finding("breaking", path="2")
    report = build("backward", "a.avsc", "b.avsc", findings=[first, second])
    assert [row["stable_path"] for row in report["findings"]] == ["2", "9"]


def test_report_counts_are_consistent():
    report = build(
        "backward",
        "a.avsc",
        "b.avsc",
        findings=[finding("breaking", path="1"), finding("runtime-dependent", "R4", "2"), finding("non-breaking", "R7", "3")],
    )
    summary = report["summary"]
    assert summary["findings_total"] == 3
    assert summary["breaking"] + summary["runtime_dependent"] + summary["non_breaking"] == summary["findings_total"]


# ── IR 阶段：不可表达构造的「拒 + 报」与报告装配 ─────────────────────────────


def test_require_complete_ir_exits_three_and_names_each_construct():
    """`--require-complete-ir` 真跑到退出码 3，且**拒的同时就报**（不只报个数）。"""
    code, out, err = run([UNSUPPORTED_FIXTURE, UNSUPPORTED_FIXTURE, "--require-complete-ir"])
    assert code == 3
    assert "patternProperties" in err
    assert "/patternProperties" in err  # 指针要能直接拿去定位
    assert out == ""  # 失败路径零副作用：拒收时 stdout 一个字节都不写


def test_ir_stage_report_assembly_renders_unsupported():
    """报告装配走**判定阶段与 IR 阶段共用的那一条路径**，不可表达构造必须出现在两种输出里。

    判定核还没接上（M3），所以这里直接给装配函数 IR 侧的对象——它正是 `_run` 在
    普通路径上会传进去的同一个东西（`Unsupported` 序列）。
    """
    ir = parse_schema(UNSUPPORTED_FIXTURE)
    built = _assemble_report(
        "backward",
        "order-old.json",
        "order-new.json",
        unsupported=ir.ir_unsupported,
    )

    markdown = report.render(built, "md")
    assert "不可表达的构造（ir_unsupported）" in markdown
    for item in ir.ir_unsupported:
        assert item.construct in markdown
        assert item.json_pointer in markdown
        assert item.reason in markdown

    payload = loads(report.render(built, "json"))
    assert payload["summary"]["ir_unsupported"] == len(ir.ir_unsupported)
    assert [row["construct"] for row in payload["ir_unsupported"]] == ["patternProperties"]
    assert payload["ir_unsupported"][0]["json_pointer"] == "/patternProperties"
