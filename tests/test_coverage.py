# -*- coding: utf-8 -*-
"""M1 覆盖度门：21 格（7 规则 × 3 格式）+ 4 反例 + 4 不可表达构造，**由脚本计算并打印**。

判据全在 `tests/fixture_scan.py` 里现算（不读手填清单）。本文件只做断言与打印。

**为什么 N/A 也要断言**：`applies=false` 的格子不要求夹具，但如果磁盘上真放了一对，
说明"规则表说没这回事"和"数据里造了这回事"打架了——两边都错才会一致，
这正是"数据先行"最容易悄悄腐烂的地方。
"""

from contractcompat.rules import load_rule_table

import fixture_scan


def test_rule_fixture_filenames_are_consistent():
    _, problems = fixture_scan.scan_rule_fixtures()
    assert problems == []


def test_matrix_is_twenty_one_cells_and_fully_covered():
    """21/21：`applies=true` 的格子必须有 old+new 一对；`applies=false` 的格子必须没有。"""
    table = load_rule_table()
    found, problems = fixture_scan.scan_rule_fixtures()
    assert problems == []
    rows = fixture_scan.matrix_rows(found, table)
    assert len(rows) == 21

    missing = [(rule_id, fmt) for rule_id, fmt, status, _ in rows if status == "MISSING"]
    unexpected = [(rule_id, fmt) for rule_id, fmt, status, _ in rows if status == "UNEXPECTED"]
    assert missing == [], "缺 fixture 的格: %s" % (missing,)
    assert unexpected == [], "规则表标 N/A 但磁盘上有夹具（口径打架）: %s" % (unexpected,)

    text = fixture_scan.print_matrix(rows, fixture_scan.scan_negatives(), fixture_scan.scan_unsupported())
    assert "21 格登记 21/21" in text

    assert sum(1 for row in rows if row[2] == "covered") == 18
    assert sum(1 for row in rows if row[2] == "na") == 3


def test_coverage_counts_are_complete():
    """反例 4/4、不可表达构造 4/4——单列计数，不与 21 格混算。"""
    negatives = fixture_scan.scan_negatives()
    unsupported = fixture_scan.scan_unsupported()
    assert sorted(negatives) == sorted(fixture_scan.NEGATIVE_SLUGS)
    assert sorted(unsupported) == sorted(fixture_scan.UNSUPPORTED_SLUGS)
