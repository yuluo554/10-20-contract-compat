# -*- coding: utf-8 -*-
"""README 指令面 → parser 的反射对账。

判据只做一件成本极低的事：把 README 里每个 ```bash 代码块内的 `compat ...` 命令行抽出来，
逐条喂给 `build_parser().parse_args()`；任何一条抛 `SystemExit(2)` 即红。

抓的是一类真实缺陷：**文档写着 `--show-kind=a,b`，而 parser 给了 `choices=(...)`** ——
三处文档都对，代码一处拦，没有任何门在对账"文档写的参数形态 parser 认不认"。

注意：README 的示例目前指向 M1–M5 才存在的 fixture 路径；本门**只验参数面**、不验文件存在，
因此现在也能跑（这是有意的：它不该随里程碑进度变红）。
"""

import os
import re

import pytest

from contractcompat.cli import build_parser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")

BLOCK = re.compile(r"```bash\n(.*?)```", re.DOTALL)
COMPAT_LINE = re.compile(r"^\s*compat\s+(.*)$")


def readme_commands():
    with open(README, "r", encoding="utf-8") as handle:
        text = handle.read()
    commands = []
    for block in BLOCK.findall(text):
        for line in block.splitlines():
            match = COMPAT_LINE.match(line)
            if match:
                commands.append(match.group(1).strip())
    return commands


def test_readme_exists_and_has_commands():
    assert os.path.isfile(README)
    commands = readme_commands()
    # 非空跑自证：README 里一条 compat 命令都抽不到时，本门什么也没证明
    assert len(commands) >= 3, "README 至少要有安装/version + 三条场景命令，实际抽到 %d" % len(commands)


@pytest.mark.parametrize("command", readme_commands())
def test_readme_command_is_parseable(command):
    # 剥掉 shell 行内注释（示例里的 `# 砸老消费者` 是给人看的，不是参数）
    cleaned = command.split("  #")[0].strip()
    argv = cleaned.split()
    if argv and argv[0] == "compat":
        argv = argv[1:]
    try:
        build_parser().parse_args(argv)
    except SystemExit as exit_request:
        # `--version` / `--help` 正常退出也是 SystemExit(0)：只有非 0 才是"文档与 parser 不一致"
        if exit_request.code not in (0, None):
            pytest.fail("README 命令被 parser 拒绝（exit %s）：compat %s" % (exit_request.code, command))


def test_readme_documents_exit_codes():
    with open(README, "r", encoding="utf-8") as handle:
        text = handle.read()
    for code in ("0", "1", "2", "3"):
        assert "| %s |" % code in text, "README 退出码表缺 %s" % code


def test_readme_version_line_matches_package():
    """版本在 README 与代码里必须一致（M6 的"四处一致"之一；这里先锁前两处）。"""
    from contractcompat import __version__

    with open(README, "r", encoding="utf-8") as handle:
        text = handle.read()
    assert __version__ in text


#: README 里出现的 fixture 路径（`data/fixtures/...`）。M1 之后它们必须**真的存在**：
#: 文档写了一个不存在的示例路径，读者照抄就报"文件不存在"，而参数面反射门看不出来。
FIXTURE_PATH = re.compile(r"(data/fixtures/[\w./-]+\.(?:pb|avsc|json))")


def test_readme_fixture_paths_exist():
    """M1 承诺：README 三条场景里点名的 fixture 必须有实物。"""
    with open(README, "r", encoding="utf-8") as handle:
        text = handle.read()
    paths = sorted(set(FIXTURE_PATH.findall(text)))
    assert paths, "README 里一条 fixture 路径都没抽到（示例被删了？）"
    missing = [path for path in paths if not os.path.isfile(os.path.join(ROOT, path.replace("/", os.sep)))]
    assert missing == [], "README 点名但磁盘缺失: %s" % missing


#: README 里自述的测试数（"各 N 收集 / N 通过 / N 跳过"）。自述计数是**最容易腐烂的断言**：
#: 加一条参数化用例就会漂，而没有任何门在看它。这条门锁的是**算术关系**——
#: 收集数必须等于「通过数 + 跳过数」。只锁收集数的话，把通过数写成任意值仍然绿
#: （同类仓库踩过这个坑：门只锁收集数，README 写「各 999 通过」也照样过）。
SELF_REPORTED = re.compile(r"各\s*(\d+)\s*收集.*?(\d+)\s*通过.*?(\d+)\s*跳过")


def test_readme_self_reported_test_count_arithmetic():
    """README 自述的三个数必须自洽：收集 = 通过 + 跳过。"""
    with open(README, "r", encoding="utf-8") as handle:
        text = handle.read()
    matches = SELF_REPORTED.findall(text)
    assert matches, "README 里找不到自述测试数（『各 N 收集 / N 通过 / N 跳过』被改写了？）"
    for collected, passed, skipped in matches:
        collected, passed, skipped = int(collected), int(passed), int(skipped)
        assert collected == passed + skipped, (
            "README 自述的测试数不自洽：收集 %d ≠ 通过 %d + 跳过 %d" % (collected, passed, skipped)
        )


def test_readme_self_reported_count_matches_actual_collection():
    """自述收集数必须等于真实收集数（`--co -q` 的末行）。

    用**子进程**而不是 pytest 自己的 hook：hook 拿到的是"本文件加载后"的状态，
    而同一次收集里本文件自己的参数化也参与计数——那会让这条门自证循环。
    """
    import subprocess
    import sys

    process = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "pytest", "--co", "-q"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )
    output = process.stdout.decode("utf-8", "replace")
    match = re.search(r"(\d+) tests? collected", output)
    assert match, "收集数取不到（pytest --co -q 输出变了）：\n%s" % output[-2000:]
    actual = int(match.group(1))

    with open(README, "r", encoding="utf-8") as handle:
        text = handle.read()
    for collected, _, _ in SELF_REPORTED.findall(text):
        assert int(collected) == actual, "README 自述 %s 项，实测收集 %d 项" % (collected, actual)
