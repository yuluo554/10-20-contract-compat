#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""golden 生成器：**只调用 CLI（生产实现）**，不在这里重算任何判定。

为什么必须只调 CLI：如果生成器和生产实现各写一份逻辑，两份同错会让 golden 永远绿——
"比对两份预先算好的答案"是本项目明令禁止的形态（``plan/04`` §四）。

M1 的 golden 只落 **IR 形态**（归一后的两侧中间表示）。"七档 × 三格式的方向性矩阵"
golden 要等 M3 的 ``diff``/``judge`` 落地，在 ``data/golden/README.md`` 里如实标注
"待 M3 生成"——**不伪造期望值**。

用法::

    py data/tools/gen_golden.py            # 生成到 data/golden/
    py data/tools/gen_golden.py --check    # 重生成到临时目录 → 与入库 golden 逐字节比对

``--check`` 退出码：0 一致 / 1 有漂移 / 3 环境跑不动 CLI（缺 protobuf 等）。
"""

from __future__ import absolute_import

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURES = os.path.join(ROOT, "data", "fixtures")
GOLDEN = os.path.join(ROOT, "data", "golden")
SRC = os.path.join(ROOT, "src")

#: 参与 golden 的目录（顺序固定：报告与报错都按这个顺序来，便于人读）
DIRECTORIES = ("proto", "avro", "jsonschema", "negatives")
#: 扩展名 → 该目录里被视为"schema 输入"的后缀（``.proto`` 是留档源文本，不参与）
INPUT_SUFFIXES = (".pb", ".avsc", ".json")


def _env():
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = SRC + (os.pathsep + existing if existing else "")
    env["PYTHONUTF8"] = "1"
    return env


def discover_pairs():
    """扫 ``data/fixtures``，返回 ``[(dir, slug, old_rel, new_rel)]``（确定性排序）。

    配对规则只有一条：同一目录下 ``<slug>-old<ext>`` 与 ``<slug>-new<ext>`` 同名同后缀。
    缺一侧就**报错退出**而不是跳过——"少了一半输入"必须显眼，不能被当成"这个用例不存在"。
    """
    pairs = []
    problems = []
    for directory in DIRECTORIES:
        base = os.path.join(FIXTURES, directory)
        if not os.path.isdir(base):
            problems.append("缺目录: data/fixtures/%s" % directory)
            continue
        found = {}
        for name in sorted(os.listdir(base)):
            stem, suffix = os.path.splitext(name)
            if suffix.lower() not in INPUT_SUFFIXES:
                continue
            for side in ("old", "new"):
                marker = "-" + side
                if stem.endswith(marker):
                    slug = stem[: -len(marker)]
                    found.setdefault(slug, {})[side] = (suffix.lower(), name)
                    break
        for slug in sorted(found):
            sides = found[slug]
            old = sides.get("old")
            new = sides.get("new")
            if not old or not new:
                problems.append(
                    "%s/%s 只有一侧（old=%s new=%s）" % (directory, slug, bool(old), bool(new))
                )
                continue
            if old[0] != new[0]:
                problems.append("%s/%s 两侧后缀不同（%s vs %s）" % (directory, slug, old[0], new[0]))
                continue
            pairs.append(
                (
                    directory,
                    slug,
                    "data/fixtures/%s/%s" % (directory, old[1]),
                    "data/fixtures/%s/%s" % (directory, new[1]),
                )
            )
    return pairs, problems


def golden_name(directory, slug):
    return "ir-%s-%s.json" % (directory, slug)


def _run_cli(old_rel, new_rel):
    """调用**生产 CLI**产出规范 IR JSON；返回 ``(exit_code, stdout_bytes, stderr_text)``。"""
    command = [
        sys.executable,
        "-m",
        "contractcompat.cli",
        old_rel,
        new_rel,
        "--emit-ir",
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return (
        completed.returncode,
        completed.stdout,
        completed.stderr.decode("utf-8", "replace"),
    )


def generate_into(target_dir, only=None):
    """把每对 fixture 的 IR golden 写进 ``target_dir``；返回 ``(written, failures)``。"""
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir)
    pairs, problems = discover_pairs()
    if problems:
        return [], problems
    written = []
    failures = []
    for directory, slug, old_rel, new_rel in pairs:
        if only and only not in slug:
            continue
        code, stdout, stderr = _run_cli(old_rel, new_rel)
        if code != 0:
            failures.append(
                "%s/%s 的 CLI 退出码 %d（不是 0）：%s" % (directory, slug, code, stderr.strip()[:200])
            )
            continue
        if not stdout:
            failures.append("%s/%s 的 CLI 没有输出" % (directory, slug))
            continue
        path = os.path.join(target_dir, golden_name(directory, slug))
        with open(path, "wb") as handle:
            handle.write(stdout)
        written.append(golden_name(directory, slug))
    return written, failures


def run_generate(only=None):
    written, failures = generate_into(GOLDEN, only=only)
    if failures:
        sys.stderr.write("golden 生成失败 %d 处：\n" % len(failures))
        for item in failures[:20]:
            sys.stderr.write("  " + item + "\n")
        return 3
    keep = os.path.join(GOLDEN, ".gitkeep")
    if os.path.isfile(keep):
        os.remove(keep)
    sys.stdout.write("已写入 %d 份 IR golden 到 data/golden/\n" % len(written))
    return 0


def run_check(only=None):
    temp_dir = tempfile.mkdtemp(prefix="cc-golden-")
    try:
        written, failures = generate_into(temp_dir, only=only)
        if failures:
            sys.stderr.write("golden --check 无法生成 %d 处（环境问题，不是漂移）：\n" % len(failures))
            for item in failures[:20]:
                sys.stderr.write("  " + item + "\n")
            return 3

        expected = set(written)
        on_disk = set()
        if os.path.isdir(GOLDEN):
            for name in sorted(os.listdir(GOLDEN)):
                if name.startswith("ir-") and name.endswith(".json"):
                    if only and only not in name:
                        continue
                    on_disk.add(name)

        problems = []
        for name in sorted(expected & on_disk):
            with open(os.path.join(temp_dir, name), "rb") as handle:
                fresh = handle.read()
            with open(os.path.join(GOLDEN, name), "rb") as handle:
                frozen = handle.read()
            if fresh != frozen:
                problems.append("字节不一致: %s（重生成 %d B / 入库 %d B）" % (name, len(fresh), len(frozen)))
        for name in sorted(expected - on_disk):
            problems.append("入库缺 golden: %s" % name)
        for name in sorted(on_disk - expected):
            problems.append("多出无对应 fixture 的 golden: %s" % name)

        if problems:
            sys.stdout.write("golden --check: %d 处漂移\n" % len(problems))
            for item in problems[:40]:
                sys.stdout.write("  " + item + "\n")
            if len(problems) > 40:
                sys.stdout.write("  ……（其余 %d 条略）\n" % (len(problems) - 40))
            return 1
        sys.stdout.write("golden --check: 全绿（%d 份 golden 逐字节一致）\n" % len(expected))
        return 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="IR golden 生成器（只调用 CLI，不自己实现判定）")
    parser.add_argument("--check", action="store_true", help="重生成到临时目录并与入库 golden 逐字节比对")
    parser.add_argument("--only", default=None, help="只处理 slug 含该子串的用例")
    args = parser.parse_args(argv)
    if args.check:
        return run_check(args.only)
    return run_generate(args.only)


if __name__ == "__main__":
    sys.exit(main())
