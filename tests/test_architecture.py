# -*- coding: utf-8 -*-
"""分层与序列化守门（AST 级，不是字面 greps）。

三条约束写在 AGENTS.md 里，这里是它们的可证伪实现：
  ① 解析层不判定：`parsers/*` 不得 import `policy` / `rules` / `blast`
  ② 判定层不渲染：`policy.py` / `rules.py` 不得 import `report`
  ③ 序列化单点：全仓 `json.dumps(` 只允许出现在 `canonical.py`

**为什么用 AST 而不是文本 grep**：`import` 的写法有绝对/相对/`from X import Y`/动态导入四种，
纯文本会漏掉相对导入（`from .. import policy` 时 `node.module` 是 None，名字在 `names` 里）。
"""

import ast
import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ROOT = os.path.join(REPO_ROOT, "src", "contractcompat")

PARSER_FORBIDDEN = {"policy", "rules", "blast", "report"}
JUDGE_FORBIDDEN = {"report"}


def iter_python_files(*roots):
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [name for name in dirnames if name not in {"__pycache__", ".git"}]
            for name in sorted(filenames):
                if name.endswith(".py"):
                    yield os.path.join(dirpath, name)


def imported_names(path):
    """返回 `(是否绝对导入, 名字)` 的集合，覆盖四种 import 形态。"""
    with open(path, "r", encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=path)
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add((True, alias.name.split(".")[0], alias.name))
        elif isinstance(node, ast.ImportFrom):
            absolute = node.level == 0
            module = node.module or ""
            for alias in node.names:
                found.add((absolute, module.split(".")[0] if module else "", "%s.%s" % (module, alias.name)))
    return found


def test_layers_exist():
    """守门自己要有对象可扫（非空跑自证）：目录结构变了先在这里红。"""
    expected = [
        "cli.py",
        "canonical.py",
        "ir.py",
        "policy.py",
        "rules.py",
        "blast.py",
        "report.py",
        os.path.join("parsers", "__init__.py"),
        os.path.join("parsers", "proto.py"),
        os.path.join("parsers", "avro.py"),
        os.path.join("parsers", "jsonschema.py"),
    ]
    missing = [rel for rel in expected if not os.path.isfile(os.path.join(SRC_ROOT, rel))]
    assert missing == []


def test_parsers_do_not_import_judgement_modules():
    offenders = []
    parser_dir = os.path.join(SRC_ROOT, "parsers")
    for path in iter_python_files(parser_dir):
        for absolute, top, full in imported_names(path):
            candidates = {top, full.split(".")[-1]}
            hit = candidates & PARSER_FORBIDDEN
            if hit:
                offenders.append("%s -> %s" % (os.path.basename(path), full))
    assert offenders == []


@pytest.mark.parametrize("module", ["policy.py", "rules.py"])
def test_judgement_layer_does_not_import_report(module):
    path = os.path.join(SRC_ROOT, module)
    offenders = [full for _, top, full in imported_names(path) if top in JUDGE_FORBIDDEN or full in JUDGE_FORBIDDEN]
    assert offenders == []


def test_relative_import_forms_are_actually_detected():
    """阳性对照：守门必须能认出相对导入与 from-import 两种形态。

    没有这条对照，上面几条"0 命中"可能只是"没扫到"——"0 命中"与"扫了 0 个"输出相同。
    """
    sample = '''
from .. import policy
from contractcompat import blast
import contractcompat.rules
'''
    tree = ast.parse(sample)
    detected = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                detected.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module:
                detected.add(module.split(".")[0])
            for alias in node.names:
                detected.add(alias.name.split(".")[0])
    assert {"policy", "blast", "contractcompat"} <= detected


def test_json_dumps_only_in_canonical():
    """序列化单点：多个入口各写一份参数，迟早出现跨机漂移。

    扫描面 = `src/` 全部 `.py`；只允许 `canonical.py` 出现 `json.dumps(` 调用。
    """
    offenders = []
    for path in iter_python_files(os.path.join(REPO_ROOT, "src")):
        if os.path.basename(path) == "canonical.py":
            continue
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
        if "json.dumps(" in source:
            offenders.append(os.path.relpath(path, REPO_ROOT))
    assert offenders == []


def test_no_clock_or_host_reads_in_reporting_modules():
    """报告跨机可复算：时钟 / 主机名 / 用户名不得进报告层。"""
    forbidden = {"time", "datetime", "socket", "platform", "getpass"}
    for module in ["report.py", "canonical.py", "ir.py"]:
        path = os.path.join(SRC_ROOT, module)
        tops = {top for _, top, _ in imported_names(path)}
        assert not (tops & forbidden), "%s 引入了 %s" % (module, tops & forbidden)
