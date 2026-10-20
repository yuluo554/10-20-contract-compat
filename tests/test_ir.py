# -*- coding: utf-8 -*-
"""ContractIR 与三格式形态判别（M0 已实现的部分）。

M2 会补齐"解析成字段"的部分；本文件的断言现在就锁住**规范序**与**形态判别**，
因为这两条是"同一输入两次运行逐字节一致"与"退出码 2/3 分流"的地基。
"""

import json
import os

import pytest

from contractcompat.errors import CapabilityError, SchemaParseError, UsageError
from contractcompat.ir import ContractIR, EnumValue, Field, Unsupported, sort_fields, to_json
from contractcompat.parsers import detect_format, parse
from contractcompat.parsers.jsonschema import UNSUPPORTED_CONSTRUCTS


def write(tmp_path, name, payload):
    path = tmp_path / name
    if isinstance(payload, bytes):
        path.write_bytes(payload)
    elif isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return str(path)


def test_fields_sorted_by_number_then_pointer():
    fields = [
        Field("no_number_b", "string", json_pointer="/properties/no_number_b"),
        Field("second", "int", number=2),
        Field("no_number_a", "string", json_pointer="/properties/no_number_a"),
        Field("first", "string", number=1),
    ]
    ordered = [field.name for field in sort_fields(fields)]
    assert ordered == ["first", "second", "no_number_a", "no_number_b"]


def test_sort_does_not_compare_none_with_int():
    """这是必然踩的坑：混排 None 与 int 会抛 TypeError（Py3 不允许 None < int）。"""
    fields = [Field("a", "string", number=None, json_pointer="/a"), Field("b", "int", number=0)]
    assert [field.name for field in sort_fields(fields)] == ["b", "a"]


def test_default_is_three_state():
    absent = Field("a", "string")
    explicit_null = Field("a", "string", default_present=True, default_value=None)
    valued = Field("a", "string", default_present=True, default_value="x")
    assert absent.to_json()["default"] == {"present": False, "value": None}
    assert explicit_null.to_json()["default"] == {"present": True, "value": None}
    assert valued.to_json()["default"] == {"present": True, "value": "x"}
    # 三态必须两两不同：否则"改成 null"与"删掉默认值"会不可区分（R7 要区分）
    assert len({json.dumps(row.to_json()["default"], sort_keys=True) for row in (absent, explicit_null, valued)}) == 3


def test_enum_values_sorted_without_comparing_none():
    ir = ContractIR(
        "avro",
        name="Order",
        fields=[Field("status", "enum", enum_values=[EnumValue("B", 1), EnumValue("A"), EnumValue("C", 0)])],
    )
    payload = json.loads(json.dumps(to_json(ir)))
    # IR 内部按 (number, name) 排；无号排后
    assert [value["name"] for value in payload["fields"][0]["enum_values"]] == ["B", "A", "C"]


def test_ir_json_is_stable_across_two_builds():
    def build():
        return to_json(
            ContractIR(
                "jsonschema",
                name="Order",
                fields=[
                    Field("b", "string", json_pointer="/properties/b"),
                    Field("a", "integer", json_pointer="/properties/a", cardinality="required"),
                ],
                ir_unsupported=[Unsupported("patternProperties", "/patternProperties", "正则键无法枚举")],
            )
        )

    assert json.dumps(build(), sort_keys=True) == json.dumps(build(), sort_keys=True)


def test_ir_rejects_unknown_format():
    with pytest.raises(SchemaParseError):
        ContractIR("thrift")


def test_ir_rejects_unknown_cardinality():
    with pytest.raises(SchemaParseError):
        Field("a", "string", cardinality="sometimes")


def test_detect_format_avro(tmp_path):
    path = write(tmp_path, "a.avsc", {"type": "record", "name": "Order", "fields": []})
    assert detect_format(path) == ("avro", "json")


def test_detect_format_jsonschema(tmp_path):
    path = write(tmp_path, "a.json", {"$schema": "https://json-schema.org/draft/2020-12/schema", "properties": {}})
    assert detect_format(path) == ("jsonschema", "json")


def test_detect_format_proto_text(tmp_path):
    path = write(tmp_path, "a.proto", 'syntax = "proto3";\nmessage Order { string id = 1; }\n')
    assert detect_format(path) == ("proto", "text")


def test_detect_format_descriptor_by_content_not_extension(tmp_path):
    """形态判别按内容：一个叫 .txt 的二进制描述符也要认出来（按扩展名分派会漏）。"""
    path = write(tmp_path, "descriptor.txt", b"\x00\x01\x02not-text")
    assert detect_format(path) == ("proto", "descriptor")


def test_detect_format_missing_file_is_usage_error(tmp_path):
    with pytest.raises(UsageError):
        detect_format(str(tmp_path / "nope.avsc"))


def test_detect_format_unknown_text_is_usage_error(tmp_path):
    path = write(tmp_path, "notes.txt", "这只是一段说明文字，不是 schema。\n")
    with pytest.raises(UsageError):
        detect_format(path)


def test_detect_format_broken_json_is_parse_error(tmp_path):
    path = write(tmp_path, "broken.json", '{"properties": ')
    with pytest.raises(SchemaParseError):
        detect_format(path)


def test_parse_proto_text_requires_descriptor(tmp_path):
    """`.proto` 文本**不自行解析**（题面 §六）：必须由 protoc 产出描述符，缺失即能力不足。"""
    path = write(tmp_path, "a.proto", 'syntax = "proto3";\nmessage Order { string id = 1; }\n')
    with pytest.raises(CapabilityError) as caught:
        parse(path)
    assert "descriptor_set_out" in str(caught.value)


def test_parse_avro_validates_shape_before_mapping(tmp_path):
    path = write(tmp_path, "a.avsc", {"type": "record", "name": "Order", "fields": []})
    with pytest.raises(NotImplementedError):
        parse(path)  # M2 才接上映射；现在必须显式说"没实现"，不能返回空 IR


def test_parse_avro_rejects_non_record_top_level(tmp_path):
    path = write(tmp_path, "a.avsc", {"type": "map", "values": "string"})
    with pytest.raises(SchemaParseError):
        parse(path)


def test_parse_jsonschema_rejects_non_object(tmp_path):
    path = write(tmp_path, "a.json", "[]")
    with pytest.raises(SchemaParseError):
        parse(path)


def test_unsupported_construct_list_is_explicit():
    """getsentry 的坑：未实现的构造被静默忽略。这里把清单本身钉住。"""
    assert "patternProperties" in UNSUPPORTED_CONSTRUCTS
    assert "if" in UNSUPPORTED_CONSTRUCTS
    assert "recursive_ref" in UNSUPPORTED_CONSTRUCTS
    assert "dependentSchemas" in UNSUPPORTED_CONSTRUCTS


def test_parse_missing_file_reports_usage_error(tmp_path):
    with pytest.raises(UsageError):
        parse(str(tmp_path / "ghost.avsc"))
