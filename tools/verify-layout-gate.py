#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""布局门的变异验证脚本（9 组）：故意弄坏一个必备件，门必须变红；还原后必须恢复全绿。

为什么要有这个脚本：**门跑了且绿** 不等于 **门里每条判据都被证伪过一次**。
一条断言只在"删掉被测对象仍绿"时才暴露自己是假门。

三条纪律（缺一条，"没红"就无法定性）：
  ① 替换前 assert 锚点存在（marker 没匹配上 = 静默 no-op，看起来像"门是假的"）；
  ② 替换后 assert 文件已变（字节真的变了）；
  ③ 还原后 assert 字节与原始完全一致（并清掉残留备份）。

用法：``py tools/verify-layout-gate.py``
退出码：0 = 9 组全红且还原后全绿；1 = 有变异没红（假门）；2 = 用法错误。
"""

from __future__ import print_function

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(ROOT, "tools", "check-sprint-layout.py")


def read(rel):
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8", newline="") as handle:
        return handle.read()


def write(rel, text):
    with open(os.path.join(ROOT, rel), "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def run_gate():
    """返回 (退出码, stdout+stderr)。**不继承父环境的中文编码坑**：文本模式按 UTF-8 解。"""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.run(
        [sys.executable, "-X", "utf8", GATE],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )
    return process.returncode, process.stdout.decode("utf-8", "replace")


def mutate(rel, transform):
    """对 ``rel`` 施加 ``transform``；返回还原函数。三条纪律在 apply / restore 里各断言一次。"""
    original = read(rel)
    mutated = transform(original)
    if mutated is None or mutated == original:
        raise AssertionError("变异没有改变 %s 的字节：marker 没匹配上（静默 no-op）" % rel)
    write(rel, mutated)

    def restore():
        write(rel, original)
        if read(rel) != original:
            raise AssertionError("还原 %s 失败（字节不一致）" % rel)

    return restore


def delete_file(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        raise AssertionError("要删的文件不存在: %s" % rel)
    with open(path, "rb") as handle:
        original = handle.read()
    os.remove(path)

    def restore():
        with open(path, "wb") as handle:
            handle.write(original)
        if not os.path.isfile(path):
            raise AssertionError("还原 %s 失败" % rel)

    return restore


MUTATIONS = []


def mutation(label, expect):
    def register(function):
        MUTATIONS.append((label, expect, function))
        return function

    return register


@mutation("M1 删 AGENTS.md", "LAYOUT.FILES")
def _m1():
    return delete_file("AGENTS.md")


@mutation("M2 把 M0 在一个副本里翻成 ⬜（跨副本不一致）", "LAYOUT.STATUS")
def _m2():
    """靶子必须是**已 ✅** 的里程碑：翻一个本来就 ⬜ 的，两侧都是 pending，永远造不出冲突。"""
    rel = "plan/05-里程碑.md"

    def transform(text):
        marker = "| M0 | 方法论装订"
        assert marker in text, "锚点缺失"
        lines = text.split("\n")
        replaced = False
        for index, line in enumerate(lines):
            if line.startswith(marker):
                assert "✅" in line, "M0 在 plan/05 里不是 ✅，靶子选错了"
                lines[index] = line.replace("✅ 已完成", "⬜ 未开始", 1)
                replaced = True
        assert replaced, "没找到 M0 行"
        return "\n".join(lines)

    return mutate(rel, transform)


@mutation("M3 把已 ✅ 的里程碑写回 plan/06 的缺口格", "LAYOUT.GAPS")
def _m3():
    """靶子由**表结构**定位，不写死某一行的文案。

    写死文案会在文档改字后变成"锚点缺失"（M1 就踩过：G5 描述改了一句，本组直接崩）。
    判据要的是"缺口行的关闭条件里出现已完成的里程碑"，所以取缺口表第一条数据行即可。
    """
    rel = "plan/06-交付对标.md"

    def transform(text):
        lines = text.split("\n")
        header = None
        for index, line in enumerate(lines):
            if line.startswith("|") and "缺口" in line:
                header = index
                break
        assert header is not None, "锚点缺失：plan/06 找不到含『缺口』表头的表"
        row = header + 2  # 跳过分隔行
        assert row < len(lines) and lines[row].startswith("|"), "缺口表没有数据行"
        assert "M0" not in lines[row], "选中的缺口行本来就提到 M0，变异证明不了判据"
        lines[row] = lines[row].rstrip().rstrip("|").rstrip() + "；M0 已落地 |"
        return "\n".join(lines)

    return mutate(rel, transform)


@mutation("M4 删一份 HANDOFF-M1", "LAYOUT.HANDOFFS")
def _m4():
    return delete_file("plan/HANDOFF-M1.md")


@mutation("M5 删 plan/00 顶部整行装订行", "LAYOUT.BINDING_HEAD")
def _m5():
    rel = "plan/00-README总览.md"

    def transform(text):
        lines = text.split("\n")
        kept = [line for line in lines if not line.startswith("> 方法论：`ai-tool-project-sprint`")]
        assert len(kept) == len(lines) - 1, "装订行锚点没匹配上"
        return "\n".join(kept)

    return mutate(rel, transform)


@mutation("M6 删 plan/02（计划套件缺一份）", "LAYOUT.FILES")
def _m6():
    return delete_file("plan/02-架构与技术选型.md")


@mutation("M7 抹掉 plan/04 的『真值纪律』字样（小节判据应失效）", "LAYOUT.SECTIONS")
def _m7():
    """靶子必须覆盖**全文**：该词在文档开头的导语里也出现，只改小节标题 = 没改到判据输入。"""
    rel = "plan/04-数据计划.md"

    def transform(text):
        assert text.count("真值纪律") >= 1, "锚点缺失"
        return text.replace("真值纪律", "数据纪律（改名后判据应失效）")

    return mutate(rel, transform)


@mutation("M8 在 AGENTS.md 里点名一个不存在的 tools 脚本", "LAYOUT.DOC_TOOLS")
def _m8():
    rel = "AGENTS.md"

    def transform(text):
        marker = "## 强制布局"
        assert marker in text, "锚点缺失"
        return text.replace(marker, "（发布门：`py tools/check-release.py`）\n\n" + marker, 1)

    return mutate(rel, transform)


@mutation("M9 删掉 plan/00 里的 CI run 号（CI_CLAIM 应判「声称实跑却无 run id」）", "LAYOUT.CI_CLAIM")
def _m9():
    """靶子必须落在**描述行**（首格不是 M<数字>），那才是 LAYOUT.CI_CLAIM 的扫描面。

    只删 run id、保留「已实跑」字样：判据若写成"未实跑才要求 run id"，本组永远造不出红。
    """
    rel = "plan/00-README总览.md"

    def transform(text):
        marker = "run `39457916512`"
        assert marker in text, "锚点缺失：plan/00 里找不到 CI run 号"
        mutated = text.replace(marker, "run「已脱敏」", 1)
        assert "已实跑" in mutated, "变异把『已实跑』也改掉了，证明不了 CI_CLAIM"
        return mutated

    return mutate(rel, transform)


def main(argv):
    if len(argv) > 1:
        sys.stderr.write("用法: py tools/verify-layout-gate.py\n")
        return 2

    baseline_code, baseline_output = run_gate()
    if baseline_code != 0:
        sys.stdout.write("基线不是全绿，先修布局再跑变异验证：\n%s\n" % baseline_output)
        return 1

    failures = []
    for label, expected, make in MUTATIONS:
        restore = make()
        try:
            code, output = run_gate()
            if code == 0:
                failures.append("%s —— 门仍绿（假门）" % label)
                continue
            if expected not in output:
                failures.append(
                    "%s —— 门红了，但不是 %s 报的（可能是别的判据顺带红：无法证明该判据有效）" % (label, expected)
                )
                continue
            sys.stdout.write("PASS  %-44s → %s 报红\n" % (label, expected))
        finally:
            restore()

    final_code, final_output = run_gate()
    if final_code != 0:
        failures.append("还原后门没有恢复全绿：\n%s" % final_output)

    sys.stdout.write("=" * 64 + "\n")
    sys.stdout.write("变异组数: %d ｜ 未达成: %d ｜ 还原后: %s\n" % (len(MUTATIONS), len(failures), "全绿" if final_code == 0 else "红"))
    for item in failures:
        sys.stdout.write("FAIL  %s\n" % item)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
