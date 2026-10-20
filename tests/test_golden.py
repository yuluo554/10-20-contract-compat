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


def cli_files():
    if not os.path.isdir(GOLDEN):
        return []
    return sorted(
        name
        for name in os.listdir(GOLDEN)
        if name.startswith("cli-") and name.endswith((".json", ".md"))
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


def expected_golden_count():
    """真值 = 生成器现算的配对数（不手填：新增一对夹具时这里自动跟上）。

    手工数字会随夹具增长而腐烂；而"生成器能配出几对"是磁盘上的事实。
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("gen_golden", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pairs, problems = module.discover_pairs()
    assert problems == [], problems
    return len(pairs)


def test_golden_directory_is_not_empty():
    """非空跑自证：一份 golden 都没有时，本文件的断言什么也没证明。"""
    expected = expected_golden_count()
    assert expected >= 28, "配对数量异常偏少（%d）：夹具被删了？" % expected
    assert len(golden_files()) == expected, (
        "应有 %d 份 IR golden（每对夹具一份），实际 %d" % (expected, len(golden_files()))
    )
    assert len(policy_files()) == expected, (
        "应有 %d 份 policy golden（与 IR 一一对应），实际 %d" % (expected, len(policy_files()))
    )
    # 端到端：每对夹具 2 份（md + json）+ 四态四联样例的另 3 档 × 2
    four_state_extra = len(gen_module().FOUR_STATE_ORDERS) - 1
    assert len(cli_files()) == 2 * (expected + four_state_extra), (
        "应有 %d 份端到端 golden，实际 %d" % (2 * (expected + four_state_extra), len(cli_files()))
    )


def gen_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("gen_golden", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expected_cli_names():
    """生成器现算的端到端 golden 名单（与磁盘双向对账用）。"""
    module = gen_module()
    pairs, problems = module.discover_pairs()
    assert problems == [], problems
    names = set()
    for directory, slug, _old, _new in pairs:
        for name, _extra, _codes in module._cli_jobs(directory, slug):
            names.add(name)
    return names


def test_cli_golden_names_match_disk_bidirectionally():
    """端到端 golden 名单与磁盘双向闭合：缺一份或多一份都红。"""
    assert sorted(expected_cli_names() - set(cli_files())) == [], "磁盘缺端到端 golden"
    assert sorted(set(cli_files()) - expected_cli_names()) == [], "磁盘多出无主的端到端 golden"


def test_four_state_quadruple_exists_and_differs():
    """四态四联：同一破例（删字段）四种发布顺序的 golden 都在，且 blast_radius 互不相同。"""
    quadruple = {}
    for name in sorted(cli_files()):
        if not name.startswith("cli-proto-r1-field-removed") or not name.endswith(".json"):
            continue
        with open(os.path.join(GOLDEN, name), "r", encoding="utf-8") as handle:
            payload = loads(handle.read())
        radii = tuple(row.get("blast_radius") for row in payload["findings"])
        quadruple[name] = (payload["notes"], radii)
    assert len(quadruple) == 4, sorted(quadruple)
    radii = set(value[1] for value in quadruple.values())
    assert len(radii) == 4, quadruple  # 四种顺序 → 四种不同的归因
    assert {"OLD_CONSUMER", "NEW_CONSUMER", "BOTH", "REPLAY_ONLY"} <= {
        radius for value in radii for radius in value
    }


def test_cli_golden_json_carries_severity_and_blast_radius():
    """端到端 golden 承载 M4 的 severity 与 M5 的 blast_radius；md 是它的渲染视图。"""
    jsons = [name for name in cli_files() if name.endswith(".json")]
    assert jsons
    severity_values = 0
    for name in jsons:
        with open(os.path.join(GOLDEN, name), "r", encoding="utf-8") as handle:
            payload = loads(handle.read())
        assert payload["findings"] or payload["summary"]["findings_total"] == 0, name
        for row in payload["findings"]:
            assert row["severity"] in ("breaking", "runtime-dependent", "non-breaking", None), (name, row)
            if row["severity"] is not None:
                assert row["blast_radius"] in ("OLD_CONSUMER", "NEW_CONSUMER", "BOTH", "REPLAY_ONLY"), (name, row)
                severity_values += 1
            else:
                assert row["blast_radius"] is None, (name, row)  # N/A 行不归因
    assert severity_values >= 1, "端到端 golden 里一条命中都没有：夹具被删了？"


def test_cli_golden_md_matches_json_same_pair():
    """同一对夹具的 md 与 json 是同一次 CLI 运行的两面：同 policy、同输入、同 findings 条数。"""
    jsons = set(name[:-5] for name in cli_files() if name.endswith(".json"))
    mds = set(name[:-3] for name in cli_files() if name.endswith(".md"))
    assert jsons == mds, "md / json 不成对: %s" % sorted(jsons ^ mds)
    for base in sorted(jsons):
        with open(os.path.join(GOLDEN, base + ".json"), "r", encoding="utf-8") as handle:
            payload = loads(handle.read())
        with open(os.path.join(GOLDEN, base + ".md"), "r", encoding="utf-8") as handle:
            text = handle.read()
        assert payload["policy"] in text, base
        assert "判定表（%d 条）" % payload["summary"]["findings_total"] in text, base


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
    for name in golden_files() + policy_files() + cli_files():
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
    """README 必须把七档矩阵登记成已生成，且盘上份数与配对数量一致。

    反向断言：不得再写"待 M3"——没生成却登记成"已生成"会被文件数抓；
    生成了却还写"待 M3"会让承诺-证据台账滞后。
    """
    with open(README, "r", encoding="utf-8") as handle:
        text = handle.read()
    assert "待 M3" not in text
    assert "policy-*.json" in text or "policy-<dir>-<slug>.json" in text
    assert "七档" in text
    assert len(policy_files()) == expected_golden_count()


def test_golden_is_consistent_across_two_generator_runs():
    """双跑一致：连续两次 `--check` 都过，说明生成过程本身是确定的。"""
    first = run_generator(GENERATOR, "--check")
    if first[0] == 3:
        pytest.skip("环境缺 protobuf")
    second = run_generator(GENERATOR, "--check")
    assert first[0] == 0 and second[0] == 0
