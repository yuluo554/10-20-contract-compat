#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""布局门（方法论装订的第二件）：把"项目还长在方法论上"变成可跑红的断言。

判据一律落**仓库内文件**（不读 git 元数据——浅克隆 / 无 tag 的检出形态下 git 判据会翻转）。
退出码：0 全绿 / 1 有 FAIL / 2 用法错误。

判据清单（每一条都对应一组变异，见 plan/05 §三 与 plan/HANDOFF-M1.md §七）：
  LAYOUT.FILES        必备文件齐（计划套件 + data/README + README + AGENTS）
  LAYOUT.BINDING_HEAD plan/00 顶部装订行（三锚点同现：方法论名 / 布局门命令 / 日期）
  LAYOUT.SECTIONS     各文档含必需小节
  LAYOUT.DOC_TOOLS    文档点名的 tools/ 脚本必须有实物（非空跑自证）
  LAYOUT.STATUS       同一里程碑在 N 处副本上状态一致（真值不取自任何单一副本）
  LAYOUT.HANDOFFS     每个 ✅ 里程碑有下一棒交接单，且七节齐
  LAYOUT.GAPS         plan/06 缺口列不得仍挂着已 ✅ 的里程碑
  LAYOUT.RELEASE      最后一个里程碑 ✅ 后，发布留档两栏 + 覆盖对账小节

已知本条判据尚未被证伪：LAYOUT.RELEASE 在最后一个里程碑（M6）翻 ✅ 之前不适用，
因此它要到 M6 才能做变异验证——M6 收尾必须补"M6 删覆盖对账节 / M8 去掉 §二 的 tag 后标记"
两组变异。把这件事写在 HANDOFF 里，别让它静默。
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

checks = []
scanned = {"docs": 0, "handoffs": 0, "copies": 0, "doc_tools": 0, "gaps_cells": 0}


def add(check_id, ok, detail):
    checks.append((check_id, bool(ok), detail))


def read(rel):
    """返回文件文本；不存在返回 None（**永不抛**，由调用方判 FAIL）。"""
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return handle.read()


REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    "data/README.md",
    "plan/00-README总览.md",
    "plan/01-题目文档.md",
    "plan/02-架构与技术选型.md",
    "plan/03-模块详设.md",
    "plan/04-数据计划.md",
    "plan/05-里程碑.md",
    "plan/06-交付对标.md",
]

# 装订行：三个锚点**必须同现于同一行**。用前瞻（顺序无关）而不是 A.*B.*C：
# 写死顺序会把"日期在命令之前"这种合法写法判成缺（实测假红）。
BINDING_LINE = re.compile(
    r"^>(?=.*ai-tool-project-sprint)(?=.*check-sprint-layout)(?=.*20\d{2}-\d{2}-\d{2}).*$",
    re.MULTILINE,
)

REQUIRED_SECTIONS = {
    "plan/00-README总览.md": ["文档索引", "决策记录", "承诺-证据台账", "里程碑"],
    "plan/01-题目文档.md": ["任务要求", "评分标准", "边界与非目标"],
    "plan/02-架构与技术选型.md": ["分层", "构建"],
    "plan/03-模块详设.md": ["模块详设", "测试点"],
    "plan/04-数据计划.md": ["数据清单", "真值纪律", "覆盖度"],
    "plan/05-里程碑.md": ["DoD", "已知未验证项", "风险预案"],
    "plan/06-交付对标.md": ["评分对标", "缺口", "风险登记"],
    "data/README.md": ["依据查证记录", "数值口径"],
}

# 交接单七节（顺序无关，超集合法：项目自定更细的格式不算违规）
HANDOFF_SECTIONS = [
    "当前进度",
    "当前事实",
    "待办",
    "K 编号",
    "环境坑",
    "DoD",
    "命令速查",
]

# 状态副本：同一里程碑在这几处的状态必须互相一致。
# plan/06 的缺口列是**第四个副本**（以"缺口是否已关闭"的形态承载状态），由 LAYOUT.GAPS 逐格核对。
STATUS_COPIES = [
    ("plan/00-README总览.md", "里程碑表"),
    ("plan/05-里程碑.md", "状态表"),
    ("README.md", "状态行"),
]

# 只认"状态行"：表格行且首格就是里程碑号（不扫自由文本——"未验证项保持 ⬜"这类句子会被误读）。
STATUS_LINE = re.compile(r"^\|\s*\*{0,2}M(\d+)\b")
PENDING_MARKERS = ["⬜", "🟡", "未开始", "未执行", "待执行", "待确认"]


def check_required_files():
    missing = [rel for rel in REQUIRED_FILES if not os.path.isfile(os.path.join(ROOT, rel.replace("/", os.sep)))]
    scanned["docs"] = len(REQUIRED_FILES) - len(missing)
    add(
        "LAYOUT.FILES",
        not missing,
        "缺: " + ",".join(missing) if missing else "%d 份齐备" % scanned["docs"],
    )


def check_binding_head():
    text = read("plan/00-README总览.md") or ""
    ok = bool(BINDING_LINE.search(text))
    add(
        "LAYOUT.BINDING_HEAD",
        ok,
        "plan/00 顶部有装订行（三锚点齐）"
        if ok
        else "plan/00 顶部缺装订行（需同行出现：方法论名 + 布局门命令 + 装订日期）",
    )


def check_sections():
    bad = []
    for rel, needles in REQUIRED_SECTIONS.items():
        text = read(rel)
        if text is None:
            continue  # 缺文件由 LAYOUT.FILES 报，这里不重复刷屏
        lack = [needle for needle in needles if needle not in text]
        if lack:
            bad.append("%s: %s" % (rel, "/".join(lack)))
    add(
        "LAYOUT.SECTIONS",
        not bad,
        "；".join(bad) if bad else "%d 份小节齐备" % len(REQUIRED_SECTIONS),
    )


DOC_TOOL = re.compile(r"(?<![\w/])(tools/[\w.-]+\.(?:py|mjs|js|sh|ps1))")


def check_documented_tools():
    """文档点名的工具必须有实物。

    判据只认"根目录 tools/ 的路径形态"，不读文档语义。
    前面的负向断言 `(?<![\\w/])` 是为了不把 `data/tools/gen_golden.py`（M1 交付物）
    误当成根目录脚本——`data/` 下的生成器不在本条扫描面内。
    """
    docs = ["AGENTS.md"]
    plan_dir = os.path.join(ROOT, "plan")
    if os.path.isdir(plan_dir):
        docs += ["plan/" + name for name in sorted(os.listdir(plan_dir)) if name.endswith(".md")]
    referenced = set()
    for rel in docs:
        text = read(rel)
        if text is None:
            continue
        referenced.update(DOC_TOOL.findall(text))
    if not referenced:
        # 非空跑自证：一份文档都没提到 tools/ 时，这条判据什么也没证明
        add(
            "LAYOUT.DOC_TOOLS",
            False,
            "扫了 %d 份文档，0 处 tools/ 引用——判据是空的（阳性对照失败）" % len(docs),
        )
        return
    scanned["doc_tools"] = len(referenced)
    missing = sorted(rel for rel in referenced if not os.path.isfile(os.path.join(ROOT, rel)))
    add(
        "LAYOUT.DOC_TOOLS",
        not missing,
        "文档点名但不存在的工具: " + ",".join(missing)
        if missing
        else "%d 个文档点名的 tools/ 脚本全部在位" % len(referenced),
    )


def collect_states():
    """逐副本采集 `{k: set(done|pending)}`。真值不取自任何一个副本。"""
    states = {}
    for rel, kind in STATUS_COPIES:
        text = read(rel)
        if text is None:
            continue
        scanned["copies"] += 1
        for line in text.splitlines():
            match = STATUS_LINE.match(line)
            if not match:
                continue
            pending = any(marker in line for marker in PENDING_MARKERS)
            states.setdefault(int(match.group(1)), set()).add("pending" if pending else "done")
    return states


def check_status_agreement(states):
    conflicts = []
    for key in sorted(states):
        if len(states[key]) > 1:
            conflicts.append("M%d 在副本间状态不一致（%s）" % (key, " vs ".join(sorted(states[key]))))
    add(
        "LAYOUT.STATUS",
        not conflicts,
        "；".join(conflicts)
        if conflicts
        else "%d 处状态副本 × %d 个里程碑 状态全一致" % (scanned["copies"], len(states)),
    )


def check_handoffs(done, planned_last):
    """每个 ✅ 的里程碑必须留下"下一棒"交接单；最后一个里程碑（收尾棒）写自身那一份。"""
    problems = []
    for key in sorted(done):
        target = key if key == planned_last else key + 1
        rel = "plan/HANDOFF-M%d.md" % target
        text = read(rel)
        if text is None:
            problems.append("%s(缺)" % rel)
            continue
        scanned["handoffs"] += 1
        lack = [needle for needle in HANDOFF_SECTIONS if needle not in text]
        if lack:
            problems.append("%s(缺节: %s)" % (rel, "/".join(lack)))
    add(
        "LAYOUT.HANDOFFS",
        not problems,
        "；".join(problems)
        if problems
        else "%d 份交接单齐（七节）" % scanned["handoffs"],
    )


PATHISH = re.compile(r"`[^`]*`|[\w\-./]+\.md")


def check_stale_gaps(done):
    """plan/06 的缺口列是状态的第四个副本。

    按表头定位列号再取单元格（不是"行里含『缺口』二字"）；扫描面 = 表头之后到**第一张表结束**
    （空行或非表格行），不扫到文件末尾——否则后面的风险表会被误判（已知假门形态⑦）。

    匹配前先剥掉行内代码与 `*.md` 路径：文件名里的 `M6` 是标识符，状态里的 `M6` 才是里程碑引用
    （已知假门形态⑥/⑧）。
    """
    lines = (read("plan/06-交付对标.md") or "").splitlines()
    header_index = None
    for index, line in enumerate(lines):
        if line.startswith("|") and "缺口" in line:
            header_index = index
            break
    if header_index is None:
        add("LAYOUT.GAPS", False, "plan/06 找不到含『缺口』表头的表（判据表搬走了？）")
        return
    cells_in_header = [cell for cell in lines[header_index].split("|")]
    column = len(cells_in_header) - 2  # 最后一个有效列（去掉首尾空段）
    stale = []
    for line in lines[header_index + 2:]:
        if not line.startswith("|"):
            break  # 扫描面到此为止（表结束）
        cells = line.split("|")
        cell = cells[column] if column < len(cells) else ""
        scanned["gaps_cells"] += 1
        cleaned = PATHISH.sub(" ", cell)
        for key in done:
            if re.search(r"(^|[^0-9A-Za-z])M%d([^0-9]|$)" % key, cleaned):
                stale.append("缺口列仍提已完成的 M%d: %s" % (key, cell.strip()))
    # 第四个状态副本也计入覆盖量：缺口表不存在时上面已 FAIL，这里保证下界能抓住"副本被删"
    scanned["copies"] += 1
    add(
        "LAYOUT.GAPS",
        not stale,
        "；".join(stale) if stale else "缺口列 %d 格无已 ✅ 里程碑" % scanned["gaps_cells"],
    )


def check_release_doc(done, planned_last):
    """最后一个里程碑 ✅ 之后，发布留档必须两栏齐 + 覆盖对账小节。"""
    if planned_last is None or planned_last not in done:
        add("LAYOUT.RELEASE", True, "最后一个里程碑（M%s）未 ✅，本条判据在本轮不适用" % planned_last)
        return
    rel = "plan/RELEASE-M%d.md" % planned_last
    wrapup_rel = "plan/WRAPUP-M%d.md" % planned_last
    release = read(rel)
    wrapup = read(wrapup_rel)
    if release is None and wrapup is None:
        add("LAYOUT.RELEASE", False, "缺 %s 或 %s" % (rel, wrapup_rel))
        return
    if release is None:
        add("LAYOUT.RELEASE", True, "WRAPUP 形态（%s）" % wrapup_rel)
        return
    columns = bool(re.search(r"^##\s*一、tag 前事实", release, re.MULTILINE)) and bool(
        re.search(r"^##\s*二、tag 后追加", release, re.MULTILINE)
    )
    coverage = bool(re.search(r"^#{2,3}.*覆盖对账", release, re.MULTILINE))
    rows = len(re.findall(r"^\|.*(?:实现|不适用|待首推).*\|$", release, re.MULTILINE))
    add(
        "LAYOUT.RELEASE",
        columns and coverage and rows >= 3,
        "两栏:%s 覆盖对账小节:%s 三态行数:%d" % (columns, coverage, rows),
    )


def run(name, function, *args):
    """永不崩：被检查对象缺失 / 形态异常时记一条 FAIL 并继续（否则 rc=1 却一条结论都没跑完）。"""
    try:
        return function(*args)
    except Exception as error:  # noqa: BLE001 - 门的职责是报红，不是抛栈
        add(name, False, "检查抛异常: %s: %s" % (type(error).__name__, error))
        return None


def main(argv):
    if len(argv) > 1:
        sys.stderr.write("用法: py tools/check-sprint-layout.py\n")
        return 2

    run("LAYOUT.FILES", check_required_files)
    run("LAYOUT.BINDING_HEAD", check_binding_head)
    run("LAYOUT.SECTIONS", check_sections)
    run("LAYOUT.DOC_TOOLS", check_documented_tools)

    states = run("LAYOUT.STATUS", collect_states) or {}
    done = set(key for key, value in states.items() if "done" in value)
    planned_last = max(states) if states else None

    run("LAYOUT.STATUS", check_status_agreement, states)
    run("LAYOUT.HANDOFFS", check_handoffs, done, planned_last)
    run("LAYOUT.GAPS", check_stale_gaps, done)
    run("LAYOUT.RELEASE", check_release_doc, done, planned_last)

    failed = [item for item in checks if not item[1]]
    sys.stdout.write("布局门（方法论装订） · 判据只落仓库内文件\n")
    sys.stdout.write("=" * 56 + "\n")
    for check_id, ok, detail in checks:
        sys.stdout.write("%s  %s  %s\n" % ("PASS" if ok else "FAIL", check_id, detail))
    sys.stdout.write("=" * 56 + "\n")
    sys.stdout.write(
        "这轮扫到：必备文档 %d / 交接单 %d / 状态副本 %d / 文档点名的 tools 脚本 %d / 缺口格 %d\n"
        % (
            scanned["docs"],
            scanned["handoffs"],
            scanned["copies"],
            scanned["doc_tools"],
            scanned["gaps_cells"],
        )
    )
    sys.stdout.write("结论: %s\n" % ("全绿" if not failed else "%d 项 FAIL" % len(failed)))
    return 0 if not failed else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # 控制台编码不含 emoji 时不至于崩
        except Exception:
            pass
    sys.exit(main(sys.argv))
