# -*- coding: utf-8 -*-
"""JSON Schema 解析器单测（M2）：七项、required、enum 字面量、oneOf、`$ref` 可达/不可达、退出码 2/3。

两条纪律在这里被逐条钉住：
  * **不可表达构造必须落 `ir_unsupported`**（不抛错、不静默忽略），`--require-complete-ir` 才拒；
  * `$ref` 只解析同文件指针，外部/走不通的一律记 `external_ref` 且**零网络**。
"""

import io
import json
import os

import pytest

from contractcompat.cli import main
from contractcompat.errors import SchemaParseError
from contractcompat.parsers import detect_format, parse

import fixture_scan

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "data", "fixtures", "jsonschema")


def fixture(name):
    return os.path.join(FIXTURES, name)


def write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    return str(path)


def run(argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    return main(argv, stdout=stdout, stderr=stderr), stdout.getvalue(), stderr.getvalue()


# ── 字段七项 ────────────────────────────────────────────────────────────────


def test_field_items_are_all_mapped():
    ir = parse(fixture("r4-enum-narrowed-old.json"))
    assert ir.format == "jsonschema"
    assert ir.name == "Order"
    assert [field.name for field in ir.fields] == ["order_id", "status"]
    # JSON Schema 无字段号 → None；稳定路径是指针（`data/README.md` §4.3）
    assert [field.number for field in ir.fields] == [None, None]
    assert [field.json_pointer for field in ir.fields] == ["/properties/order_id", "/properties/status"]
    assert [field.stable_path() for field in ir.fields] == ["/properties/order_id", "/properties/status"]
    assert [field.type for field in ir.fields] == ["string", "string"]
    assert [field.cardinality for field in ir.fields] == ["required", "optional"]
    assert [field.to_json()["default"] for field in ir.fields] == [
        {"present": False, "value": None},
        {"present": False, "value": None},
    ]
    assert [field.oneof_membership for field in ir.fields] == [None, None]
    assert [list(field.aliases) for field in ir.fields] == [[], []]
    assert ir.reserved_numbers == () and ir.reserved_names == ()
    assert ir.meta["additional_properties"] is False
    assert ir.meta["required"] == ["order_id"]
    assert ir.meta["field_count"] == 2
    assert ir.meta["schema_dialect"] == "https://json-schema.org/draft/2020-12/schema"


def test_required_drives_cardinality():
    old = parse(fixture("r3-requiredness-old.json"))
    new = parse(fixture("r3-requiredness-new.json"))
    old_by_name = dict((field.name, field) for field in old.fields)
    new_by_name = dict((field.name, field) for field in new.fields)
    assert old_by_name["total_amount"].cardinality == "optional"
    assert new_by_name["total_amount"].cardinality == "required"
    assert old.meta["required"] == ["order_id"]
    assert new.meta["required"] == ["order_id", "total_amount"]


# ── enum：字面量标签，不是 json.dumps ───────────────────────────────────────


def test_enum_values_have_no_numbers_and_keep_document_order():
    status = dict((field.name, field) for field in parse(fixture("r4-enum-narrowed-old.json")).fields)["status"]
    assert [(value.name, value.number) for value in status.enum_values] == [
        ("STATUS_UNSPECIFIED", None),
        ("PENDING", None),
        ("PAID", None),
    ]


def test_enum_labels_are_literal_forms(tmp_path):
    """`_literal_label` 是手写字面量（K7）：`json.dumps` 只在 `canonical.py`（AST 守门）。

    如果这里改成 `json.dumps`，布尔会是 `true`、对象会带空格与引号——标签跨版本漂移。
    """
    path = write(
        tmp_path,
        "labels.json",
        {
            "type": "object",
            "properties": {
                "flag": {"enum": [0, 1.5, True, False, None, "x", [1, 2], {"a": 1}]},
            },
        },
    )
    labels = [value.name for value in parse(path).fields[0].enum_values]
    assert labels == ["0", "1.5", "true", "false", "null", "x", "[1,2]", "{a:1}"]


# ── oneOf / anyOf ───────────────────────────────────────────────────────────


def test_oneof_membership_signature_is_order_insensitive():
    """分支下标一动就全变，会把"同一分支换了位置"误报成"分支移动"；签名必须按标签排序。"""
    old = dict((field.name, field) for field in parse(fixture("r6-oneof-moved-old.json")).fields)["payment"]
    new = dict((field.name, field) for field in parse(fixture("r6-oneof-moved-new.json")).fields)["payment"]
    assert old.oneof_membership == "oneOf:integer,string"
    assert new.oneof_membership == "oneOf:boolean,integer"
    # type 标签保留**声明顺序**（union 语义），与签名一静一动：两者不可互相替代
    assert old.type == "oneOf(string,integer)"
    assert new.type == "oneOf(integer,boolean)"


def test_oneof_signature_ignores_declaration_order(tmp_path):
    def build(branches):
        return write(
            tmp_path,
            "oneof-%d.json" % len(branches),
            {"type": "object", "properties": {"x": {"oneOf": branches}}},
        )

    forward = parse(build([{"type": "string"}, {"type": "integer"}])).fields[0]
    backward = parse(build([{"type": "integer"}, {"type": "string"}])).fields[0]
    assert forward.oneof_membership == backward.oneof_membership == "oneOf:integer,string"
    assert forward.type != backward.type  # 声明顺序仍体现在 type 上


# ── $ref：可达 / 不可达 ─────────────────────────────────────────────────────


def test_local_ref_is_resolved_in_place(tmp_path):
    path = write(
        tmp_path,
        "local-ref.json",
        {
            "$defs": {"Status": {"type": "string", "enum": ["PENDING", "PAID"]}},
            "type": "object",
            "properties": {"status": {"$ref": "#/$defs/Status"}},
            "required": ["status"],
        },
    )
    ir = parse(path)
    status = ir.fields[0]
    assert status.type == "string"
    assert [value.name for value in status.enum_values] == ["PENDING", "PAID"]
    # 指针纪律：跟随 $ref 不重置指针（仍是字段自己的位置）
    assert status.json_pointer == "/properties/status"
    assert ir.ir_unsupported == ()


def test_unreachable_refs_are_reported_not_followed(tmp_path):
    """外部 URL 与"本文件里不存在的指针"都不取：零网络是红线，且不得静默当 any。"""
    path = write(
        tmp_path,
        "broken-refs.json",
        {
            "type": "object",
            "properties": {
                "remote": {"$ref": "https://example.invalid/contracts/ext.json"},
                "missing": {"$ref": "#/definitions/nope"},
            },
        },
    )
    ir = parse(path)
    by_name = dict((field.name, field) for field in ir.fields)
    assert by_name["remote"].type == "unresolved_ref"
    assert by_name["missing"].type == "unresolved_ref"
    entries = sorted((item.construct, item.json_pointer) for item in ir.ir_unsupported)
    assert entries == [
        ("external_ref", "/properties/missing/$ref"),
        ("external_ref", "/properties/remote/$ref"),
    ]


def test_recursive_ref_terminates_and_is_reported():
    """环引用不展开（会栈溢出），按不可表达登记；返回必须**正常**，不是 RecursionError。"""
    ir = parse(fixture("ir-unsupported-recursive-ref-new.json"))
    constructs = [item.construct for item in ir.ir_unsupported]
    assert constructs.count("recursive_ref") == 2  # 定义处一次、使用处一次
    pointers = [item.json_pointer for item in ir.ir_unsupported if item.construct == "recursive_ref"]
    assert pointers == ["/$defs/Node/properties/child/$ref", "/properties/root/$ref"]
    # 递归类型的字段仍能取到类型（不跟随展开，但对象形态可判）
    assert dict((field.name, field) for field in ir.fields)["root"].type == "object"


# ── 不可表达构造：不是异常，是 IR 里的一等结论 ─────────────────────────────


def test_patternproperties_pointer_is_absolute_and_named():
    ir = parse(fixture("ir-unsupported-patternproperties-new.json"))
    assert [(item.construct, item.json_pointer) for item in ir.ir_unsupported] == [
        ("patternProperties", "/patternProperties"),
    ]
    assert ir.ir_unsupported[0].reason  # 理由不能空：空理由等于静默忽略


def test_if_then_else_group_is_recorded_once():
    """`if/then/else` 一组只记一条（K9）：三键齐时不得刷成三条。"""
    ir = parse(fixture("ir-unsupported-if-then-else-new.json"))
    assert [item.construct for item in ir.ir_unsupported] == ["if"]
    assert ir.ir_unsupported[0].json_pointer == "/if"


def test_dependent_schemas_is_recorded():
    ir = parse(fixture("ir-unsupported-dependent-schemas-new.json"))
    assert [(item.construct, item.json_pointer) for item in ir.ir_unsupported] == [
        ("dependentSchemas", "/dependentSchemas"),
    ]


def test_unsupported_is_recorded_not_raised():
    """默认：**登记后继续**（IR 仍可用）；拒绝出结论是 `--require-complete-ir` 的策略（见 test_cli）。"""
    ir = parse(fixture("ir-unsupported-patternproperties-new.json"))
    assert [item.construct for item in ir.ir_unsupported] == ["patternProperties"]
    assert ir.fields  # IR 不是空的：可表达的部分照常映射
    assert ir.ir_unsupported[0].reason


# ── 元信息 ──────────────────────────────────────────────────────────────────


def test_additional_properties_tolerance_is_metadata(tmp_path):
    closed = parse(fixture("r4-enum-narrowed-old.json"))
    assert closed.meta["additional_properties"] is False
    open_schema = parse(write(tmp_path, "open.json", {"type": "object", "properties": {"a": {"type": "string"}}}))
    assert open_schema.meta["additional_properties"] is True


# ── 失败路径：退出码 2 ──────────────────────────────────────────────────────


def test_invalid_json_exit_two(tmp_path):
    path = write(tmp_path, "broken.json", '{"properties": ')
    with pytest.raises(SchemaParseError):
        detect_format(path)
    code, _, err = run([path, path])
    assert code == 2
    assert err


def test_non_object_top_level_exit_two(tmp_path):
    path = write(tmp_path, "array.json", "[]")
    with pytest.raises(SchemaParseError):
        parse(path)
    code, _, _ = run([path, path])
    assert code == 2


def test_property_must_be_object_exit_two(tmp_path):
    path = write(tmp_path, "bad-property.json", {"type": "object", "properties": {"a": "string"}})
    with pytest.raises(SchemaParseError) as caught:
        parse(path)
    assert "properties/a" in str(caught.value)
    code, _, _ = run([path, path])
    assert code == 2
