# -*- coding: utf-8 -*-
"""Protobuf 解析器单测（M2）：七项、规范序、reserved 展开、oneof、enum 短名、缺件态退出码 3。

**缺 protobuf 的用例一律用 `builtins.__import__` 桩**（不依赖本机装没装）：
`detect_format` 走 `parsers/__init__._protobuf_module()`，`parse_descriptor_set` 走
`protobuf_available()` + `from google.protobuf import descriptor_pb2`——两处各打一次，
且每条桩用例都配阳性对照（不装桩就必须正常解析），否则"桩生效"与"解析器本来就坏"不可区分。
"""

import builtins
import io
import os

import pytest

from contractcompat.cli import main
from contractcompat.errors import CapabilityError, UsageError
from contractcompat.ir import ContractIR
from contractcompat.parsers import detect_format, parse
from contractcompat.parsers.proto import parse_descriptor_set, protobuf_available

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "data", "fixtures", "proto")
#: 全量扫描的根：`.pb` 不只在 `proto/`，`negatives/` 也有一对
FIXTURES_ROOT = os.path.join(ROOT, "data", "fixtures")


def fixture(name):
    return os.path.join(FIXTURES, name)


def run(argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    return main(argv, stdout=stdout, stderr=stderr), stdout.getvalue(), stderr.getvalue()


def descriptor_pb2():
    return pytest.importorskip("google.protobuf.descriptor_pb2")


def write_descriptor(tmp_path, name, build):
    """用 protobuf 现造一份描述符（只用于 fixture 覆盖不到的行为）。"""
    builder = descriptor_pb2().FileDescriptorSet()
    file_proto = builder.file.add()
    file_proto.name = "order.proto"
    file_proto.package = "example.invalid.contracts"
    file_proto.syntax = "proto3"
    build(file_proto)
    path = tmp_path / name
    path.write_bytes(builder.SerializeToString(deterministic=True))
    return str(path)


def add_field(message, name, number, field_type=9, label=1, **extra):
    field = message.field.add()
    field.name = name
    field.number = number
    field.type = field_type
    field.label = label
    for key, value in extra.items():
        setattr(field, key, value)
    return field


# ── 字段七项 ────────────────────────────────────────────────────────────────


def test_field_items_are_all_mapped():
    ir = parse(fixture("r3-requiredness-new.pb"))
    assert ir.format == "proto"
    assert ir.name == "Order"
    assert [field.name for field in ir.fields] == ["order_id", "status"]
    assert [field.number for field in ir.fields] == [1, 2]
    assert [field.json_pointer for field in ir.fields] == [None, None]
    assert [field.stable_path() for field in ir.fields] == ["1", "2"]  # 稳定路径 = 字段号
    assert [field.type for field in ir.fields] == ["string", "string"]
    assert [field.cardinality for field in ir.fields] == ["optional", "required"]  # proto2 required
    assert [field.to_json()["default"] for field in ir.fields] == [
        {"present": False, "value": None},
        {"present": False, "value": None},
    ]
    assert [list(field.enum_values) for field in ir.fields] == [[], []]
    assert [list(field.aliases) for field in ir.fields] == [[], []]
    assert ir.reserved_numbers == () and ir.reserved_names == ()
    assert ir.meta["package"] == "example.invalid.contracts"
    assert ir.meta["syntax"] == "proto2"
    assert ir.meta["file"] == "order.proto"


def test_fields_are_sorted_by_number_not_declaration_order(tmp_path):
    """规范序（K3）：描述符里字段声明顺序不可信，IR 必须按字段号排。"""

    def build(file_proto):
        message = file_proto.message_type.add()
        message.name = "Order"
        add_field(message, "second", 2)
        add_field(message, "first", 1)
        add_field(message, "tenth", 10)

    ir = parse(write_descriptor(tmp_path, "out-of-order.pb", build))
    assert [field.name for field in ir.fields] == ["first", "second", "tenth"]
    assert [field.number for field in ir.fields] == [1, 2, 10]


# ── reserved ────────────────────────────────────────────────────────────────


def test_fixture_reserved_number_is_carried():
    ir = parse(fixture("r5-reserved-conflict-new.pb"))
    assert ir.reserved_numbers == (2,)
    assert ir.meta["messages"][0]["reserved_numbers"] == [2]
    assert 2 in [field.number for field in ir.fields]  # 这个 fixture 演的是"字段撞 reserved"


def test_reserved_ranges_are_expanded_with_endpoint_rule(tmp_path):
    """描述符的 `end` 是**开区间**；超大范围不展开成巨型元组（只记端点）。"""

    def build(file_proto):
        message = file_proto.message_type.add()
        message.name = "Order"
        add_field(message, "order_id", 1)
        narrow = message.reserved_range.add()
        narrow.start, narrow.end = 3, 6  # `reserved 3 to 5;` → (3, 4, 5)
        wide = message.reserved_range.add()
        wide.start, wide.end = 100, 200  # > 64 个号 → 只记 (100, 199)
        message.reserved_name.append("old_name")

    ir = parse(write_descriptor(tmp_path, "reserved.pb", build))
    assert ir.reserved_numbers == (3, 4, 5, 100, 199)
    assert ir.reserved_names == ("old_name",)


# ── oneof ───────────────────────────────────────────────────────────────────


def test_oneof_membership_is_carried_and_member_stays_optional():
    old = parse(fixture("r6-oneof-moved-old.pb"))
    by_name = dict((field.name, field) for field in old.fields)
    assert by_name["card_token"].oneof_membership == "payment"
    assert by_name["card_token"].cardinality == "optional"  # proto3 里 oneof 成员 label 仍是 optional
    assert by_name["bank_ref"].oneof_membership is None
    assert old.meta["messages"][0]["oneofs"] == ["payment"]

    new = parse(fixture("r6-oneof-moved-new.pb"))
    assert new.meta["messages"][0]["oneofs"] == ["payment"]  # 声明还在
    assert [field.oneof_membership for field in new.fields] == [None, None, None]  # 但没有成员


# ── enum / default ──────────────────────────────────────────────────────────


def test_enum_values_use_short_type_name():
    """enum 字段的 type 用短类型名（K6）：与 Avro 的 `Status` 同说法，而不是 `enum`。"""
    old = parse(fixture("r4-enum-narrowed-old.pb"))
    new = parse(fixture("r4-enum-narrowed-new.pb"))
    status_old = dict((field.name, field) for field in old.fields)["status"]
    status_new = dict((field.name, field) for field in new.fields)["status"]
    assert status_old.type == status_new.type == "Status"
    assert [(value.name, value.number) for value in status_old.enum_values] == [
        ("STATUS_UNSPECIFIED", 0),
        ("PENDING", 1),
        ("PAID", 2),
    ]
    assert [value.name for value in status_new.enum_values] == ["STATUS_UNSPECIFIED", "PENDING"]


def test_default_value_is_carried_three_state():
    new = parse(fixture("r7-default-changed-new.pb"))
    old = parse(fixture("r7-default-changed-old.pb"))
    assert dict((field.name, field) for field in new.fields)["status"].to_json()["default"] == {
        "present": True,
        "value": "PAID",
    }
    assert dict((field.name, field) for field in old.fields)["status"].to_json()["default"] == {
        "present": True,
        "value": "PENDING",
    }
    assert dict((field.name, field) for field in new.fields)["order_id"].to_json()["default"] == {
        "present": False,
        "value": None,
    }


# ── 失败路径：非法描述符 → 退出码 2 ─────────────────────────────────────────


def test_invalid_descriptor_exit_two(tmp_path):
    path = tmp_path / "garbage.pb"
    path.write_bytes(b"\x00\x01\x02not-a-descriptor")
    with pytest.raises(UsageError):  # 坏输入是 2；缺 protobuf 才是 3（两者必须分开）
        detect_format(str(path))
    code, _, err = run([str(path), str(path)])
    assert code == 2
    assert err


def test_empty_descriptor_exit_two(tmp_path):
    """能往返序列化但没有任何 `.proto` 文件 → 不是合法输入（2）。"""
    pb = descriptor_pb2()
    path = tmp_path / "empty.pb"
    path.write_bytes(pb.FileDescriptorSet().SerializeToString(deterministic=True))
    code, _, _ = run([str(path), str(path)])
    assert code == 2


# ── 缺 protobuf → 退出码 3（import 桩；两处各打一次）────────────────────────


@pytest.fixture
def no_protobuf(monkeypatch):
    """让 `google.protobuf` 的 import 抛 ImportError——**不依赖本机装没装**。"""
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "google.protobuf" or name.startswith("google.protobuf."):
            raise ImportError("stubbed: google.protobuf 不可用")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)


def _all_pb_files():
    """`data/fixtures/**/*.pb` 的**全量**清单（排序固定，便于对日志）。

    D1 的失败形态是"照着实现分支挑了个恰好通过的夹具"，所以这组用例必须由
    **磁盘扫描**驱动：写死 slug 就会在下一次加夹具时悄悄少测。
    """
    found = []
    for directory, _, names in os.walk(FIXTURES_ROOT):
        for name in names:
            if name.endswith(".pb"):
                found.append(os.path.join(directory, name))
    return sorted(found)


def _pb_ids(paths):
    return [os.path.relpath(path, FIXTURES_ROOT).replace(os.sep, "/") for path in paths]


ALL_PB = _all_pb_files()


def test_pb_fixture_scan_matches_the_documented_count():
    """参数化的**自指守门**：扫描为空或少于台账数时，下面那组用例会"全绿但什么都没测"。"""
    assert len(ALL_PB) == 20, "台账 = 20 份 .pb（avro 之外：proto 9 对 + negatives 1 对）"
    assert sum(1 for path in ALL_PB if path.endswith("-old.pb")) == 10


@pytest.mark.parametrize("path", ALL_PB, ids=_pb_ids(ALL_PB))
def test_detect_format_without_protobuf_is_capability_error(path, no_protobuf):
    """第一处：`parsers/__init__.detect_format` 的缺件态前置判据。

    **全量参数化**（D1）：判据不许依赖"NUL 字节"这种巧合——20 份里 17 份可 UTF-8
    解码、17 份不含 NUL，靠 NUL 判会有 8 对落到退出码 2。
    """
    with pytest.raises(CapabilityError) as caught:
        detect_format(path)
    assert "protobuf" in str(caught.value)


@pytest.mark.parametrize("path", ALL_PB, ids=_pb_ids(ALL_PB))
def test_cli_without_protobuf_exits_three(path, no_protobuf):
    """第二处：CLI 真入口——缺件态是 3，不是 2（"环境给不了" ≠ "调用方写错"）。"""
    code, _, err = run([path, path])
    assert code == 3
    assert "protobuf" in err


@pytest.mark.parametrize("path", ALL_PB, ids=_pb_ids(ALL_PB))
def test_descriptor_parses_without_the_stub(path):
    """**阳性对照**：同一批 `.pb` 不装桩就必须真解析成功——否则上面两条只证明了"桩坏了"。"""
    pytest.importorskip("google.protobuf")
    ir = parse(path)
    assert isinstance(ir, ContractIR)
    assert ir.format == "proto"
    assert ir.name == "Order"


def test_protobuf_available_reports_importability(no_protobuf):
    """探针本身：桩下必须回答 False（阳性对照见下一条）。"""
    assert protobuf_available() is False


def test_protobuf_available_positive_control():
    pytest.importorskip("google.protobuf")
    assert protobuf_available() is True


def test_parse_descriptor_set_guard_without_protobuf(no_protobuf):
    """`parsers/proto.parse_descriptor_set` 自己的守门（不经 `detect_format` 时也成立）。"""
    with pytest.raises(CapabilityError) as caught:
        parse_descriptor_set(fixture("r1-field-removed-old.pb"))
    assert "pip install protobuf" in str(caught.value)


# ── 负控：缺件态判据不许把"调用方写错"也吞成 3 ─────────────────────────────


def test_negative_control_broken_json_without_protobuf(tmp_path, no_protobuf):
    """能解码、以 `{` 开头但 JSON 非法 → 仍是 2（SchemaParseError）。

    乙案的前置判据只认「`.pb` 后缀」与「不可 UTF-8 解码」两条；一旦放宽成
    "缺 protobuf 就一律 3"，这条会变红——这正是它要防的越界。
    """
    path = tmp_path / "broken.json"
    path.write_text('{"properties": ', encoding="utf-8")
    code, _, err = run([str(path), str(path)])
    assert code == 2
    assert err


def test_negative_control_unknown_text_without_protobuf(tmp_path, no_protobuf):
    """能解码、像文本、但既非 JSON 也非 proto 文本 → 2（"你给我的东西不对"）。"""
    path = tmp_path / "notes.txt"
    path.write_text("这只是一段说明文字，不是 schema。\n", encoding="utf-8")
    code, _, err = run([str(path), str(path)])
    assert code == 2
    assert err


def test_negative_control_decodable_garbage_without_protobuf(tmp_path, no_protobuf):
    """可解码的乱码 + 非 `.pb` 后缀 → 2（不是描述符，也不是"环境给不了"）。"""
    path = tmp_path / "garbage.bin"
    path.write_bytes(b"\x00\x01\x02not-a-descriptor")
    code, _, err = run([str(path), str(path)])
    assert code == 2
    assert err


def test_negative_control_avsc_and_json_still_dispatch_without_protobuf(tmp_path, no_protobuf):
    """缺 protobuf **不影响** Avro / JSON Schema 的判别（前置判据只看 `.pb` 与可解码性）。"""
    avro = tmp_path / "a.avsc"
    avro.write_text('{"type": "record", "name": "Order", "fields": []}', encoding="utf-8")
    assert detect_format(str(avro)) == ("avro", "json")

    schema = tmp_path / "a.json"
    schema.write_text('{"$schema": "https://json-schema.org/draft/2020-12/schema"}', encoding="utf-8")
    assert detect_format(str(schema)) == ("jsonschema", "json")

