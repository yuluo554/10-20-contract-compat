# -*- coding: utf-8 -*-
"""fixture 语义门：每对夹具**真的演了它声称演的那件事**。

覆盖计数在 `test_coverage.py`；本文件管"数量对"之外的事：

  * 同一语义（删字段）三格式各一份且 slug 相同（红线①的可机械检查面）；
  * 4 条反例必须是完整配对，且**在 IR 上确实不是破例形态**（有 alias / 有 reserved）；
  * 4 条不可表达用例的 new 侧必须产出**非空** `ir_unsupported`；
  * 字段名只用中性占位（合成数据纪律）。
"""

import os

import pytest

from contractcompat.parsers import parse

import fixture_scan


def test_three_formats_share_one_semantic_fixture():
    """红线①：同一个"删字段"在三格式各一份，且 slug 完全相同。"""
    found, _ = fixture_scan.scan_rule_fixtures()
    for fmt in ("proto", "avro", "jsonschema"):
        assert fmt in found.get("R1", {}), "R1 缺 %s 夹具" % fmt
        assert fixture_scan.pair_count(found, "R1", fmt) == 1, "R1×%s 应当只有一对夹具" % fmt
    stems = set()
    for fmt in ("proto", "avro", "jsonschema"):
        for side in ("old", "new"):
            for path in found["R1"][fmt][side]:
                stems.add(os.path.splitext(os.path.basename(path))[0])
    assert stems == {"r1-field-removed-old", "r1-field-removed-new"}, stems


def test_r1_is_the_same_rule_across_formats():
    """三格式的"删字段"必须真的都是**少一个字段**——不是三份不同的事。"""
    found, _ = fixture_scan.scan_rule_fixtures()
    irs = {}
    for fmt in ("proto", "avro", "jsonschema"):
        old = parse(found["R1"][fmt]["old"][0])
        new = parse(found["R1"][fmt]["new"][0])
        irs[fmt] = (set(f.name for f in old.fields), set(f.name for f in new.fields))
    for fmt, (old_names, new_names) in irs.items():
        assert old_names - new_names == {"total_amount"}, "%s 删掉的字段不是 total_amount: %s" % (
            fmt, old_names - new_names)
        assert new_names - old_names == set(), "%s 的 new 侧不该新增字段: %s" % (fmt, new_names - old_names)


def test_four_negatives_are_complete_pairs():
    negatives = fixture_scan.scan_negatives()
    assert sorted(negatives) == sorted(fixture_scan.NEGATIVE_SLUGS)
    for slug, sides in negatives.items():
        assert sides.get("old") and sides.get("new"), "%s 缺一侧" % slug


def test_rename_negative_declares_alias_and_keeps_type():
    """反例②：改名带 `aliases` —— IR 必须带出别名，且类型没变（否则它演的是别的事）。"""
    sides = fixture_scan.scan_negatives()["rename-with-alias"]
    old = parse(sides["old"]).fields[0]
    new = parse(sides["new"]).fields[0]
    assert (old.name, new.name) == ("total_amount", "amount")
    assert list(new.aliases) == ["total_amount"]
    assert new.type == old.type


def test_union_negative_only_adds_a_branch():
    """反例①：union 只**新增**分支，原有分支一个不少（否则不是"加类型"）。"""
    sides = fixture_scan.scan_negatives()["union-add-type"]
    old = parse(sides["old"]).fields[1]
    new = parse(sides["new"]).fields[1]
    assert old.type == "union(null,long)"
    assert new.type == "union(null,long,string)"


def test_delete_reserved_negative_marks_number_reserved():
    """反例③：删掉的号必须真的进了 `reserved`，否则演的是普通删字段（R1）。"""
    sides = fixture_scan.scan_negatives()["delete-reserved"]
    old = parse(sides["old"])
    new = parse(sides["new"])
    assert [field.name for field in old.fields] == ["order_id", "total_amount"]
    assert [field.name for field in new.fields] == ["order_id"]
    assert 2 in new.reserved_numbers
    assert 2 not in old.reserved_numbers


def test_add_optional_negative_adds_property_outside_required():
    """反例④：加的 property 不能进 `required`——进了就变成 R3 而不是"加可选"。"""
    sides = fixture_scan.scan_negatives()["add-optional-property"]
    new = parse(sides["new"])
    fields = dict((field.name, field) for field in new.fields)
    assert fields["total_amount"].cardinality == "optional"
    assert new.meta["required"] == ["order_id"]


def test_four_unsupported_cases_are_complete_pairs():
    unsupported = fixture_scan.scan_unsupported()
    assert sorted(unsupported) == sorted(fixture_scan.UNSUPPORTED_SLUGS)
    for slug, sides in unsupported.items():
        assert sides.get("old") and sides.get("new"), "%s 缺一侧" % slug


@pytest.mark.parametrize("slug", fixture_scan.UNSUPPORTED_SLUGS)
def test_unsupported_fixture_yields_non_empty_ir_unsupported(slug):
    """不可表达构造必须**出现在 IR 里**（非空），不是被静默忽略。"""
    path = fixture_scan.scan_unsupported()[slug]["new"]
    ir = parse(path)
    assert ir.ir_unsupported, "%s 的 new 侧应产出 ir_unsupported，实际为空" % slug
    assert all(item.json_pointer for item in ir.ir_unsupported), [i.json_pointer for i in ir.ir_unsupported]


@pytest.mark.parametrize("slug", fixture_scan.UNSUPPORTED_SLUGS)
def test_unsupported_client_sees_the_expected_construct(slug):
    """逐个构造对号：登记的名字必须是该夹具真正引入的那个。"""
    expected = fixture_scan.UNSUPPORTED_CONSTRUCT_OF[slug]
    ir = parse(fixture_scan.scan_unsupported()[slug]["new"])
    constructs = [item.construct for item in ir.ir_unsupported]
    assert expected in constructs, "%s 应含 %s，实际 %s" % (slug, expected, constructs)


def test_recursive_ref_does_not_overflow_and_is_reported():
    """递归 `$ref` 不能栈溢出：必须**正常返回**并登记成 `recursive_ref`。"""
    ir = parse(fixture_scan.scan_unsupported()["recursive-ref"]["new"])
    constructs = [item.construct for item in ir.ir_unsupported]
    assert constructs.count("recursive_ref") >= 1
    # 指针相对文档根，能顺着指回去
    pointer = [i.json_pointer for i in ir.ir_unsupported if i.construct == "recursive_ref"][0]
    assert pointer.startswith("/") and pointer.endswith("$ref")


def test_old_side_of_unsupported_cases_is_clean():
    """对照组：不可表达用例的 old 侧不得也含构造，否则差异不是"引入了它"。"""
    for slug, sides in fixture_scan.scan_unsupported().items():
        old = parse(sides["old"])
        assert not old.ir_unsupported, "%s 的 old 侧不该有 ir_unsupported: %s" % (
            slug, [(i.construct, i.json_pointer) for i in old.ir_unsupported])


def test_fixture_names_are_neutral_placeholders():
    """合成数据纪律：字段名只用中性占位（`data/README.md` §三）。

    **用解析结果取字段名**，不用正则扫原文：正则会把 `"type"` / `"$ref"` 这类结构键
    当成字段名（实测踩到），那样这条门既抓不准也说不清。
    """
    allowed = {
        "Order", "Status", "order_id", "total_amount", "status", "payment",
        "card_token", "bank_ref", "amount", "root", "child", "Node",
        "STATUS_UNSPECIFIED", "PENDING", "PAID",
    }
    names = set()
    for directory in ("proto", "avro", "jsonschema", "negatives"):
        base = os.path.join(fixture_scan.FIXTURES, directory)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if not name.endswith((".pb", ".avsc", ".json")):
                continue
            ir = parse(os.path.join(base, name))
            if ir.name:
                names.add(ir.name)
            for field in ir.fields:
                names.add(field.name)
                for value in field.enum_values:
                    names.add(value.name)
    unexpected = sorted(word for word in names if word not in allowed)
    assert unexpected == [], "出现非中性占位名: %s" % unexpected
