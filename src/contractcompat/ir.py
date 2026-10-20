# -*- coding: utf-8 -*-
"""ContractIR：三格式共用的同构中间表示。

设计要点：
  * 纯数据 + 规范序，**不读时钟、不读路径、不读环境**；
  * ``fields`` 规范序 = 有字段号的在前（按号），无号的在后（按 json_pointer, name）；
  * ``default`` 是三态（无默认 / 显式 null / 有值）——用 ``null`` 兼表"无默认"会让
    "默认值被改成 null"与"删掉默认值"变成同一件事，而 R7 必须区分它们。
"""

from __future__ import absolute_import

from .errors import SchemaParseError

__all__ = [
    "FORMATS",
    "CARDINALITIES",
    "IMPLEMENTED_IN",
    "Unsupported",
    "EnumValue",
    "Field",
    "ContractIR",
    "sort_fields",
    "to_json",
]

FORMATS = ("proto", "avro", "jsonschema")
CARDINALITIES = ("required", "optional", "repeated", "nullable")

#: 各模块的实现里程碑（骨架期用于把"未实现"讲清楚，M2–M5 逐格翻转）。
IMPLEMENTED_IN = {
    "ir": "M2",
    "parsers.proto": "M2",
    "parsers.avro": "M2",
    "parsers.jsonschema": "M2",
    "policy": "M3",
    "rules": "M4",
    "blast": "M5",
    "report": "M5",
}


class _Record(object):
    """轻量不可变记录（3.8 可用；避免 dataclass 与 frozen tuple 的来回转换）。"""

    __slots__ = ()

    def __eq__(self, other):
        return type(self) is type(other) and self._key() == other._key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((type(self).__name__,) + tuple(self._key()))

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, ", ".join("%s=%r" % pair for pair in self._pairs()))

    def _key(self):
        return tuple(value for _, value in self._pairs())

    def _pairs(self):
        raise NotImplementedError


class Unsupported(_Record):
    """一个无法表达的构造（**必须出现在输出里**，不得静默忽略）。"""

    __slots__ = ("construct", "json_pointer", "reason")

    def __init__(self, construct, json_pointer, reason):
        self.construct = construct
        self.json_pointer = json_pointer
        self.reason = reason

    def _pairs(self):
        return (("construct", self.construct), ("json_pointer", self.json_pointer), ("reason", self.reason))

    def to_json(self):
        return {"construct": self.construct, "json_pointer": self.json_pointer, "reason": self.reason}


class EnumValue(_Record):
    __slots__ = ("name", "number")

    def __init__(self, name, number=None):
        self.name = name
        self.number = number

    def _pairs(self):
        return (("name", self.name), ("number", self.number))

    def sort_key(self):
        # number 可能为 None（JSON Schema 的 enum 无编号）：缺号的排后面，**不比较 None**
        if self.number is None:
            return (1, 0, self.name)
        return (0, self.number, self.name)

    def to_json(self):
        return {"name": self.name, "number": self.number}


class Field(_Record):
    __slots__ = (
        "name",
        "number",
        "json_pointer",
        "type",
        "cardinality",
        "default_present",
        "default_value",
        "enum_values",
        "oneof_membership",
        "aliases",
    )

    def __init__(
        self,
        name,
        type,
        cardinality="optional",
        number=None,
        json_pointer=None,
        default_present=False,
        default_value=None,
        enum_values=(),
        oneof_membership=None,
        aliases=(),
    ):
        if cardinality not in CARDINALITIES:
            raise SchemaParseError("cardinality 非法: %r（允许 %s）" % (cardinality, CARDINALITIES))
        self.name = name
        self.type = type
        self.cardinality = cardinality
        self.number = number
        self.json_pointer = json_pointer
        self.default_present = bool(default_present)
        self.default_value = default_value
        self.enum_values = tuple(enum_values)
        self.oneof_membership = oneof_membership
        self.aliases = tuple(aliases)

    def _pairs(self):
        return (
            ("name", self.name),
            ("number", self.number),
            ("json_pointer", self.json_pointer),
            ("type", self.type),
            ("cardinality", self.cardinality),
            ("default_present", self.default_present),
            ("default_value", self.default_value),
            ("enum_values", self.enum_values),
            ("oneof_membership", self.oneof_membership),
            ("aliases", self.aliases),
        )

    def sort_key(self):
        if self.number is None:
            return (1, 0, self.json_pointer or "", self.name)
        return (0, self.number, "", self.name)

    def stable_path(self):
        """稳定路径：Protobuf 用字段号、Avro 用字段名、JSON Schema 用指针。"""
        if self.number is not None:
            return str(self.number)
        if self.json_pointer:
            return self.json_pointer
        return self.name

    def to_json(self):
        return {
            "name": self.name,
            "number": self.number,
            "json_pointer": self.json_pointer,
            "type": self.type,
            "cardinality": self.cardinality,
            "default": {"present": self.default_present, "value": self.default_value},
            "enum_values": [value.to_json() for value in self.enum_values],
            "oneof_membership": self.oneof_membership,
            "aliases": list(self.aliases),
        }


class ContractIR(_Record):
    __slots__ = ("format", "name", "fields", "reserved_numbers", "reserved_names", "ir_unsupported", "meta")

    def __init__(
        self,
        format,
        name="",
        fields=(),
        reserved_numbers=(),
        reserved_names=(),
        ir_unsupported=(),
        meta=None,
    ):
        if format not in FORMATS:
            raise SchemaParseError("format 非法: %r（允许 %s）" % (format, FORMATS))
        self.format = format
        self.name = name
        self.fields = sort_fields(fields)
        self.reserved_numbers = tuple(sorted(set(reserved_numbers)))
        self.reserved_names = tuple(sorted(set(reserved_names)))
        self.ir_unsupported = tuple(
            sorted(ir_unsupported, key=lambda item: (item.json_pointer or "", item.construct))
        )
        self.meta = dict(meta or {})

    def _pairs(self):
        return (
            ("format", self.format),
            ("name", self.name),
            ("fields", self.fields),
            ("reserved_numbers", self.reserved_numbers),
            ("reserved_names", self.reserved_names),
            ("ir_unsupported", self.ir_unsupported),
        )

    def to_json(self):
        return {
            "format": self.format,
            "name": self.name,
            "fields": [field.to_json() for field in self.fields],
            "reserved_numbers": list(self.reserved_numbers),
            "reserved_names": list(self.reserved_names),
            "ir_unsupported": [item.to_json() for item in self.ir_unsupported],
            "meta": dict(sorted(self.meta.items())),
        }


def sort_fields(fields):
    """规范序。**不比较 None**：``None < int`` 在 Py3 抛 TypeError。"""
    return tuple(sorted(fields, key=lambda field: field.sort_key()))


def to_json(ir):
    return ir.to_json()
