# -*- coding: utf-8 -*-
"""JSON Schema 解析器：``properties`` / ``required`` / ``type`` / ``enum`` / ``oneOf`` / 可解析 ``$ref``。

M0 骨架：读文件 + 形态校验；**不可表达构造的清单**先落成常量（M2 用它产出 ``ir_unsupported``）。
"""

from __future__ import absolute_import

import json

from ..errors import SchemaParseError

__all__ = ["parse_schema", "load_document", "UNSUPPORTED_CONSTRUCTS"]

#: 首期**不可表达**的构造：见到就必须进 ``ir_unsupported``，不得静默忽略。
#: 这是对 getsentry/json-schema-diff "not implemented and therefore ignored" 的直接回应。
UNSUPPORTED_CONSTRUCTS = (
    "patternProperties",
    "if",
    "then",
    "else",
    "dependentSchemas",
    "dependentRequired",
    "propertyNames",
    "recursive_ref",
)


def load_document(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        try:
            document = json.load(handle)
        except ValueError as error:
            raise SchemaParseError("JSON Schema 不是合法 JSON: %s（%s）" % (path, error))
    if not isinstance(document, dict):
        raise SchemaParseError("JSON Schema 顶层必须是对象: %s" % path)
    return document


def parse_schema(path, require_complete_ir=False):
    load_document(path)  # 形态校验先行：非法输入必须落退出码 2
    raise NotImplementedError("JSON Schema → IR 映射计划在 M2 落地；当前为 M0 骨架")
