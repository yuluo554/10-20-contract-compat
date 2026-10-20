# -*- coding: utf-8 -*-
"""Avro 解析器：``.avsc`` 的 JSON（``fields`` / ``default`` / ``aliases`` / ``symbols``）→ IR。

口径（``data/README.md`` §4.3）：Avro 的**稳定路径是字段名**，不是数组下标——
Avro 按名字解析，位置只是编码细节。因此 Avro 的 ``Field.number`` 与 ``json_pointer``
**一律留 None**，``stable_path()`` 自然回落到 ``name``（也正好走 ``ir.sort_fields`` 的无号分支）。

``N/A`` 语义：Avro 没有字段号概念，R5 在规则表里标 ``applies=false``；
本模块**不伪造编号**去"凑齐七项"——那是把 N/A 结论改成假数据。
"""

from __future__ import absolute_import

import json

from ..errors import SchemaParseError
from ..ir import ContractIR, EnumValue, Field

__all__ = [
    "parse_avsc",
    "load_document",
    "collect_named",
    "normalize_type",
    "cardinality_of",
]

_NAMED = ("record", "enum", "fixed", "error")


def load_document(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        try:
            document = json.load(handle)
        except ValueError as error:
            raise SchemaParseError("Avro schema 不是合法 JSON: %s（%s）" % (path, error))
    if not isinstance(document, dict):
        raise SchemaParseError("Avro schema 顶层必须是对象: %s" % path)
    if document.get("type") not in _NAMED:
        raise SchemaParseError(
            "不支持顶层 Avro 类型 %r（首期只收 record / enum / fixed）: %s" % (document.get("type"), path)
        )
    return document


def collect_named(node, found=None):
    """收集文档内的**具名类型**定义，供按名引用时查符号表。

    只走 Avro 的结构位置（``fields[*].type`` / ``items`` / ``values``），不猜别的键。
    """
    found = {} if found is None else found
    if isinstance(node, dict):
        node_type = node.get("type")
        if node_type in _NAMED and node.get("name"):
            found[node["name"]] = node
        for field in node.get("fields") or ():
            if isinstance(field, dict):
                collect_named(field.get("type"), found)
        if "items" in node:
            collect_named(node["items"], found)
        if "values" in node:
            collect_named(node["values"], found)
    elif isinstance(node, list):
        for item in node:
            collect_named(item, found)
    return found


def normalize_type(schema, named=None):
    """把 Avro 类型表达式压成**确定性字符串**。

    基本类型原样；union **保留声明顺序**（解析顺序在 Avro 里有语义，排序会篡改它）；
    array / map 展开成 ``array<T>`` / ``map<T>``；具名类型取其 ``name``；
    带 ``logicalType`` 的写成 ``int(date)`` 形态（逻辑类型变化是 R2 的证据）。
    """
    named = named or {}
    if isinstance(schema, str):
        target = named.get(schema)
        if target is not None:
            return normalize_type(target, named)
        return schema
    if isinstance(schema, list):
        return "union(%s)" % ",".join(normalize_type(item, named) for item in schema)
    if isinstance(schema, dict):
        inner = schema.get("type")
        if isinstance(inner, (dict, list)):
            return normalize_type(inner, named)
        if inner == "array":
            return "array<%s>" % normalize_type(schema.get("items"), named)
        if inner == "map":
            return "map<%s>" % normalize_type(schema.get("values"), named)
        if inner in _NAMED:
            return schema.get("name") or inner
        if schema.get("logicalType"):
            return "%s(%s)" % (inner, schema["logicalType"])
        if isinstance(inner, str) and named.get(inner) is not None:
            return normalize_type(named[inner], named)
        return inner if inner is not None else "unknown"
    return "unknown"


def _has_null_branch(schema):
    if isinstance(schema, list):
        return any(
            item == "null" or (isinstance(item, dict) and item.get("type") == "null") for item in schema
        )
    return isinstance(schema, dict) and schema.get("type") == "null"


def cardinality_of(schema, has_default):
    """Avro 没有 ``required`` 关键字，按三条**可机械判定**的规则映射。

    含 ``null`` 分支 → ``nullable``；否则有 ``default`` → ``optional``；
    其余 → ``required``（读侧缺字段又无默认，正是 R3 的证据形态）。
    """
    if _has_null_branch(schema):
        return "nullable"
    if has_default:
        return "optional"
    return "required"


def _enum_values_of(schema, named):
    """字段类型若是 enum（含按名引用），把 ``symbols`` 带成 ``EnumValue``（编号 = 下标）。

    Avro 二进制编码里 enum 用**符号下标**，所以下标就是它的稳定编号。
    """
    target = schema
    if isinstance(schema, str):
        target = named.get(schema)
    if isinstance(target, dict) and target.get("type") == "enum":
        return tuple(
            EnumValue(symbol, index) for index, symbol in enumerate(target.get("symbols") or ())
        )
    return ()


def parse_avsc(path, require_complete_ir=False):
    """Avro record → :class:`ContractIR`。字段七项：名 / 类型 / 基数 / 默认 / enum 编号 / 别名 / 空号。"""
    document = load_document(path)
    if document.get("type") not in ("record", "error"):
        raise SchemaParseError(
            "首期只把顶层 record 映射成 IR，实际是 %r: %s" % (document.get("type"), path)
        )
    named = collect_named(document)

    fields = []
    for index, raw in enumerate(document.get("fields") or ()):
        if not isinstance(raw, dict) or not raw.get("name"):
            raise SchemaParseError("Avro 字段结构非法（缺 name）: 第 %d 个字段 @ %s" % (index, path))
        type_schema = raw.get("type")
        has_default = "default" in raw
        fields.append(
            Field(
                name=raw["name"],
                type=normalize_type(type_schema, named),
                cardinality=cardinality_of(type_schema, has_default),
                number=None,
                json_pointer=None,
                default_present=has_default,
                default_value=raw.get("default"),
                enum_values=_enum_values_of(type_schema, named),
                oneof_membership=None,
                aliases=tuple(raw.get("aliases") or ()),
            )
        )

    return ContractIR(
        "avro",
        name=document.get("name") or "",
        fields=fields,
        # Avro 无字段号 → reserved_numbers 恒空；reserved_names 也没有对应关键字。
        reserved_numbers=(),
        reserved_names=(),
        ir_unsupported=(),
        meta={
            "namespace": document.get("namespace") or "",
            "field_count": len(fields),
            # Avro 的 record 级 "aliases" 针对命名，不是字段；单列出来便于 M4 判 R1
            "record_aliases": list(document.get("aliases") or ()),
        },
    )
