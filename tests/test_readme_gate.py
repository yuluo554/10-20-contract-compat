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
