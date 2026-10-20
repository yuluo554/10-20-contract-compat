# -*- coding: utf-8 -*-
"""Avro 解析器单测（M2）：字段七项、enum 下标、union 顺序、alias、三态 default、退出码 2。

口径（`data/README.md` §4.3）：Avro 的稳定路径 = **字段名**，`number` / `json_pointer`
一律 `None`。这里逐项断言，而不是"看起来对"——R5/R6 在 Avro 下是 `N/A` 结论，
一旦有人为了"七项齐"给 Avro 编字段号，那两条 N/A 就会假命中（HANDOFF-M2 §二 #5）。
"""

import io
import json
import os

import pytest

from contractcompat.cli import main
from contractcompat.errors import SchemaParseError
from contractcompat.parsers import detect_format, parse
from contractcompat.parsers.avro import cardinality_of, normalize_type

import fixture_scan

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "data", "fixtures", "avro")


def fixture(name):
    return os.path.join(FIXTURES, name)


def write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    return str(path)


def run(argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    return main(argv, stdout=stdout, stderr=stderr), stdout.getvalue(), stderr.getvalue()


# ── 字段七项：名 / 号 / 类型 / 基数 / 默认 / enum 编号 / reserved ──────────────


def test_field_items_are_all_mapped():
    ir = parse(fixture("r1-field-removed-old.avsc"))
    assert ir.format == "avro"
    assert ir.name == "Order"
    assert [field.name for field in ir.fields] == ["order_id", "total_amount"]
    # 号与指针必须留 None：Avro 按名字解析，位置只是编码细节
    assert [field.number for field in ir.fields] == [None, None]
    assert [field.json_pointer for field in ir.fields] == [None, None]
    assert [field.stable_path() for field in ir.fields] == ["order_id", "total_amount"]
    assert [field.type for field in ir.fields] == ["string", "long"]
    # 基数：无 default 且不含 null 分支 → required；有 default → optional
    assert [field.cardinality for field in ir.fields] == ["required", "optional"]
    assert ir.fields[0].to_json()["default"] == {"present": False, "value": None}
    assert ir.fields[1].to_json()["default"] == {"present": True, "value": 0}
    assert [list(field.enum_values) for field in ir.fields] == [[], []]
    assert [list(field.aliases) for field in ir.fields] == [[], []]
    assert ir.reserved_numbers == () and ir.reserved_names == ()
    assert ir.meta["namespace"] == "example.invalid.contracts"
    assert ir.meta["field_count"] == 2
    assert ir.meta["record_aliases"] == []


def test_cardinality_three_way_mapping():
    assert cardinality_of("string", has_default=False) == "required"
    assert cardinality_of("string", has_default=True) == "optional"
    assert cardinality_of(["null", "string"], has_default=True) == "nullable"
    # null 分支优先于 default：nullable 是 R3 的证据形态，不能被 optional 盖掉
    assert cardinality_of(["null", "string"], has_default=False) == "nullable"


def test_default_is_three_state_on_real_documents():
    old = parse(fixture("r7-default-changed-old.avsc")).fields[1]
    new = parse(fixture("r7-default-changed-new.avsc")).fields[1]
    assert old.to_json()["default"] == {"present": True, "value": "PENDING"}
    assert new.to_json()["default"] == {"present": True, "value": "PAID"}


# ── enum ────────────────────────────────────────────────────────────────────


def test_enum_symbols_carry_index_as_number():
    """Avro 二进制编码里 enum 用符号下标，所以下标就是它的真编号（不是伪造字段号）。"""
    ir = parse(fixture("r4-enum-narrowed-old.avsc"))
    status = dict((field.name, field) for field in ir.fields)["status"]
    assert status.type == "Status"  # 具名类型，不是 "enum"
    assert [(value.name, value.number) for value in status.enum_values] == [
        ("STATUS_UNSPECIFIED", 0),
        ("PENDING", 1),
        ("PAID", 2),
    ]
    new_status = dict((field.name, field) for field in parse(fixture("r4-enum-narrowed-new.avsc")).fields)["status"]
    assert [value.name for value in new_status.enum_values] == ["STATUS_UNSPECIFIED", "PENDING"]


def test_named_type_reference_resolves(tmp_path):
    path = write(
        tmp_path,
        "named.avsc",
        {
            "type": "record",
            "name": "Order",
            "fields": [
                {"name": "status", "type": {"type": "enum", "name": "Status", "symbols": ["PENDING", "PAID"]}},
                {"name": "status_copy", "type": "Status"},
            ],
        },
    )
    ir = parse(path)
    by_name = dict((field.name, field) for field in ir.fields)
    assert by_name["status"].type == "Status"
    assert by_name["status_copy"].type == "Status"
    assert [(value.name, value.number) for value in by_name["status_copy"].enum_values] == [
        ("PENDING", 0),
        ("PAID", 1),
    ]


# ── union / alias / logicalType ─────────────────────────────────────────────


def test_union_keeps_declaration_order():
    """union 的声明顺序在 Avro 里有语义：**不排序**，否则"加分支"会被看成"整体变了"。"""
    sides = fixture_scan.scan_negatives()["union-add-type"]
    old = parse(sides["old"]).fields[1]
    new = parse(sides["new"]).fields[1]
    assert old.type == "union(null,long)"
    assert new.type == "union(null,long,string)"
    # 顺序敏感：同一组分支换个顺序必须是不同字符串（否则"移动"检测不出来）
    assert normalize_type(["long", "null"]) == "union(long,null)"


def test_rename_with_alias_carries_alias_and_keeps_type():
    sides = fixture_scan.scan_negatives()["rename-with-alias"]
    old = parse(sides["old"]).fields[0]
    new = parse(sides["new"]).fields[0]
    assert (old.name, new.name) == ("total_amount", "amount")
    assert list(new.aliases) == ["total_amount"]
    assert new.type == old.type


def test_logical_type_is_part_of_type_label(tmp_path):
    """logicalType 变化是 R2 的证据：它必须改变 type 字符串，不能落在元数据里。"""
    path = write(
        tmp_path,
        "logical.avsc",
        {
            "type": "record",
            "name": "Order",
            "fields": [{"name": "created_at", "type": {"type": "int", "logicalType": "date"}}],
        },
    )
    assert parse(path).fields[0].type == "int(date)"


def test_array_and_map_are_rendered_with_inner_type(tmp_path):
    path = write(
        tmp_path,
        "containers.avsc",
        {
            "type": "record",
            "name": "Order",
            "fields": [
                {"name": "tags", "type": {"type": "array", "items": "string"}},
                {"name": "labels", "type": {"type": "map", "values": "long"}},
            ],
        },
    )
    # 无号字段按名字排（K3 的规范序：Avro 稳定路径是名字，不是声明顺序）
    ir = parse(path)
    assert [field.name for field in ir.fields] == ["labels", "tags"]
    assert dict((field.name, field.type) for field in ir.fields) == {
        "tags": "array<string>",
        "labels": "map<long>",
    }


# ── 失败路径：退出码 2 ──────────────────────────────────────────────────────


def test_invalid_json_exit_two(tmp_path):
    path = write(tmp_path, "broken.avsc", '{"type": "record", "name": ')
    with pytest.raises(SchemaParseError):
        detect_format(path)
    code, _, err = run([path, path])
    assert code == 2
    assert err


def test_non_record_top_level_exit_two(tmp_path):
    """首期只把顶层 `record` 映射成 IR；map / enum 顶层是"读不懂"（2），不是"能力不足"（3）。"""
    path = write(tmp_path, "map.avsc", {"type": "map", "values": "string"})
    with pytest.raises(SchemaParseError):
        parse(path)
    code, _, _ = run([path, path])
    assert code == 2


def test_missing_field_name_exit_two(tmp_path):
    path = write(
        tmp_path,
        "nameless.avsc",
        {"type": "record", "name": "Order", "fields": [{"type": "string"}]},
    )
    with pytest.raises(SchemaParseError) as caught:
        parse(path)
    assert "name" in str(caught.value)
    code, _, _ = run([path, path])
    assert code == 2
