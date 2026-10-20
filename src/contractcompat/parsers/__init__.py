# -*- coding: utf-8 -*-
"""三格式解析器入口（按文件形态判别归属，**不按目录名**）。

M0 骨架：``parse`` 已完成"按形态分派 + 缺件态分类"，三种格式的具体解析体留 M2。
`detect_format` 已经实现——它决定退出码 2（未知形态）与 3（缺能力）的分流，
M2 只替换 ``_parse_*`` 的函数体。

形态判别优先级（**内容优先于扩展名**）：
  1. 文件魔数 / 二进制可读性 → ``FileDescriptorSet``（``.pb``）
  2. JSON 文本 → 顶层有 ``fields`` 且 ``type`` 含 record/enum → avro；
     顶层有 ``properties`` / ``$schema`` / ``type`` 对象形态 → jsonschema
  3. UTF-8 文本且首行像 ``syntax = "proto3";`` → proto 文本（需 protoc）
  4. 其它 → UsageError（退出码 2）
"""

from __future__ import absolute_import

import json
import os

from ..errors import CapabilityError, SchemaParseError, UsageError
from ..ir import ContractIR

__all__ = ["detect_format", "parse", "IMPLEMENTED_IN"]

IMPLEMENTED_IN = {"detect_format": "M0", "parse.avro": "M2", "parse.jsonschema": "M2", "parse.proto": "M2"}

_AVRO_TYPES = ("record", "enum", "fixed", "error")
_JSONSCHEMA_HINTS = ("$schema", "properties", "definitions", "$defs", "required")
_PROTO_HINTS = ("syntax =", "syntax=", "message ", "package ")


def _read_text(raw):
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None


def _looks_binary(raw):
    """NUL 字节是最可靠的二进制判据（UTF-16 文本除外——本工具只收 UTF-8）。"""
    return b"\x00" in raw[:4096]


def detect_format(path):
    """返回 ``("proto"|"avro"|"jsonschema", kind)``；``kind`` ∈ ``{"descriptor","text","json"}``。

    判别只看**内容形态**；扩展名只作为内容不可判时的兜底提示（不单独决定）。
    """
    if not os.path.isfile(path):
        raise UsageError("文件不存在: %s" % path)
    with open(path, "rb") as handle:
        raw = handle.read()

    if _looks_binary(raw):
        return "proto", "descriptor"

    text = _read_text(raw)
    if text is None:
        raise UsageError("输入不是 UTF-8 文本，也不是可识别的二进制描述符: %s" % path)

    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            document = json.loads(text)
        except ValueError as error:
            raise SchemaParseError("JSON 非法: %s（%s）" % (path, error))
        if isinstance(document, dict):
            kind = document.get("type")
            if kind in _AVRO_TYPES or "fields" in document:
                return "avro", "json"
            if any(hint in document for hint in _JSONSCHEMA_HINTS):
                return "jsonschema", "json"
            # 顶层是 $ref / 单类型 schema 这类极简形态，仍按 JSON Schema 处理
            if "type" in document or "$ref" in document:
                return _json_kind(path, document), "json"
        return _json_kind(path, document), "json"

    if any(hint in text[:4000] for hint in _PROTO_HINTS):
        return "proto", "text"

    raise UsageError("无法判别 schema 形态（既不是 JSON、也不是 proto 文本、也不是描述符）: %s" % path)


def _json_kind(path, document):
    """内容判不出时用扩展名兜底（**不按目录名**：同一目录里可以混放三格式）。

    判据顺序固定：内容优先；扩展名只在内容歧义时生效，且仍要过该格式自己的形态校验
    （所以"扩展名对、内容错"会落 SchemaParseError 而不是被静默当成另一种格式）。
    """
    suffix = os.path.splitext(path)[1].lower()
    if suffix == ".avsc":
        return "avro"
    return "jsonschema"


def parse(path, *, require_complete_ir=False, protoc_runner=None):
    """解析一个 schema 文件为 :class:`ContractIR`。"""
    fmt, kind = detect_format(path)
    if fmt == "proto":
        return _parse_proto(path, kind, require_complete_ir=require_complete_ir, protoc_runner=protoc_runner)
    if fmt == "avro":
        return _parse_avro(path, require_complete_ir=require_complete_ir)
    return _parse_jsonschema(path, require_complete_ir=require_complete_ir)


def _not_yet(what, milestone):
    raise CapabilityError("%s 尚未实现（计划在 %s）；M0 骨架只交付参数面与退出码契约" % (what, milestone))


def _parse_proto(path, kind, require_complete_ir=False, protoc_runner=None):
    if kind == "text":
        # 题面 §六：不自行解析 .proto 文本；必须由 protoc 产出描述符
        raise CapabilityError(
            "输入是 .proto 文本；本工具不解析 proto 源码，请先用 "
            "`protoc --descriptor_set_out=<out.pb> --include_imports <file.proto>` 生成 FileDescriptorSet"
        )
    from .proto import parse_descriptor_set

    return parse_descriptor_set(path, require_complete_ir=require_complete_ir)


def _parse_avro(path, require_complete_ir=False):
    from .avro import parse_avsc

    return parse_avsc(path, require_complete_ir=require_complete_ir)


def _parse_jsonschema(path, require_complete_ir=False):
    from .jsonschema import parse_schema

    return parse_schema(path, require_complete_ir=require_complete_ir)
