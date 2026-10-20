# -*- coding: utf-8 -*-
"""工作流文件守门：本地先解析，别等 GitHub 告诉你。

`name:` 里含裸 `: ` 会让 YAML 把第二个冒号当 mapping 分隔符 → 整份文件解析失败 →
GitHub 端 run 显示 failure 而 **jobs=0**（文件字节和 state 都正常）。这类失败排查成本极高，
所以推送前必须在本地 `yaml.safe_load` 并断言 job / step 数。
"""

import os

import pytest

yaml = pytest.importorskip("yaml", reason="workflow 守门需要 PyYAML（dev 环境已装）")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "ci.yml")


def load():
    assert os.path.isfile(WORKFLOW), "缺 CI 工作流文件"
    with open(WORKFLOW, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_workflow_parses():
    assert load() is not None


def test_single_job_with_expected_step_count():
    document = load()
    jobs = document.get("jobs") or {}
    assert list(jobs) == ["test"]
    steps = jobs["test"]["steps"]
    # 7 个显式步骤 + checkout + setup = 9；数字变了要同轮更新本条（防"顺手删掉一条门"）
    assert len(steps) == 9
    assert [step.get("name") for step in steps if step.get("name")] == [
        "Install (editable + dev extras)",
        "Sprint layout gate (methodology binding)",
        "Unit tests",
        "Fixture regenerate check (bit-level, .pb is binary)",
        "Golden regenerate check (byte-level, CLI-only generator)",
        "CLI smoke (console script)",
        "CLI smoke (module path, the other entry)",
    ]


def test_reproducibility_gates_are_wired_into_ci():
    """fixture / golden 的复算门必须在 CI 里**单独成步**。

    只放在 pytest 里不够：缺 protobuf 时测试会 skip，而 skip 与 pass 在日志里长得一样。
    """
    run_steps = [step.get("run", "") for step in load()["jobs"]["test"]["steps"]]
    assert any("gen_fixtures.py --check" in run for run in run_steps)
    assert any("gen_golden.py --check" in run for run in run_steps)


def test_layout_gate_is_wired_into_ci():
    """布局门只在开发机存在 = 等于没有（方法论装订第②件的硬要求）。"""
    run_steps = [step.get("run", "") for step in load()["jobs"]["test"]["steps"]]
    assert any("check-sprint-layout.py" in run for run in run_steps)


def test_both_cli_entry_points_are_smoked():
    """`python -m pkg` 与裸 `pkg` 是两条通路（sys.path 来源不同），只跑一条会漏安装面缺陷。"""
    run_steps = " ".join(step.get("run", "") for step in load()["jobs"]["test"]["steps"])
    assert "compat --version" in run_steps
    assert "python -m contractcompat.cli" in run_steps


def test_ci_sets_utf8_for_all_steps():
    """CI 的 `python -m pytest` 不是"我们敲的命令"，没有 `-X utf8`；靠 env 兜底。"""
    env = load()["jobs"]["test"].get("env") or {}
    assert env.get("PYTHONUTF8") == "1"


def test_matrix_covers_declared_python_floor():
    """`requires-python = ">=3.8"` 必须在矩阵里有一条 3.8 腿，否则底线声明无人验证。"""
    matrix = load()["jobs"]["test"]["strategy"]["matrix"]
    assert "3.8" in matrix["python-version"]
    assert "3.12" in matrix["python-version"]
