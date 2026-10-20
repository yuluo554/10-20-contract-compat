# -*- coding: utf-8 -*-
"""三格式解析器入口（按文件形态判别归属，**不按目录名**）。

``detect_format`` 决定退出码 2（未知形态）与 3（缺能力）的分流；``parse`` 按判别结果分派。

形态判别优先级（**内容优先于扩展名**）：
  1. JSON 文本（首字符 ``{`` / ``[``）→ avro（顶层 ``fields`` 或 record/enum 类型）或 jsonschema
  2. ``FileDescriptorSet`` → **往返校验**：能 ParseFromString 且重新序列化逐字节相同
     （只判"能解析"不够：任意一两字节的残缺输入也可能解析成功，那种误判会
     把一段乱码说成"合法的 Protobuf 描述符"）
  3. UTF-8 文本且含 ``syntax = "proto3";`` 一类特征 → proto 文本（需 protoc）
  4. 其它 → UsageError（退出码 2）；含 NUL 且判别不出 → 也是 2（二进制垃圾不是 schema）

判别顺序把 JSON 放最前、描述符放 proto 文本前：描述符是二进制，而 `.pb` 的字节
**不保证**含 NUL（实测最小的 ``FileDescriptorSet`` 全是可打印 ASCII）——
用"NUL 才算二进制"会把合法描述符判成 proto 文本。
"""

from __future__ import absolute_import

import json
import os

from ..errors import CapabilityError, SchemaParseError, UsageError

__all__ = ["detect_format", "parse", "IMPLEMENTED_IN", "looks_like_descriptor_set"]

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
    """NUL 字节是**快速**的二进制提示，但**不是**充分条件（描述符可以不含 NUL）。"""
    return b"\x00" in raw[:4096]


def _protobuf_module():
    """返回 ``descriptor_pb2`` 或 ``None``（**不做猜测**：只回答"能不能 import"）。"""
    try:
        from google.protobuf import descriptor_pb2
    except ImportError:
        return None
    return descriptor_pb2


def looks_like_descriptor_set(raw):
    """``FileDescriptorSet`` 的**强判据**：能解析、非空、且重新序列化逐字节相同。

    返回 ``True`` / ``False`` / ``None``（``None`` = protobuf 未安装，判不了）。
    ``None`` 与 ``False`` 必须分开：前者是环境问题（退出码 3），后者是输入问题（2）。
    """
    descriptor_pb2 = _protobuf_module()
    if descriptor_pb2 is None:
        return None
    if not raw:
        return False
    holder = descriptor_pb2.FileDescriptorSet()
    try:
        holder.ParseFromString(raw)
    except Exception:  # DecodeError 在不同版本里类名不同
        return False
    if not holder.file:
        return False
    if not all(item.name.endswith((".proto", ".protodevel")) for item in holder.file):
        return False
    # 往返一致才认：protobuf 对同一消息的默认序列化是确定的
    try:
        return holder.SerializeToString(deterministic=True) == raw
    except Exception:
        return False


def detect_format(path):
    """返回 ``("proto"|"avro"|"jsonschema", kind)``；``kind`` ∈ ``{"descriptor","text","json"}``。

    判别只看**内容形态**；扩展名只作为内容不可判时的兜底提示（不单独决定）。
    """
    if not os.path.isfile(path):
        raise UsageError("文件不存在: %s" % path)
    with open(path, "rb") as handle:
        raw = handle.read()

    text = _read_text(raw)

    # ① 描述符先判：**往返校验**比"首字符像不像 JSON"强得多。
    #    反例（实测踩到）：某些描述符序列化后以 ``\n[`` 开头，JSON 优先会把它们
    #    判成"非法 JSON"并报退出码 2——一个合法描述符被说成"你写错了"。
    descriptor = looks_like_descriptor_set(raw)
    if descriptor is True:
        return "proto", "descriptor"
    if descriptor is None and _looks_binary(raw):
        raise CapabilityError(
            "输入看起来是二进制描述符，但环境缺 protobuf 无法判别："
            "请 `py -m pip install protobuf` 后重试（退出码 3 的既定语义）"
        )

    # ② JSON
    if text is not None:
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

    if text is None:
        raise UsageError("输入不是 UTF-8 文本，也不是可识别的 FileDescriptorSet: %s" % path)

    # ③ proto 源码文本：本工具不解析，只识别出来以便给出准确的退出码 3
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
