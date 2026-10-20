# -*- coding: utf-8 -*-
"""Protobuf 解析器：读 ``FileDescriptorSet``（``protoc --descriptor_set_out`` 的产物）。

**不做** ``.proto`` 文本解析（``plan/00`` 已定案弃选）：文本输入由
``parsers/__init__._parse_proto`` 直接拒成 ``CapabilityError``（退出码 3）。

跨 message 字段号复用（R5 的增量格）需要**文件级视图**，所以每个 message 的
``(message_name, field_number)`` 都收进 ``meta["messages"]``，由 M4 的 R5 在文件级求值。
外层 IR 的 ``fields`` 取**第一个** message 的字段——单 message 是最小 schema 的常态，
多 message 的情形 R5 从 ``meta`` 里读全量。
"""

from __future__ import absolute_import

from ..errors import CapabilityError, SchemaParseError
from ..ir import ContractIR, EnumValue, Field

__all__ = [
    "parse_descriptor_set",
    "protobuf_available",
    "TYPE_NAMES",
    "WIRE_COMPATIBLE_GROUPS",
]

#: ``FieldDescriptorProto.Type`` 的枚举号 → 名字（写成常量而不是 import 枚举，
#: 这样本文件不 import protobuf，模块级零依赖）。
TYPE_NAMES = {
    1: "double",
    2: "float",
    3: "int64",
    4: "uint64",
    5: "int32",
    6: "fixed64",
    7: "fixed32",
    8: "bool",
    9: "string",
    10: "group",
    11: "message",
    12: "bytes",
    13: "uint32",
    14: "enum",
    15: "sfixed32",
    16: "sfixed64",
    17: "sint32",
    18: "sint64",
}

#: wire 兼容组（buf 的 ``FIELD_WIRE_COMPATIBLE_TYPE`` 语义）：同组内改类型不破坏线上字节。
#: 这是 R2 判 `breaking` / `runtime-dependent` 的**事实来源**，不是判据本身。
WIRE_COMPATIBLE_GROUPS = (
    frozenset({"int32", "uint32", "int64", "uint64", "bool"}),
    frozenset({"string", "bytes"}),
    frozenset({"fixed32", "sfixed32"}),
    frozenset({"fixed64", "sfixed64"}),
)

_LABELS = {1: "optional", 2: "required", 3: "repeated"}


def protobuf_available():
    """探测 ``google.protobuf`` 是否可用（**不做猜测**：只回答"能不能 import"）。"""
    try:
        import google.protobuf  # noqa: F401
    except ImportError:
        return False
    return True


def _type_name(value):
    return TYPE_NAMES.get(value, "unknown(%s)" % value)


def _field_type(field_proto):
    """字段类型标签：enum / message 用具名类型的**短名**（``Status``），不用 ``enum``。

    理由：跨格式可比。Avro 的枚举字段类型就叫 ``Status``，JSON Schema 叫 ``string``；
    Protobuf 若只写 ``enum``，同一个"枚举字段"在三格式里会呈现成三种说法，
    "同一语义同一张表"这条红线就断在 IR 层了。
    """
    kind = _type_name(field_proto.type)
    if kind in ("enum", "message", "group"):
        short = (getattr(field_proto, "type_name", "") or "").lstrip(".").rsplit(".", 1)[-1]
        return short or kind
    return kind


def _cardinality(label, oneof_index):
    """``oneof`` 成员在 proto3 里 label 仍是 optional；基数按 oneof 语义记 optional。"""
    if oneof_index is not None:
        return "optional"
    return _LABELS.get(label, "optional")


def _enum_values(field_proto, enum_types):
    """字段若是 enum 类型（或按类型名指向本文件的 enum），带出符号与编号。"""
    type_name = getattr(field_proto, "type_name", "") or ""
    short = type_name.lstrip(".").rsplit(".", 1)[-1]
    enum = enum_types.get(short)
    if enum is None:
        return ()
    return tuple(EnumValue(value.name, value.number) for value in enum.value)


def _reserved_ranges(message):
    """``reserved 3, 5 to 8;`` → ``(3, 5, 8)``。

    描述符里的 ``end`` 是**开区间**（``3 to 5`` 记成 start=3 end=6），所以逐个展开；
    范围很大时（``max``）不该展开成巨型元组——超过 64 个号就只记端点。
    """
    numbers = []
    for item in message.reserved_range:
        start, end = int(item.start), int(item.end)
        if end - start <= 64:
            numbers.extend(range(start, end))
        else:
            numbers.extend((start, end - 1))
    return tuple(sorted(set(numbers)))


def parse_descriptor_set(path, require_complete_ir=False):
    """``FileDescriptorSet`` → :class:`ContractIR`（首个 message 的字段 + 文件级 message 视图）。"""
    if not protobuf_available():
        raise CapabilityError(
            "解析 FileDescriptorSet 需要 protobuf：请 `py -m pip install protobuf` 后重试（退出码 3 的既定语义）"
        )

    from google.protobuf import descriptor_pb2

    descriptor_set = descriptor_pb2.FileDescriptorSet()
    with open(path, "rb") as handle:
        raw = handle.read()
    try:
        descriptor_set.ParseFromString(raw)
    except Exception as error:  # protobuf 抛的是 DecodeError，但版本间类名不同
        raise SchemaParseError("不是合法的 FileDescriptorSet: %s（%s）" % (path, error))

    if not descriptor_set.file:
        raise SchemaParseError("FileDescriptorSet 里没有任何 .proto 文件: %s" % path)

    message_view = []
    first_message = None
    first_file = descriptor_set.file[0]

    for file_proto in descriptor_set.file:
        enum_types = dict((enum.name, enum) for enum in file_proto.enum_type)
        for message in file_proto.message_type:
            # 嵌套 message / enum 也收进来（R5 要求跨 message 视图）
            local_enums = dict(enum_types)
            local_enums.update((enum.name, enum) for enum in message.enum_type)

            oneof_names = [oneof.name for oneof in message.oneof_decl]
            entries = []
            for field_proto in message.field:
                oneof_index = None
                if field_proto.HasField("oneof_index"):
                    oneof_index = int(field_proto.oneof_index)
                oneof_name = (
                    oneof_names[oneof_index]
                    if oneof_index is not None and oneof_index < len(oneof_names)
                    else None
                )
                has_default = field_proto.HasField("default_value")
                entries.append(
                    {
                        "message": message.name,
                        "name": field_proto.name,
                        "number": int(field_proto.number),
                        "type": _field_type(field_proto),
                        "type_name": getattr(field_proto, "type_name", "") or "",
                        "cardinality": _cardinality(field_proto.label, oneof_index),
                        "oneof": oneof_name,
                        "default_present": has_default,
                        "default_value": field_proto.default_value if has_default else None,
                        "enum_values": [
                            (value.name, value.number)
                            for value in _enum_values(field_proto, local_enums)
                        ],
                        "packed": bool(field_proto.options.packed) if field_proto.options else False,
                    }
                )
            message_view.append(
                {
                    "name": message.name,
                    "fields": entries,
                    "reserved_numbers": list(_reserved_ranges(message)),
                    "reserved_names": sorted(message.reserved_name),
                    "oneofs": sorted(oneof_names),
                }
            )
            if first_message is None:
                first_message = {
                    "message": message,
                    "entries": entries,
                    "local_enums": local_enums,
                }

    if first_message is None:
        raise SchemaParseError("FileDescriptorSet 里没有任何 message（首期只判 message 形态）: %s" % path)

    fields = []
    for entry in first_message["entries"]:
        fields.append(
            Field(
                name=entry["name"],
                type=entry["type"],
                cardinality=entry["cardinality"],
                number=entry["number"],
                json_pointer=None,
                default_present=entry["default_present"],
                default_value=entry["default_value"],
                enum_values=tuple(EnumValue(name, number) for name, number in entry["enum_values"]),
                oneof_membership=entry["oneof"],
                aliases=(),
            )
        )

    package = getattr(first_file, "package", "") or ""
    return ContractIR(
        "proto",
        name=first_message["message"].name,
        fields=fields,
        reserved_numbers=_reserved_ranges(first_message["message"]),
        reserved_names=tuple(sorted(first_message["message"].reserved_name)),
        ir_unsupported=(),
        meta={
            "package": package,
            "file": first_file.name,
            "syntax": getattr(first_file, "syntax", "") or "proto2",
            "messages": message_view,
        },
    )
