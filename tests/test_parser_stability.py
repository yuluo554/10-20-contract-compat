# -*- coding: utf-8 -*-
"""解析确定性（M2-3）与越界输入行为（M2-6）。

**双跑逐字节一致**是 golden 与 digest 能成立的地基：一次解析的结果只要有一处依赖
迭代顺序 / 环境，`--check` 就会间歇性红。这里既给单文件断言（定位坏在哪一个），
也给全量 54 份 schema 输入的批量断言（防止新增 fixture 时漏检）。

**越界输入**（空 message / 无 `properties` / 空 `fields`）是**合法 schema**：
解析器必须返回空 IR，而不是报错、也不是"看起来像空但少个键"。空 IR 是 R3（新增必填）
与 R1（删字段）的对照基线，改坏了会让判定静默变成"没差异"。
"""

import io
import os

import pytest

from contractcompat.canonical import dumps
from contractcompat.cli import main
from contractcompat.ir import to_json
from contractcompat.parsers import parse
from contractcompat.parsers.proto import protobuf_available

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "data", "fixtures")

#: 54 = 18 `.pb` + 14 `.avsc` + 22 `.json`；另有 18 份 `.proto` 是**人读源文本**，
#: 不是解析输入（文本一律退出码 3，见 `test_ir.py`）。
SCHEMA_EXTS = (".pb", ".avsc", ".json")
EXPECTED_SCHEMA_INPUTS = 54

SINGLE_FILE_CASES = (
    os.path.join(FIXTURES, "avro", "r1-field-removed-old.avsc"),
    os.path.join(FIXTURES, "jsonschema", "r4-enum-narrowed-old.json"),
    os.path.join(FIXTURES, "proto", "r6-oneof-moved-old.pb"),
)


def schema_inputs():
    found = []
    for dirpath, dirnames, filenames in os.walk(FIXTURES):
        dirnames[:] = sorted(name for name in dirnames if name != "__pycache__")
        for name in sorted(filenames):
            if name.endswith(SCHEMA_EXTS):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def run(argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    return main(argv, stdout=stdout, stderr=stderr), stdout.getvalue(), stderr.getvalue()


# ── 双跑逐字节一致 ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("path", SINGLE_FILE_CASES, ids=lambda path: os.path.basename(path))
def test_single_file_double_parse_is_byte_identical(path):
    """单文件断言：同一份输入解析两次，`canonical.dumps(to_json(ir))` 逐字节相同。"""
    if path.endswith(".pb"):
        pytest.importorskip("google.protobuf")
    first = dumps(to_json(parse(path)))
    second = dumps(to_json(parse(path)))
    assert first == second
    assert first.strip()  # 非空跑自证：空字符串相等什么也没证明


def test_every_fixture_is_byte_stable_across_two_parses():
    paths = schema_inputs()
    assert len(paths) == EXPECTED_SCHEMA_INPUTS, "fixture 数量变了（新增/删除都要同步本断言）: %d" % len(paths)
    if not protobuf_available():
        pytest.skip("环境缺 protobuf：%d 份 .pb 无法解析" % len([p for p in paths if p.endswith(".pb")]))
    checked = 0
    for path in paths:
        first = dumps(to_json(parse(path)))
        second = dumps(to_json(parse(path)))
        assert first == second, "双跑不一致: %s" % os.path.relpath(path, ROOT)
        checked += 1
    assert checked == EXPECTED_SCHEMA_INPUTS


# ── 越界输入：空 schema 合法，返回空 IR ─────────────────────────────────────


def test_avro_record_with_empty_fields_yields_empty_ir(tmp_path):
    path = tmp_path / "empty.avsc"
    path.write_text('{"type": "record", "name": "Order", "fields": []}', encoding="utf-8")
    ir = parse(str(path))
    assert ir.format == "avro"
    assert ir.name == "Order"
    assert ir.fields == ()
    assert ir.meta["field_count"] == 0
    assert to_json(ir)["fields"] == []


def test_avro_empty_record_emits_valid_ir_through_cli(tmp_path):
    """`--emit-ir` 是数据导出模式：空 schema 也应出得成，退出码 0（不是判定结论）。"""
    path = tmp_path / "empty.avsc"
    path.write_text('{"type": "record", "name": "Order", "fields": []}', encoding="utf-8")
    code, out, _ = run([str(path), str(path), "--emit-ir"])
    assert code == 0
    assert '"fields": []' in out


def test_jsonschema_without_properties_yields_empty_ir(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text('{"type": "object", "title": "Order"}', encoding="utf-8")
    ir = parse(str(path))
    assert ir.format == "jsonschema"
    assert ir.name == "Order"
    assert ir.fields == ()
    assert ir.meta["required"] == []
    assert ir.meta["field_count"] == 0


def test_proto_message_without_fields_yields_empty_ir(tmp_path):
    pb = pytest.importorskip("google.protobuf.descriptor_pb2")
    builder = pb.FileDescriptorSet()
    file_proto = builder.file.add()
    file_proto.name = "order.proto"
    file_proto.package = "example.invalid.contracts"
    file_proto.syntax = "proto3"
    file_proto.message_type.add().name = "Order"  # 空 message
    path = tmp_path / "empty.pb"
    path.write_bytes(builder.SerializeToString(deterministic=True))

    ir = parse(str(path))
    assert ir.format == "proto"
    assert ir.name == "Order"
    assert ir.fields == ()
    assert ir.meta["messages"][0]["fields"] == []
    assert dumps(to_json(parse(str(path)))) == dumps(to_json(ir))  # 空 IR 也必须双跑一致
