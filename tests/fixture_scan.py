# -*- coding: utf-8 -*-
"""fixture 扫描与覆盖矩阵计算（**不是测试文件**，被 `test_coverage.py` / `test_fixtures.py` 共用）。

判据一律**从磁盘现算**，不读手填清单：手填的矩阵会随时间腐烂成假的，
而"文件名改了一个字母"这种事故只有现算才抓得住。
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "data", "fixtures")

#: 文件名 `<rule_id>-<slug>-<side>.<ext>`（rule_id 小写 r1..r7）
RULE_FILE = re.compile(r"^(r\d+)-(.+)-(old|new)\.(pb|avsc|json)$")
EXT_FORMAT = {".pb": "proto", ".avsc": "avro", ".json": "jsonschema"}

#: 反例清单（"看起来破、实际不破"四条，见 `data/README.md` §三）
NEGATIVE_SLUGS = ("union-add-type", "rename-with-alias", "delete-reserved", "add-optional-property")
#: 不可表达构造清单（`plan/04` §三）
UNSUPPORTED_SLUGS = ("patternproperties", "if-then-else", "recursive-ref", "dependent-schemas")

#: 各不可表达用例的 new 侧应出现的 `ir_unsupported[*].construct`
UNSUPPORTED_CONSTRUCT_OF = {
    "patternproperties": "patternProperties",
    "if-then-else": "if",
    "recursive-ref": "recursive_ref",
    "dependent-schemas": "dependentSchemas",
}


def scan_rule_fixtures():
    """返回 ``{"R1": {"proto": {"old": path, "new": path}, ...}}``——从磁盘现算。"""
    found = {}
    problems = []
    for directory in ("proto", "avro", "jsonschema"):
        base = os.path.join(FIXTURES, directory)
        if not os.path.isdir(base):
            problems.append("缺目录 data/fixtures/%s" % directory)
            continue
        for name in sorted(os.listdir(base)):
            match = RULE_FILE.match(name)
            if not match:
                continue
            rule, _slug, side, ext = match.groups()
            fmt = EXT_FORMAT["." + ext]
            if fmt != directory:
                problems.append("%s/%s 的扩展名是 %s，却放在 %s 目录" % (directory, name, fmt, directory))
            found.setdefault(rule.upper(), {}).setdefault(fmt, {})[side] = os.path.join(base, name)
    return found, problems


def _scan_side_pairs(base, prefix=""):
    """扫一个目录，按 ``<prefix><slug>-<side><ext>`` 配对。"""
    result = {}
    if not os.path.isdir(base):
        return result
    for name in sorted(os.listdir(base)):
        if prefix and not name.startswith(prefix):
            continue
        stem, ext = os.path.splitext(name)
        if ext.lower() not in EXT_FORMAT:
            continue
        body = stem[len(prefix):] if prefix else stem
        for side in ("old", "new"):
            if body.endswith("-" + side):
                result.setdefault(body[: -len(side) - 1], {})[side] = os.path.join(base, name)
                break
    return result


def scan_negatives():
    return _scan_side_pairs(os.path.join(FIXTURES, "negatives"))


def scan_unsupported():
    return _scan_side_pairs(os.path.join(FIXTURES, "jsonschema"), prefix="ir-unsupported-")


def matrix_rows(found, table):
    """逐格算 ``(rule_id, format, 状态, 证据)``；状态 ∈ {covered, na, MISSING, UNEXPECTED}。"""
    rows = []
    for rule in table["rules"]:
        rule_id = rule["rule_id"]
        for fmt in ("proto", "avro", "jsonschema"):
            applies = bool(rule["formats"][fmt].get("applies"))
            slot = found.get(rule_id, {}).get(fmt, {})
            complete = bool(slot.get("old") and slot.get("new"))
            if applies:
                rows.append((rule_id, fmt, "covered" if complete else "MISSING", rule["name"]))
            else:
                rows.append(
                    (rule_id, fmt, "na" if not complete else "UNEXPECTED",
                     rule["formats"][fmt].get("reason", ""))
                )
    return rows


MARK = {"covered": "✔", "na": "N/A", "MISSING": "✘", "UNEXPECTED": "!"}


def print_matrix(rows, negatives, unsupported):
    """把矩阵打印到标准输出（`-s` 可见）；返回同一段文本，便于断言。"""
    lines = ["", "M1 覆盖矩阵（7 规则 × 3 格式 = 21 格；N/A 是结论，不是缺格）", ""]
    lines.append("| rule_id | rule | proto | avro | jsonschema |")
    lines.append("|---|---|---|---|---|")
    by_rule = {}
    for rule_id, fmt, status, evidence in rows:
        by_rule.setdefault(rule_id, {"name": evidence, "cells": {}})["cells"][fmt] = status
    for rule_id in sorted(by_rule):
        cells = by_rule[rule_id]["cells"]
        lines.append(
            "| %s | %s | %s | %s | %s |"
            % (rule_id, by_rule[rule_id]["name"],
               MARK[cells["proto"]], MARK[cells["avro"]], MARK[cells["jsonschema"]])
        )
    covered = sum(1 for row in rows if row[2] == "covered")
    na = sum(1 for row in rows if row[2] == "na")
    lines.append("")
    lines.append(
        "21 格登记 %d/21（%d 对夹具 + %d 格 N/A——N/A 是结论，不是缺格）；"
        "反例 %d/%d；不可表达构造 %d/%d"
        % (covered + na, covered, na,
           len(negatives), len(NEGATIVE_SLUGS),
           len(unsupported), len(UNSUPPORTED_SLUGS))
    )
    text = "\n".join(lines)
    print(text)
    return text
