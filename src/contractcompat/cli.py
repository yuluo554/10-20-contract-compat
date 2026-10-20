# -*- coding: utf-8 -*-
"""命令行入口：``compat <old> <new> [options]``。

退出码契约唯一定义在 ``data/README.md`` §4.5；本模块只做**异常 → 退出码**的映射：

    0  该 policy 下无 breaking 项
    1  有 breaking 项（含默认计入的 runtime-dependent）
    2  用法 / 输入错误
    3  环境或能力不满足

原则：**未实现的路径绝不返回 0**——返回 0 的空壳会让调用方把"没检查"读成"检查通过"。
"""

from __future__ import absolute_import

import argparse
import contextlib
import sys

from . import __version__
from .errors import ContractCompatError, UsageError

__all__ = ["build_parser", "main", "PROG"]

PROG = "compat"

POLICY_CHOICES = (
    "backward",
    "backward-transitive",
    "forward",
    "forward-transitive",
    "full",
    "full-transitive",
    "none",
)
FORMAT_CHOICES = ("md", "json")
DEPLOY_CHOICES = ("consumers-first", "producers-first", "simultaneous", "replay")

DESCRIPTION = (
    "跨格式契约兼容性判定器：把 Avro / Protobuf / JSON Schema 归一到同一套判定语汇，"
    "输出破例规则、稳定路径、砸的是老消费者还是新消费者、以及最小修复动作。"
)


def build_parser():
    """参数面 = 验收面：README 里每条命令都必须能被它解析（M6 有反射对账门）。"""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "退出码：0 = 无 breaking 项；1 = 有 breaking 项；"
            "2 = 用法/输入错误；3 = 环境或能力不满足。"
        ),
    )
    parser.add_argument("old", nargs="?", help="旧版 schema 文件（.avsc / .pb 描述符 / JSON Schema）")
    parser.add_argument("new", nargs="?", help="新版 schema 文件")
    parser.add_argument(
        "--policy",
        choices=POLICY_CHOICES,
        default="backward",
        help="兼容策略（七档，语义见 data/README.md §4.1；默认 backward）",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=FORMAT_CHOICES,
        default="md",
        help="输出格式：md（默认，渲染视图）或 json（规范形态，参与 digest）",
    )
    parser.add_argument(
        "--deploy-order",
        choices=DEPLOY_CHOICES,
        default=None,
        help="发布顺序；不给则 blast_radius 为 null 并在 notes 说明（不猜默认顺序）",
    )
    parser.add_argument(
        "--history",
        action="append",
        metavar="PATH",
        default=None,
        help="历史版本文件（可重复）；*-transitive 档必须给出",
    )
    parser.add_argument(
        "--explain-mapping",
        action="store_true",
        help="打印 buf 四档映射表（只表达最接近，不宣称等价）",
    )
    parser.add_argument(
        "--require-complete-ir",
        action="store_true",
        help="IR 存在不可表达构造时拒绝出结论（退出码 3）",
    )
    parser.add_argument(
        "--emit-ir",
        action="store_true",
        help="只输出两侧归一后的 IR（规范 JSON，含 digest），不做判定；golden 生成器用它取真值",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--strict-runtime-dependent",
        dest="strict_runtime_dependent",
        action="store_true",
        default=True,
        help="runtime-dependent 计入退出码 1（默认开）",
    )
    group.add_argument(
        "--ignore-runtime-dependent",
        dest="strict_runtime_dependent",
        action="store_false",
        help="只把 runtime-dependent 从退出码里摘出；输出条目一律保留",
    )
    parser.add_argument(
        "--verify",
        metavar="PATH",
        default=None,
        help="校验一份已生成的 JSON 报告（重算 digest 并定位被改字段）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%s %s" % (PROG, __version__),
        help="打印版本并退出",
    )
    return parser


def _write(text, stream):
    stream.write(text)
    if not text.endswith("\n"):
        stream.write("\n")


def _run(args, stdout, stderr):
    """真正的执行体；返回退出码。所有判定逻辑在 M2–M5 逐棒接上。"""
    from . import blast, parsers, policy, report, rules

    # ① 参数组合校验（退出码 2 的路径在 M0 就要真跑）
    if args.verify:
        if args.old or args.new:
            raise UsageError("--verify 与 <old> <new> 不能同时使用")
        ok, differences = report.verify_file(args.verify)
        if ok:
            _write("报告自洽：digest 与内容一致", stdout)
            return 0
        _write("报告不一致：定位到 %d 处" % len(differences), stderr)
        for item in differences:
            _write(
                "  %s: 期望 %r 实际 %r（%s）"
                % (item.get("json_path"), item.get("expected"), item.get("actual"), item.get("kind")),
                stderr,
            )
        return 1

    if not args.old or not args.new:
        raise UsageError("缺少输入文件：用法 compat <old> <new> [--policy ...]（--help 查看全部参数）")

    policy.resolve_policy(args.policy, args.history)
    blast.validate_deploy_order(args.deploy_order)

    # ② 解析（M2 起三格式都接上；未实现的路径仍会明确报"尚未实现"而不是返回 0）
    old_ir = _parse(parsers, args.old, args.require_complete_ir)
    new_ir = _parse(parsers, args.new, args.require_complete_ir)

    unsupported = list(old_ir.ir_unsupported) + [
        item for item in new_ir.ir_unsupported if item not in old_ir.ir_unsupported
    ]
    if args.require_complete_ir and unsupported:
        from .errors import CapabilityError

        # IR 阶段就拒：**拒的同时必须就报**——只写"N 处"会让用户无从下手，
        # 所以要逐条点名构造与指针（getsentry 的教训正是"未支持 = 静默忽略"）。
        raise CapabilityError(
            "--require-complete-ir：IR 含 %d 处不可表达构造，拒绝出结论\n%s"
            % (len(unsupported), _describe_unsupported(unsupported))
        )

    # ②′ 只出 IR（golden 生成器唯一入口）：不判定、不出 findings，故与 policy 无关
    if args.emit_ir:
        _write(_render_ir(old_ir, new_ir, args.old, args.new), stdout)
        return 0

    # ③ 判定 → 规则 → 归因 → 报告
    differences = policy.diff(old_ir, new_ir)
    verdict = policy.judge(differences, args.policy, args.history or ())
    table = rules.load_rule_table()
    findings = rules.evaluate(differences, table)
    findings, notes = blast.attribute(findings, args.deploy_order)

    mapping = policy.mapping_table() if args.explain_mapping else None
    built = _assemble_report(
        policy=args.policy,
        old_name=_display_name(args.old),
        new_name=_display_name(args.new),
        unsupported=unsupported,
        findings=findings,
        notes=notes,
        verdict=verdict,
        mapping=mapping,
    )
    _write(report.render(built, args.output_format), stdout)

    if args.explain_mapping:
        _write(_render_mapping(mapping), stdout)

    return _exit_code(built, args.strict_runtime_dependent)


def _parse(parsers, path, require_complete_ir):
    try:
        return parsers.parse(path, require_complete_ir=require_complete_ir)
    except NotImplementedError as error:
        from .errors import CapabilityError

        raise CapabilityError(str(error))


def _describe_unsupported(unsupported):
    """逐条点名不可表达构造：`construct @ pointer — reason`（**就报**，不只报个数）。"""
    return "\n".join(
        "  - `%s` @ `%s` — %s" % (item.construct, item.json_pointer, item.reason)
        for item in unsupported
    )


def _assemble_report(
    policy,
    old_name,
    new_name,
    unsupported=(),
    findings=(),
    notes=(),
    verdict="compatible",
    mapping=None,
):
    """装配报告对象（**判定阶段与 IR 阶段只用这一条路径**）。

    ``unsupported`` 直接收 IR 侧的 ``Unsupported`` 对象：由 ``report.build`` 统一成
    报告里的三键形态，本函数与渲染层都不做二次解释。M2 的判定核尚未接上，
    普通命令还走不到这里；但"不可表达构造必须出现在报告里"的落点就在本函数，
    所以它单独可测（见 ``tests/test_cli.py`` 的 IR 阶段装配用例）。
    """
    from . import report

    return report.build(
        policy=policy,
        old_name=old_name,
        new_name=new_name,
        findings=findings,
        notes=notes,
        ir_unsupported=unsupported,
        verdict=verdict,
        mapping=mapping,
    )


def _display_name(path):
    """报告里只写 basename——绝对路径会让 digest 跨机不可复算。"""
    normalized = path.replace("\\", "/")
    return normalized.rsplit("/", 1)[-1]


def _render_ir(old_ir, new_ir, old_path, new_path):
    """``--emit-ir`` 的唯一出口：规范 JSON + digest（经 ``canonical.dumps``，不自己序列化）。

    形态固定为 ``{old, new, inputs, digest}``：两侧 IR 各自完整，``inputs`` 只写 basename。
    这条产物是 M1 的 golden 输入面——**它是生产实现算出来的**，不是生成器自己算的。
    """
    from .canonical import DIGEST_KEY, digest
    from .report import to_json

    payload = {
        "inputs": {"old": _display_name(old_path), "new": _display_name(new_path)},
        "old": old_ir.to_json(),
        "new": new_ir.to_json(),
    }
    payload[DIGEST_KEY] = digest(payload)
    return to_json(payload)


def _render_mapping(mapping):
    lines = ["", "## buf 四档映射（只表达最接近，不宣称等价）", ""]
    lines.append("| 本题 policy | 最接近的 buf 档 | 关系说明 |")
    lines.append("|---|---|---|")
    for row in mapping["rows"]:
        lines.append("| `%s` | %s | %s |" % (row["policy"], row["buf_tier"], row["relation"]))
    lines.append("")
    lines.append(mapping["notes"])
    return "\n".join(lines)


def _exit_code(built, strict_runtime_dependent):
    """退出码只由 summary 的计数决定（不含任何渲染/格式因素）。"""
    summary = built.get("summary") or {}
    if built.get("policy") == "none":
        return 0
    if summary.get("breaking", 0) > 0:
        return 1
    if strict_runtime_dependent and summary.get("runtime_dependent", 0) > 0:
        return 1
    return 0


def main(argv=None, stdout=None, stderr=None):
    """控制台入口。捕获**我们自己的**异常并映射退出码；不吞其它异常（那会掩盖真 bug）。"""
    argv = list(sys.argv[1:] if argv is None else argv)
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    parser = build_parser()

    try:
        # argparse 的 --help / --version / 用法错误都直接写 sys.stdout/sys.stderr，
        # 这里把两条流临时指到调用方给的出口，测试才能断言"用户看到的那一句话"。
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            args = parser.parse_args(argv)
    except SystemExit as exit_request:  # argparse 对用法错误抛 SystemExit(2)
        return int(exit_request.code or 0)

    try:
        return int(_run(args, stdout, stderr))
    except ContractCompatError as error:
        _write("%s: %s" % (type(error).__name__, error), stderr)
        return int(error.exit_code)
    except NotImplementedError as error:
        _write("尚未实现: %s" % error, stderr)
        return 3
    except BrokenPipeError:  # 管道被下游关掉（`compat ... | head`）不是错误
        return 0


def _ensure_utf8_stdio():
    """按实际编码探针决定是否 reconfigure：中文控制台（cp936）保持不动。

    本机习惯 `py -X utf8` 会掩盖以 cp1252 为默认的 CI 管道缺口；这里只做"能修就修"，
    不强制——CP936 下用户已能正常看图，强行改反而破坏本地观感。
    """
    for stream in (sys.stdout, sys.stderr):
        encoding = (getattr(stream, "encoding", "") or "").lower()
        if encoding and not encoding.startswith(("utf", "cp936", "gbk", "gb18030")):
            try:
                stream.reconfigure(errors="replace")
            except (AttributeError, ValueError):
                pass


if __name__ == "__main__":
    _ensure_utf8_stdio()
    sys.exit(main())
