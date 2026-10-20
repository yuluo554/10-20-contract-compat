#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fixture 生成器：把三格式的最小 schema **程序化**产出并入库。

为什么要生成器而不是手写全部文件：

  * ``.pb`` 是二进制描述符，手写等于伪造；本机**没有 protoc**（2026-10-20 实测），
    所以用 ``google.protobuf`` 库**程序化构造 ``FileDescriptorSet``**。这条路可复算、
    不依赖外部二进制，且实测 py3.8 / py3.12 两档解释器输出的字节**完全相同**。
  * ``.avsc`` / ``.json`` 是文本，但不是"随便排一下"：全部经 ``canonical.dumps`` 落盘
    （``sort_keys`` / ``indent=2`` / LF / 恰好一个结尾换行），这样 ``--check`` 才能逐字节比。

用法::

    py data/tools/gen_fixtures.py            # 生成（覆盖写）
    py data/tools/gen_fixtures.py --check    # 重生成到临时目录 → 与入库文件逐字节比对

``--check`` 退出码：0 一致 / 1 有漂移 / 3 环境缺 protobuf（造不出 ``.pb``）。
**部分运行（``--only``）不写全集清单**：清单与文件是同一次生成的两面，分开改必然漂移。
"""

from __future__ import absolute_import

import argparse
import gzip
import io
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from contractcompat.canonical import dumps  # noqa: E402  （序列化单点：不在本文件里自己 dumps）

FIXTURES = os.path.join(ROOT, "data", "fixtures")

# ── Protobuf 描述符构造 ────────────────────────────────────────────────────
# 只用到首期需要的字段语义（data/README.md §二 已登记）：field / number / label / type /
# default_value / reserved_* / oneof_index / enum 值。
TYPE_NUMBERS = {
    "double": 1,
    "float": 2,
    "int64": 3,
    "uint64": 4,
    "int32": 5,
    "fixed64": 6,
    "fixed32": 7,
    "bool": 8,
    "string": 9,
    "bytes": 12,
    "uint32": 13,
    "sfixed32": 15,
    "sfixed64": 16,
    "sint32": 17,
    "sint64": 18,
}
LABEL_NUMBERS = {"optional": 1, "required": 2, "repeated": 3}


def _descriptor_pb2():
    try:
        from google.protobuf import descriptor_pb2
    except ImportError:
        sys.stderr.write(
            "缺 protobuf：造 .pb fixture 需要它。请 `py -m pip install protobuf`（退出码 3 的既定语义）\n"
        )
        raise SystemExit(3)
    return descriptor_pb2


def build_descriptor_set(spec):
    """把一份声明式 spec 变成 ``FileDescriptorSet`` 字节（``deterministic=True``）。"""
    descriptor_pb2 = _descriptor_pb2()
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    file_proto = descriptor_set.file.add()
    file_proto.name = spec["file"]
    file_proto.package = spec.get("package", "")
    file_proto.syntax = spec.get("syntax", "proto3")

    for enum_name, values in spec.get("enums", ()):
        enum_proto = file_proto.enum_type.add()
        enum_proto.name = enum_name
        for value_name, number in values:
            value = enum_proto.value.add()
            value.name = value_name
            value.number = number

    for message in spec.get("messages", ()):
        message_proto = file_proto.message_type.add()
        message_proto.name = message["name"]
        for oneof in message.get("oneofs", ()):
            message_proto.oneof_decl.add().name = oneof

        for field in message.get("fields", ()):
            field_proto = message_proto.field.add()
            field_proto.name = field["name"]
            field_proto.number = field["number"]
            field_proto.label = LABEL_NUMBERS[field.get("label", "optional")]
            field_proto.type = TYPE_NUMBERS.get(field["type"], 11)
            if field["type"] not in TYPE_NUMBERS:
                # 具名类型（enum / message）：type_name 用全限定名，与 protoc 的产物形态一致
                field_proto.type_name = ".%s.%s" % (file_proto.package, field["type"]) if file_proto.package else (
                    ".%s" % field["type"]
                )
                if any(field["type"] == name for name, _ in spec.get("enums", ())):
                    field_proto.type = 14  # TYPE_ENUM
                else:
                    field_proto.type = 11  # TYPE_MESSAGE
            if "default" in field:
                field_proto.default_value = field["default"]
            if "oneof" in field:
                field_proto.oneof_index = message["oneofs"].index(field["oneof"])

        for start, end in message.get("reserved_ranges", ()):
            item = message_proto.reserved_range.add()
            item.start = start
            item.end = end
        for name in message.get("reserved_names", ()):
            message_proto.reserved_name.append(name)

    return descriptor_set.SerializeToString(deterministic=True)


def render_proto_source(spec):
    """把同一份 spec 渲染成人读的 ``.proto`` 文本（**留档用**，不参与解析）。

    与描述符同源：改了 spec 两边一起变，不会出现"文本和二进制说的是两件事"。
    """
    lines = ['syntax = "%s";' % spec.get("syntax", "proto3"), ""]
    if spec.get("package"):
        lines.extend(["package %s;" % spec["package"], ""])

    for enum_name, values in spec.get("enums", ()):
        lines.append("enum %s {" % enum_name)
        for value_name, number in values:
            lines.append("  %s = %d;" % (value_name, number))
        lines.extend(["}", ""])

    for message in spec.get("messages", ()):
        lines.append("message %s {" % message["name"])
        for field in message.get("fields", ()):
            parts = [field.get("label", "optional"), field["type"], field["name"]]
            body = " ".join(parts) + " = %d" % field["number"]
            options = []
            if "default" in field:
                options.append('default = "%s"' % field["default"])
            if "oneof" in field:
                options.append("// in oneof %s" % field["oneof"])
            if options:
                body += " [" + ", ".join(options) + "]" if options[0] != "//" else "  " + " ".join(options)
            lines.append("  %s;" % body)
        ranges = message.get("reserved_ranges", ())
        if ranges:
            rendered = []
            for start, end in ranges:
                rendered.append(str(start) if end - start == 1 else "%d to %d" % (start, end - 1))
            lines.append("  reserved %s;" % ", ".join(rendered))
        if message.get("reserved_names"):
            lines.append('  reserved %s;' % ", ".join('"%s"' % name for name in message["reserved_names"]))
        for oneof in message.get("oneofs", ()):
            members = [field for field in message["fields"] if field.get("oneof") == oneof]
            lines.append("  oneof %s {" % oneof)
            for field in members:
                lines.append("    %s %s = %d;" % (field["type"], field["name"], field["number"]))
            lines.append("  }")
        lines.extend(["}", ""])

    return "\n".join(lines).rstrip("\n") + "\n"


# ── 共用骨架（最小 schema，中性占位名）─────────────────────────────────────
PACKAGE = "example.invalid.contracts"


def proto(order_fields, enums=(), message="Order", reserved_ranges=(), reserved_names=(), oneofs=(), syntax="proto3"):
    return {
        "file": "order.proto",
        "package": PACKAGE,
        "syntax": syntax,
        "enums": list(enums),
        "messages": [
            {
                "name": message,
                "fields": list(order_fields),
                "oneofs": list(oneofs),
                "reserved_ranges": list(reserved_ranges),
                "reserved_names": list(reserved_names),
            }
        ],
    }


STATUS_ENUM = ("Status", [("STATUS_UNSPECIFIED", 0), ("PENDING", 1), ("PAID", 2)])


def avro(fields, name="Order", enum_symbols=None):
    """最小 Avro record；``enum_symbols`` 给了就把 ``status`` 写成内联 enum。"""
    rendered = []
    for field in fields:
        item = {"name": field["name"]}
        if field["name"] == "status" and enum_symbols is not None:
            item["type"] = {"type": "enum", "name": "Status", "symbols": list(enum_symbols)}
        else:
            item["type"] = field["type"]
        if "default" in field:
            item["default"] = field["default"]
        if "aliases" in field:
            item["aliases"] = field["aliases"]
        rendered.append(item)
    document = {"type": "record", "name": name, "namespace": PACKAGE, "fields": rendered}
    return document


def jsonschema(properties, required, title="Order", extra_property=None):
    document = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.invalid/contracts/order.json",
        "title": title,
        "type": "object",
        "properties": dict(properties),
        "required": list(required),
        "additionalProperties": False,
    }
    if extra_property is not None:
        document["properties"].update(extra_property)
    return document


# ── 21 格矩阵 + 反例 + 不可表达（本表就是 M1 的验收矩阵）──────────────────
# 每项：(相对路径, 内容形态, 值)。pair 型用 {"old":…, "new":…}。
CASES = []


def add_pair(rel_dir, slug, fmt, old, new, suffix):
    CASES.append({"dir": rel_dir, "slug": slug, "format": fmt, "old": old, "new": new, "suffix": suffix})


def add_single(rel_dir, slug, fmt, value, suffix):
    CASES.append({"dir": rel_dir, "slug": slug, "format": fmt, "old": value, "new": None, "suffix": suffix})


# R1 FIELD_REMOVED —— 三格式同一语义（红线①的可机械检查面）
add_pair(
    "proto", "r1-field-removed", "proto",
    proto([
        {"name": "order_id", "number": 1, "type": "string"},
        {"name": "total_amount", "number": 2, "type": "int64"},
    ]),
    proto([{"name": "order_id", "number": 1, "type": "string"}]),
    "pb",
)
add_pair(
    "avro", "r1-field-removed", "avro",
    avro([{"name": "order_id", "type": "string"}, {"name": "total_amount", "type": "long", "default": 0}]),
    avro([{"name": "order_id", "type": "string"}]),
    "avsc",
)
add_pair(
    "jsonschema", "r1-field-removed", "jsonschema",
    jsonschema({"order_id": {"type": "string"}, "total_amount": {"type": "integer"}}, ["order_id", "total_amount"]),
    jsonschema({"order_id": {"type": "string"}}, ["order_id"]),
    "json",
)

# R2 TYPE_CHANGED
add_pair(
    "proto", "r2-type-changed", "proto",
    proto([
        {"name": "order_id", "number": 1, "type": "string"},
        {"name": "total_amount", "number": 2, "type": "int32"},
    ]),
    proto([
        {"name": "order_id", "number": 1, "type": "string"},
        {"name": "total_amount", "number": 2, "type": "string"},
    ]),
    "pb",
)
add_pair(
    "avro", "r2-type-changed", "avro",
    avro([{"name": "order_id", "type": "string"}, {"name": "total_amount", "type": "int", "default": 0}]),
    avro([{"name": "order_id", "type": "string"}, {"name": "total_amount", "type": "string", "default": ""}]),
    "avsc",
)
add_pair(
    "jsonschema", "r2-type-changed", "jsonschema",
    jsonschema({"order_id": {"type": "string"}, "total_amount": {"type": "integer"}}, ["order_id"]),
    jsonschema({"order_id": {"type": "string"}, "total_amount": {"type": "string"}}, ["order_id"]),
    "json",
)

# R3 REQUIREDNESS_CHANGED（proto 用 proto2 才有 required 这个 label）
add_pair(
    "proto", "r3-requiredness", "proto",
    proto(
        [{"name": "order_id", "number": 1, "type": "string"}, {"name": "status", "number": 2, "type": "string"}],
        syntax="proto2",
    ),
    proto(
        [
            {"name": "order_id", "number": 1, "type": "string"},
            {"name": "status", "number": 2, "type": "string", "label": "required"},
        ],
        syntax="proto2",
    ),
    "pb",
)
add_pair(
    "avro", "r3-requiredness", "avro",
    avro([{"name": "order_id", "type": "string"}]),
    avro([{"name": "order_id", "type": "string"}, {"name": "status", "type": "string"}]),  # 新增无 default
    "avsc",
)
add_pair(
    "jsonschema", "r3-requiredness", "jsonschema",
    jsonschema({"order_id": {"type": "string"}, "total_amount": {"type": "integer"}}, ["order_id"]),
    jsonschema({"order_id": {"type": "string"}, "total_amount": {"type": "integer"}}, ["order_id", "total_amount"]),
    "json",
)

# R4 ENUM_NARROWED
add_pair(
    "proto", "r4-enum-narrowed", "proto",
    proto(
        [
            {"name": "order_id", "number": 1, "type": "string"},
            {"name": "status", "number": 2, "type": "Status"},
        ],
        enums=[STATUS_ENUM],
    ),
    proto(
        [
            {"name": "order_id", "number": 1, "type": "string"},
            {"name": "status", "number": 2, "type": "Status"},
        ],
        enums=[("Status", [("STATUS_UNSPECIFIED", 0), ("PENDING", 1)])],
    ),
    "pb",
)
add_pair(
    "avro", "r4-enum-narrowed", "avro",
    avro([{"name": "order_id", "type": "string"}, {"name": "status", "type": "string"}],
         enum_symbols=["STATUS_UNSPECIFIED", "PENDING", "PAID"]),
    avro([{"name": "order_id", "type": "string"}, {"name": "status", "type": "string"}],
         enum_symbols=["STATUS_UNSPECIFIED", "PENDING"]),
    "avsc",
)
add_pair(
    "jsonschema", "r4-enum-narrowed", "jsonschema",
    jsonschema(
        {"order_id": {"type": "string"}, "status": {"type": "string", "enum": ["STATUS_UNSPECIFIED", "PENDING", "PAID"]}},
        ["order_id"],
    ),
    jsonschema(
        {"order_id": {"type": "string"}, "status": {"type": "string", "enum": ["STATUS_UNSPECIFIED", "PENDING"]}},
        ["order_id"],
    ),
    "json",
)

# R5 FIELD_NUMBER_REUSED —— 只有 Protobuf 有字段号；Avro / JSON Schema 是 N/A（规则表 applies=false）
add_pair(
    "proto", "r5-number-reuse", "proto",
    proto([
        {"name": "order_id", "number": 1, "type": "string"},
        {"name": "total_amount", "number": 2, "type": "int64"},
    ]),
    proto([
        {"name": "order_id", "number": 1, "type": "string"},
        {"name": "status", "number": 2, "type": "string"},  # 2 号换了主人：复用
    ]),
    "pb",
)
add_pair(
    "proto", "r5-reserved-conflict", "proto",
    proto(
        [{"name": "order_id", "number": 1, "type": "string"}],
        reserved_ranges=[(2, 3)],
    ),
    proto(
        [
            {"name": "order_id", "number": 1, "type": "string"},
            {"name": "total_amount", "number": 2, "type": "int64"},  # 2 号在 reserved 里
        ],
        reserved_ranges=[(2, 3)],
    ),
    "pb",
)

# R6 ONEOF_MOVED（Avro 无 oneof → N/A）
add_pair(
    "proto", "r6-oneof-moved", "proto",
    proto(
        [
            {"name": "order_id", "number": 1, "type": "string"},
            {"name": "card_token", "number": 2, "type": "string", "oneof": "payment"},
            {"name": "bank_ref", "number": 3, "type": "string"},
        ],
        oneofs=["payment"],
    ),
    proto(
        [
            {"name": "order_id", "number": 1, "type": "string"},
            {"name": "card_token", "number": 2, "type": "string"},  # 移出 oneof
            {"name": "bank_ref", "number": 3, "type": "string"},
        ],
        oneofs=["payment"],
    ),
    "pb",
)
add_pair(
    "jsonschema", "r6-oneof-moved", "jsonschema",
    jsonschema(
        {"order_id": {"type": "string"}, "payment": {"oneOf": [{"type": "string"}, {"type": "integer"}]}},
        ["order_id"],
    ),
    jsonschema(
        {"order_id": {"type": "string"}, "payment": {"oneOf": [{"type": "integer"}, {"type": "boolean"}]}},
        ["order_id"],
    ),
    "json",
)

# R7 DEFAULT_CHANGED
add_pair(
    "proto", "r7-default-changed", "proto",
    proto(
        [
            {"name": "order_id", "number": 1, "type": "string"},
            {"name": "status", "number": 2, "type": "string", "default": "PENDING"},
        ],
        syntax="proto2",
    ),
    proto(
        [
            {"name": "order_id", "number": 1, "type": "string"},
            {"name": "status", "number": 2, "type": "string", "default": "PAID"},
        ],
        syntax="proto2",
    ),
    "pb",
)
add_pair(
    "avro", "r7-default-changed", "avro",
    avro([{"name": "order_id", "type": "string"}, {"name": "status", "type": "string", "default": "PENDING"}]),
    avro([{"name": "order_id", "type": "string"}, {"name": "status", "type": "string", "default": "PAID"}]),
    "avsc",
)
add_pair(
    "jsonschema", "r7-default-changed", "jsonschema",
    jsonschema({"order_id": {"type": "string"}, "status": {"type": "string", "default": "PENDING"}}, ["order_id"]),
    jsonschema({"order_id": {"type": "string"}, "status": {"type": "string", "default": "PAID"}}, ["order_id"]),
    "json",
)

# 反例（看起来破、实际不破）—— 防"看到变化就报破"
add_pair(
    "negatives", "union-add-type", "avro",
    avro([{"name": "order_id", "type": "string"}, {"name": "total_amount", "type": ["null", "long"], "default": None}]),
    avro([{"name": "order_id", "type": "string"},
          {"name": "total_amount", "type": ["null", "long", "string"], "default": None}]),
    "avsc",
)
add_pair(
    "negatives", "rename-with-alias", "avro",
    avro([{"name": "total_amount", "type": "long", "default": 0}]),
    avro([{"name": "amount", "type": "long", "default": 0, "aliases": ["total_amount"]}]),
    "avsc",
)
add_pair(
    "negatives", "delete-reserved", "proto",
    proto([
        {"name": "order_id", "number": 1, "type": "string"},
        {"name": "total_amount", "number": 2, "type": "int64"},
    ]),
    proto(
        [{"name": "order_id", "number": 1, "type": "string"}],
        reserved_ranges=[(2, 3)],
        reserved_names=["total_amount"],
    ),
    "pb",
)
add_pair(
    "negatives", "add-optional-property", "jsonschema",
    jsonschema({"order_id": {"type": "string"}}, ["order_id"]),
    jsonschema({"order_id": {"type": "string"}}, ["order_id"], extra_property={"total_amount": {"type": "integer"}}),
    "json",
)

# 不可表达构造（ir_unsupported）—— 新侧引入构造，旧侧是同骨架的干净版
_IR_BASE = {"order_id": {"type": "string"}}


def _ir_pair(slug, added):
    base = jsonschema(_IR_BASE, ["order_id"])
    new = jsonschema(_IR_BASE, ["order_id"])
    new.update(added)
    add_pair("jsonschema", "ir-unsupported-" + slug, "jsonschema", base, new, "json")


_IR_PAIR_SPECS = (
    ("patternproperties", {"patternProperties": {"^x-": {"type": "string"}}}),
    ("if-then-else", {"if": {"required": ["order_id"]}, "then": {"required": ["total_amount"]},
                      "else": {"required": ["status"]}}),
    ("recursive-ref", {"$defs": {"Node": {"type": "object", "properties": {"child": {"$ref": "#/$defs/Node"}}}},
                       "properties": {"order_id": {"type": "string"}, "root": {"$ref": "#/$defs/Node"}}}),
    ("dependent-schemas", {"dependentSchemas": {"order_id": {"required": ["total_amount"]}}}),
)
for _slug, _added in _IR_PAIR_SPECS:
    _ir_pair(_slug, _added)


# ── 落盘 ──────────────────────────────────────────────────────────────────
def _render_text(value):
    """文本 fixture 一律经 ``canonical.dumps``（序列化单点，且保证 ``--check`` 可逐字节比）。"""
    return dumps(value)


def _render(case, suffix):
    if case["format"] == "proto":
        return build_descriptor_set(suffix)
    return _render_text(suffix)


def materialize(target_root, only=None):
    """把全部用例写到 ``target_root``；返回写出的相对路径列表（排序）。"""
    written = []
    for case in CASES:
        if only and only not in case["slug"]:
            continue
        directory = os.path.join(target_root, case["dir"])
        if not os.path.isdir(directory):
            os.makedirs(directory)
        for side in ("old", "new"):
            payload = case[side]
            if payload is None:
                continue
            name = "%s-%s.%s" % (case["slug"], side, case["suffix"])
            path = os.path.join(directory, name)
            data = _render(case, payload)
            mode = "wb" if case["format"] == "proto" else "w"
            if mode == "wb":
                with open(path, "wb") as handle:
                    handle.write(data)
            else:
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(data)
            written.append(os.path.relpath(path, target_root).replace("\\", "/"))
            # .proto 源同目录留档（人读用；解析器不会读它）
            if case["format"] == "proto":
                source_name = "%s-%s.proto" % (case["slug"], side)
                with open(os.path.join(directory, source_name), "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(render_proto_source(payload))
                written.append(os.path.relpath(os.path.join(directory, source_name), target_root).replace("\\", "/"))
    return sorted(written)


def _clean_placeholders():
    """删掉目录里的 .gitkeep（已有实物后它只是噪音）。"""
    for directory in ("proto", "avro", "jsonschema", "negatives"):
        keep = os.path.join(FIXTURES, directory, ".gitkeep")
        if os.path.isfile(keep):
            os.remove(keep)


def run_generate(only=None):
    written = materialize(FIXTURES, only=only)
    if only:
        sys.stdout.write("只生成了匹配 %r 的用例（%d 个文件）；**未**改其他文件\n" % (only, len(written)))
    else:
        _clean_placeholders()
    sys.stdout.write("已写入 %d 个 fixture 文件到 data/fixtures/\n" % len(written))
    return 0


def run_check(only=None):
    """重生成到临时目录 → 与入库文件**逐字节**比对。"""
    temp_root = tempfile.mkdtemp(prefix="cc-fixtures-")
    try:
        generated = materialize(temp_root, only=only)
        expected = set(generated)
        on_disk = set()
        for directory in ("proto", "avro", "jsonschema", "negatives"):
            base = os.path.join(FIXTURES, directory)
            if not os.path.isdir(base):
                continue
            for name in sorted(os.listdir(base)):
                rel = "%s/%s" % (directory, name)
                if only and only not in name:
                    continue
                if name == ".gitkeep":
                    continue
                on_disk.add(rel)

        problems = []
        for rel in sorted(expected & on_disk):
            with open(os.path.join(temp_root, rel), "rb") as handle:
                fresh = handle.read()
            with open(os.path.join(FIXTURES, rel), "rb") as handle:
                frozen = handle.read()
            if fresh != frozen:
                problems.append("字节不一致: %s（重生成 %d B / 入库 %d B）" % (rel, len(fresh), len(frozen)))
        for rel in sorted(expected - on_disk):
            problems.append("入库缺文件: %s" % rel)
        for rel in sorted(on_disk - expected):
            problems.append("多多余文件（生成器不产出）: %s" % rel)

        if problems:
            sys.stdout.write("fixture --check: %d 处漂移\n" % len(problems))
            for item in problems[:40]:
                sys.stdout.write("  " + item + "\n")
            if len(problems) > 40:
                sys.stdout.write("  ……（其余 %d 条略）\n" % (len(problems) - 40))
            return 1
        sys.stdout.write("fixture --check: 全绿（%d 个文件逐字节一致）\n" % len(expected))
        return 0
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="三格式 fixture 生成器（程序化构造 .pb / 规范 JSON 落盘）")
    parser.add_argument("--check", action="store_true", help="重生成到临时目录并与入库文件逐字节比对")
    parser.add_argument("--only", default=None, help="只处理 slug 含该子串的用例（不改全集清单）")
    args = parser.parse_args(argv)
    if args.check:
        return run_check(args.only)
    return run_generate(args.only)


if __name__ == "__main__":
    sys.exit(main())
