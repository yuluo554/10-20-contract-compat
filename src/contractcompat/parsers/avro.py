# -*- coding: utf-8 -*-
"""Avro 解析器：直接吃 ``.avsc`` 的 JSON（``fields`` / ``default`` / ``aliases`` / ``symbols``）。

M0 骨架：读文件 + 形态校验（能给出准确的退出码 2），字段级映射留 M2。
"""

from __future__ import absolute_import

import json

from ..errors import SchemaParseError
from ..ir import CARDINALITIES  # noqa: F401  （M2 用到，先保证常量可从一处取）

__all__ = ["parse_avsc", "load_document"]


def load_document(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        try:
            document = json.load(handle)
        except ValueError as error:
            raise SchemaParseError("Avro schema 不是合法 JSON: %s（%s）" % (path, error))
    if not isinstance(document, dict):
        raise SchemaParseError("Avro schema 顶层必须是对象: %s" % path)
    if document.get("type") not in ("record", "enum", "fixed", "error"):
        raise SchemaParseError(
            "不支持顶层 Avro 类型 %r（首期只收 record / enum / fixed）: %s" % (document.get("type"), path)
        )
    return document


def parse_avsc(path, require_complete_ir=False):
    load_document(path)  # 形态校验先行：非法输入必须落退出码 2
    raise NotImplementedError("Avro → IR 映射计划在 M2 落地；当前为 M0 骨架")
