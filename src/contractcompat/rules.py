# -*- coding: utf-8 -*-
"""破例规则库：加载 ``rules/rule-table.json``（数据）并求值。

**规则表是数据不是代码**：命中条件、severity 默认值、修复动作都在表里，
本模块只做"加载 + 结构校验 + 按表求值"。这样"每条规则三格式各有用例"可被机械核对，
且不会出现第二套口径散落在 if 里。

M0 骨架：``load_rule_table`` / ``validate_rule_table`` / ``rule_ids`` 已实现并被测试锁住；
``evaluate`` 的函数体留 M4。
"""

from __future__ import absolute_import

import json
import os

from .errors import UsageError
from .ir import FORMATS

__all__ = [
    "SEVERITIES",
    "EXPECTED_RULE_IDS",
    "default_rule_path",
    "load_rule_table",
    "validate_rule_table",
    "rule_ids",
    "evaluate",
]

SEVERITIES = ("breaking", "runtime-dependent", "non-breaking")

EXPECTED_RULE_IDS = ("R1", "R2", "R3", "R4", "R5", "R6", "R7")

#: 数据目录相对仓库根的约定位置；**不写绝对路径**（包安装后也能靠这一层推导）。
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def default_rule_path():
    """规则表路径：优先仓库内 ``rules/``（唯一可编辑副本）；安装后回落到包内镜像。

    环境变量 ``CONTRACTCOMPAT_RULES`` 可覆盖（测试与"改规则再跑"用），但**报告里不写这个路径**。
    顺序固定：env → 仓库根 `rules/` → 包内 `data/`（wheel 安装后唯一存在的那份）。
    """
    override = os.environ.get("CONTRACTCOMPAT_RULES")
    if override:
        return override
    repo_copy = os.path.join(_REPO_ROOT, "rules", "rule-table.json")
    if os.path.isfile(repo_copy):
        return repo_copy
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "rule-table.json")


def load_rule_table(path=None):
    path = path or default_rule_path()
    if not os.path.isfile(path):
        raise UsageError("规则表不存在: %s" % path)
    with open(path, "r", encoding="utf-8-sig") as handle:
        try:
            table = json.load(handle)
        except ValueError as error:
            raise UsageError("规则表不是合法 JSON: %s（%s）" % (path, error))
    validate_rule_table(table)
    return table


def validate_rule_table(table):
    """结构校验：7 条规则、每条 3 个格式槽位、severity 三值合法。

    这是"覆盖矩阵可机械核对"的前提——缺一条规则时这里先红，而不是等某条用例悄悄不过。
    """
    if not isinstance(table, dict) or not isinstance(table.get("rules"), list):
        raise UsageError("规则表结构非法：缺 rules 数组")
    seen = []
    for rule in table["rules"]:
        rule_id = rule.get("rule_id")
        seen.append(rule_id)
        if rule.get("default_severity") not in SEVERITIES:
            raise UsageError("%s 的 default_severity 非法: %r" % (rule_id, rule.get("default_severity")))
        formats = rule.get("formats") or {}
        for fmt in FORMATS:
            slot = formats.get(fmt)
            if not isinstance(slot, dict):
                raise UsageError("%s 缺 %s 槽位" % (rule_id, fmt))
            if slot.get("applies") and not slot.get("evidence"):
                raise UsageError("%s/%s 标 applies=true 但缺 evidence" % (rule_id, fmt))
            if not slot.get("applies") and not slot.get("reason"):
                raise UsageError("%s/%s 标 applies=false 但缺 reason（N/A 必须给理由）" % (rule_id, fmt))
    if tuple(seen) != EXPECTED_RULE_IDS:
        raise UsageError("规则集合必须是 %s，实际 %s" % (list(EXPECTED_RULE_IDS), seen))
    return table


def rule_ids(table):
    return tuple(rule["rule_id"] for rule in table["rules"])


def evaluate(differences, table=None):
    raise NotImplementedError("规则命中求值计划在 M4 落地；当前为 M0 骨架")
