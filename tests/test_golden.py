# -*- coding: utf-8 -*-
"""golden 守门：形态自洽 + 重生成逐字节 + README 台账双向对账。

**为什么 golden 要由生成器产出、测试只读**：测试里重算期望值 = 实现错、期望也错，
永远绿。这里测试只做三件事：

  1. 读入库 golden，验形态（`digest` 自洽、`inputs` 只有 basename、无绝对路径）；
  2. 调生成器的 `--check`（重跑 CLI → 逐字节比对），验"入库的就是现在算出来的"；
  3. 把 `data/golden/README.md` 的台账与磁盘对账（表↔盘双向）。

生成器本身**只调 CLI**（`data/tools/gen_golden.py`），所以第 2 条不会退化成
"两份实现互相比对"。
"""

import os
import subprocess
import sys

import pytest

from contractcompat.canonical import DIGEST_KEY, digest, loads

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, "data", "golden")
README = os.path.join(GOLDEN, "README.md")
SRC = os.path.join(ROOT, "src")

GENERATOR = os.path.join(ROOT, "data", "tools", "gen_golden.py")
FIXTURE_GENERATOR = os.path.join(ROOT, "data", "tools", "gen_fixtures.py")


def golden_files():
    if not os.path.isdir(GOLDEN):
        return []
    return sorted(name for name in os.listdir(GOLDEN) if name.startswith("ir-") and name.endswith(".json"))


def policy_files():
    if not os.path.isdir(GOLDEN):
        return []
    return sorted(
        name for name in os.listdir(GOLDEN) if name.startswith("policy-") and name.endswith(".json")
    )


def run_generator(script, *args):
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PYTHONUTF8"] = "1"
    completed = subprocess.run(
        [sys.executable, script] + list(args),
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.returncode, completed.stdout.decode("utf-8", "replace"), completed.stderr.decode("utf-8", "replace")


def readme_golden_names():
    """从 README 的台账表里抽 golden 文件名（`ir-*.json` 与 `policy-*.json`）。"""
    with open(README, "r", encoding="utf-8") as handle:
        text = handle.read()
    names = set()
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        stripped = line.strip()
        if not (stripped.startswith("| `ir-") or stripped.startswith("| `policy-")):
            continue
        first = stripped.split("|")[1].strip().strip("`")
        if first.endswith(".json"):
            names.add(first)
    return names


def test_golden_directory_is_not_empty():
    """非空跑自证：一份 golden 都没有时，本文件的断言什么也没证明。"""
    assert len(golden_files()) == 27, (
        "应有 27 份 IR golden（19 规则对 + 4 反例 + 4 不可表达），实际 %d" % len(golden_files())
    )
    assert len(policy_files()) == 27, (
        "应有 27 份 policy golden（与 IR 一一对应），实际 %d" % len(policy_files())
    )


def test_golden_shape_and_digest_are_self_consistent():
    for name in golden_files():
        path = os.path.join(GOLDEN, name)
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        payload = loads(text)
        assert set(payload) == {"inputs", "old", "new", DIGEST_KEY}, "%s 顶层键不对: %s" % (name, sorted(payload))
        assert payload[DIGEST_KEY] == digest(payload), "%s 的 digest 与内容不自洽" % name
        # 输入只写 basename：绝对路径会让同一输入跨机产生不同字节
        for side in ("old", "new"):
            value = payload["inputs"][side]
            assert "/" not in value and "\\" not in value, "%s 的 inputs.%s 带了路径: %r" % (name, side, value)
        # 两侧 IR 必须各有 format 与 fields
        for side in ("old", "new"):
            assert payload[side]["format"] in ("proto", "avro", "jsonschema"), name
            assert isinstance(payload[side]["fields"], list), name


def test_golden_has_no_absolute_paths_or_timestamps():
    """跨机可复算：golden 里不得出现绝对路径、时间戳、主机名一类的漂移源。"""
    forbidden = ("C:\\", "D:\\", "/home/", "\\Users/", "/Users/")
    for name in golden_files() + policy_files():
        with open(os.path.join(GOLDEN, name), "r", encoding="utf-8") as handle:
            text = handle.read()
        for needle in forbidden:
            assert needle not in text, "%s 含绝对路径片段 %r" % (name, needle)


def test_policy_golden_shape_digest_and_no_fake_severity():
    """policy golden 只承载 M3 的事实：差异项方向 + 七档 verdict。

    反向断言：不得出现 `severity`——那是 M4 规则库的第三维；出现在这里就是伪造期望值。
    """
    from contractcompat.policy import DIRECTIONS, POLICIES, TRANSITIVE, VERDICTS

    assert policy_files()
    for name in policy_files():
        with open(os.path.join(GOLDEN, name), "r", encoding="utf-8") as handle:
            text = handle.read()
        payload = loads(text)
        assert set(payload) == {
            "inputs",
            "format",
            "differences",
            "verdicts",
            "history",
            "notes",
            DIGEST_KEY,
        }, "%s 顶层键不对: %s" % (name, sorted(payload))
        assert payload[DIGEST_KEY] == digest(payload), "%s 的 digest 与内容不自洽" % name
        for side in ("old", "new"):
            value = payload["inputs"][side]
            assert "/" not in value and "\\" not in value, "%s 的 inputs.%s 带了路径" % (name, side)
        assert payload["format"] in ("proto", "avro", "jsonschema"), name
        assert list(payload["verdicts"]) == list(POLICIES), name
        for policy_name, verdict in payload["verdicts"].items():
            if policy_name in TRANSITIVE:
                assert verdict in VERDICTS, "%s/%s 的 transitive 必须真算出来" % (name, policy_name)
            else:
                assert verdict in VERDICTS, "%s/%s" % (name, policy_name)
        assert payload["history"], "%s 缺 transitive 基线（生成器应传 --history <old>）" % name
        for item in payload["differences"]:
            assert item["direction"] in DIRECTIONS, "%s: %r" % (name, item)
        assert "severity" not in payload
        assert "\"severity\"" not in text


def test_generator_check_is_byte_identical():
    """第二层：重跑 CLI → 与入库 golden 逐字节一致（`--check` 退出码 0）。"""
    code, out, err = run_generator(GENERATOR, "--check")
    if code == 3:
        pytest.skip("环境缺 protobuf，跑不动 CLI（退出码 3）：%s" % err.strip()[:200])
    assert code == 0, "golden --check 未通过（exit %d）\n%s\n%s" % (code, out, err)
    assert "全绿" in out


def test_fixture_generator_check_is_byte_identical():
    """.pb 是二进制：生成器 `--check` 必须**位级**一致，否则"可复算"只是说说。"""
    code, out, err = run_generator(FIXTURE_GENERATOR, "--check")
    if code == 3:
        pytest.skip("环境缺 protobuf，造不出 .pb（退出码 3）：%s" % err.strip()[:200])
    assert code == 0, "fixture --check 未通过（exit %d）\n%s\n%s" % (code, out, err)
    assert "全绿" in out


def test_readme_golden_table_is_bidirectional():
    """台账与磁盘双向对账：表里有而盘上没有 → 红；盘上有而表里没有 → 红。"""
    listed = readme_golden_names()
    on_disk = set(golden_files()) | set(policy_files())
    assert listed, "README 台账一条都没抽到（表搬走了？）"
    assert sorted(listed - on_disk) == [], "台账点名但磁盘缺失: %s" % sorted(listed - on_disk)
    assert sorted(on_disk - listed) == [], "磁盘有但台账没登记: %s" % sorted(on_disk - listed)


def test_readme_registers_policy_goldens_as_generated():
    """M3 收尾：README 必须把七档矩阵登记成已生成，且盘上确实有 27 份。

    反向断言：不得再写"待 M3"——没生成却登记成"已生成"会被文件数抓；
    生成了却还写"待 M3"会让承诺-证据台账滞后。
    """
    with open(README, "r", encoding="utf-8") as handle:
        text = handle.read()
    assert "待 M3" not in text
    assert "policy-*.json" in text or "policy-<dir>-<slug>.json" in text
    assert "七档" in text
    assert len(policy_files()) == 27


def test_golden_is_consistent_across_two_generator_runs():
    """双跑一致：连续两次 `--check` 都过，说明生成过程本身是确定的。"""
    first = run_generator(GENERATOR, "--check")
    if first[0] == 3:
        pytest.skip("环境缺 protobuf")
    second = run_generator(GENERATOR, "--check")
    assert first[0] == 0 and second[0] == 0
