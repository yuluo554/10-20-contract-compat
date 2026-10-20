# -*- coding: utf-8 -*-
"""七档 policy、方向性差异项与 buf 四档映射。

M3 起本文件同时钉住两件事：
  * ``diff`` 只产出事实（新增/删除/类型变/基数变/默认值变/enum/oneof/字段号复用），
    每项带 direction；换 policy 不改 direction；
  * ``judge`` 把 direction × 七档映射成 verdict，transitive 逐历史版本重复 diff+judge。
"""

import os

import pytest

from contractcompat.errors import UsageError
from contractcompat.parsers import parse
from contractcompat.policy import (
    DIRECTIONS,
    MAPPING_NOTES,
    POLICIES,
    TRANSITIVE,
    VERDICTS,
    DiffResult,
    diff,
    judge,
    mapping_table,
    resolve_policy,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = {"proto": ".pb", "avro": ".avsc", "jsonschema": ".json"}


def fixture_path(directory, slug, side, fmt=None):
    fmt = fmt or directory
    return os.path.join(ROOT, "data", "fixtures", directory, "%s-%s%s" % (slug, side, EXT[fmt]))


def load_pair(directory, slug):
    return parse(fixture_path(directory, slug, "old")), parse(fixture_path(directory, slug, "new"))


def test_seven_policies_exist():
    """七档与 Confluent 对齐：三个方向 × {单版本, transitive} + none。"""
    assert set(POLICIES) == {
        "backward",
        "backward-transitive",
        "forward",
        "forward-transitive",
        "full",
        "full-transitive",
        "none",
    }
    assert len(POLICIES) == 7


def test_transitive_policies_are_three():
    assert set(TRANSITIVE) == {"backward-transitive", "forward-transitive", "full-transitive"}


def test_directions_and_verdicts_are_closed_enums():
    assert set(DIRECTIONS) == {"BACKWARD_OK", "FORWARD_OK", "BOTH_OK", "NONE_OK"}
    assert set(VERDICTS) == {"compatible", "breaking"}


def test_unknown_policy_rejected():
    with pytest.raises(UsageError) as caught:
        resolve_policy("sideways")
    assert "backward" in str(caught.value)


@pytest.mark.parametrize("policy", ["backward-transitive", "forward-transitive", "full-transitive"])
def test_transitive_requires_history(policy):
    """缺 --history 必须**拒绝**（退出码 2），不降级为单版本。

    降级的后果是把"与历史不兼容"静默报成"兼容"——这正是本工具要消除的误判。
    """
    with pytest.raises(UsageError) as caught:
        resolve_policy(policy)
    assert "--history" in str(caught.value)


@pytest.mark.parametrize("policy", ["backward-transitive", "forward-transitive", "full-transitive"])
def test_transitive_accepts_history(policy):
    assert resolve_policy(policy, ["v1.avsc"]) == policy


@pytest.mark.parametrize("policy", ["backward", "forward", "full", "none"])
def test_non_transitive_rejects_history(policy):
    """非 transitive 档收到 --history 是**参数矛盾**：静默忽略会让用户以为比较了历史。"""
    with pytest.raises(UsageError):
        resolve_policy(policy, ["v1.avsc"])


def test_mapping_table_has_four_rows():
    table = mapping_table()
    assert [row["policy"] for row in table["rows"]] == ["backward", "forward", "full", "none"]
    for row in table["rows"]:
        assert row["relation"], "每行必须带关系说明"
        assert row["buf_tier"]


def test_mapping_table_declares_not_equivalent():
    """`data/README.md` §4.2 的使用规则：整表必须含"只表达最接近、不宣称等价"。"""
    assert "只表达最接近" in MAPPING_NOTES
    assert "不宣称等价" in MAPPING_NOTES
    assert "不等价" in MAPPING_NOTES


def test_forward_has_no_direct_buf_equivalent():
    rows = {row["policy"]: row for row in mapping_table()["rows"]}
    assert "无直接对应" in rows["forward"]["buf_tier"]


def test_none_policy_documents_no_buf_tier():
    rows = {row["policy"]: row for row in mapping_table()["rows"]}
    assert "buf 无" in rows["none"]["relation"]


def test_mapping_table_is_a_copy():
    """调用方改返回值不得污染模块内常量（映射表是口径，不是可变状态）。"""
    table = mapping_table()
    table["rows"][0]["policy"] = "tampered"
    assert mapping_table()["rows"][0]["policy"] == "backward"


# ── M3：diff 只产出事实 ───────────────────────────────────────────────────


def test_diff_is_a_list_that_carries_both_irs():
    old, new = load_pair("avro", "r1-field-removed")
    result = diff(old, new)
    assert isinstance(result, DiffResult)
    assert isinstance(result, list)
    assert result.old == old and result.new == new


def test_every_difference_has_a_closed_direction():
    for directory, slug in (
        ("proto", "r1-field-removed"),
        ("avro", "r1-field-removed"),
        ("jsonschema", "r1-field-removed"),
        ("proto", "r2-type-changed"),
        ("avro", "r4-enum-narrowed"),
        ("jsonschema", "r6-oneof-moved"),
    ):
        old, new = load_pair(directory, slug)
        for item in diff(old, new):
            assert item["direction"] in DIRECTIONS, (directory, slug, item)
            assert item["kind"], (directory, slug, item)
            assert item["format"] == directory


def test_same_field_removal_has_same_direction_in_three_formats():
    """红线①的机械检查面：同一"删字段"在三格式下 direction 必须相同。"""
    directions = {}
    for directory in ("proto", "avro", "jsonschema"):
        old, new = load_pair(directory, "r1-field-removed")
        removed = [item for item in diff(old, new) if item["kind"] == "field_removed"]
        assert len(removed) == 1, (directory, removed)
        directions[directory] = removed[0]["direction"]
    assert set(directions.values()) == {"FORWARD_OK"}, directions
    assert directions["proto"] == directions["avro"] == directions["jsonschema"]


def test_field_removal_breaks_backward_not_forward_in_three_formats():
    """题面验收：同一个"删字段"三格式都 backward 破、forward 不破。"""
    for directory in ("proto", "avro", "jsonschema"):
        old, new = load_pair(directory, "r1-field-removed")
        d = diff(old, new)
        assert judge(d, "backward") == "breaking", directory
        assert judge(d, "forward") == "compatible", directory


def test_direction_does_not_depend_on_policy():
    """direction 是事实、policy 是选择：七档怎么换都不改 direction。"""
    old, new = load_pair("avro", "r3-requiredness")
    d = diff(old, new)
    before = [item["direction"] for item in d]
    for name in POLICIES:
        judge(d, name, [old] if name in TRANSITIVE else ())
        assert [item["direction"] for item in d] == before


def test_diff_is_deterministic():
    for directory, slug in (("proto", "r6-oneof-moved"), ("jsonschema", "r4-enum-narrowed")):
        old, new = load_pair(directory, slug)
        assert diff(old, new) == diff(old, new)


def test_diff_rejects_mixed_formats():
    avro = parse(fixture_path("avro", "r1-field-removed", "old"))
    schema = parse(fixture_path("jsonschema", "r1-field-removed", "old"))
    with pytest.raises(UsageError) as caught:
        diff(avro, schema)
    assert "格式不同" in str(caught.value)


# ── M3：七档 verdict ───────────────────────────────────────────────────────


def test_seven_policies_each_have_a_verdict():
    """七档各一条：三档单版本 + 三档 transitive + none。"""
    old_r1, new_r1 = load_pair("avro", "r1-field-removed")
    old_r7, new_r7 = load_pair("avro", "r7-default-changed")
    cases = (
        ("backward", diff(old_r1, new_r1), (), "breaking"),
        ("backward-transitive", diff(old_r1, new_r1), (old_r1,), "breaking"),
        ("forward", diff(old_r1, new_r1), (), "compatible"),
        ("forward-transitive", diff(old_r1, new_r1), (old_r1,), "compatible"),
        ("full", diff(old_r7, new_r7), (), "compatible"),
        ("full-transitive", diff(old_r7, new_r7), (old_r7,), "compatible"),
        ("none", diff(old_r1, new_r1), (), "compatible"),
    )
    assert [case[0] for case in cases] == list(POLICIES)
    for name, differences, history, expected in cases:
        assert judge(differences, name, history) == expected, name
        assert judge(differences, name, history) in VERDICTS


def test_none_lists_every_difference_but_is_always_compatible():
    old, new = load_pair("avro", "r1-field-removed")
    d = diff(old, new)
    assert d, "none 档不得吞掉差异项"
    assert judge(d, "none") == "compatible"
    assert judge(d, "backward") == "breaking"  # 同一份事实，换档才是 breaking


def test_transitive_checks_every_history_version():
    """当前对 backward 兼容，但历史版本里有被删字段 → transitive 必须破。"""
    old_r7, new_r7 = load_pair("avro", "r7-default-changed")
    old_r1 = parse(fixture_path("avro", "r1-field-removed", "old"))
    current = diff(old_r7, new_r7)
    assert current and all(item["direction"] == "BOTH_OK" for item in current)
    assert judge(current, "backward") == "compatible"
    assert judge(current, "backward-transitive", [old_r1]) == "breaking"


def test_transitive_accepts_precomputed_history_differences():
    old_r7, new_r7 = load_pair("avro", "r7-default-changed")
    old_r1 = parse(fixture_path("avro", "r1-field-removed", "old"))
    current = diff(old_r7, new_r7)
    historical = diff(old_r1, new_r7)
    assert judge(current, "backward-transitive", [historical]) == "breaking"


def test_judge_rejects_unknown_policy():
    old, new = load_pair("avro", "r1-field-removed")
    with pytest.raises(UsageError):
        judge(diff(old, new), "sideways")


# ── 各类事实的方向 ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "directory,slug,kind,direction",
    [
        ("proto", "r2-type-changed", "type_changed", "NONE_OK"),
        ("proto", "r3-requiredness", "cardinality_changed", "BACKWARD_OK"),
        ("proto", "r4-enum-narrowed", "enum_narrowed", "BACKWARD_OK"),
        ("proto", "r5-number-reuse", "field_number_reused", "NONE_OK"),
        ("proto", "r5-reserved-conflict", "reserved_conflict", "NONE_OK"),
        ("proto", "r6-oneof-moved", "oneof_moved", "BOTH_OK"),
        ("proto", "r7-default-changed", "default_changed", "BOTH_OK"),
        ("avro", "r2-type-changed", "type_changed", "NONE_OK"),
        ("avro", "r3-requiredness", "field_added", "BACKWARD_OK"),
        ("avro", "r4-enum-narrowed", "enum_narrowed", "BACKWARD_OK"),
        ("avro", "r7-default-changed", "default_changed", "BOTH_OK"),
        ("jsonschema", "r2-type-changed", "type_changed", "NONE_OK"),
        ("jsonschema", "r3-requiredness", "cardinality_changed", "BACKWARD_OK"),
        ("jsonschema", "r4-enum-narrowed", "enum_narrowed", "BACKWARD_OK"),
        ("jsonschema", "r6-oneof-moved", "oneof_moved", "NONE_OK"),
        ("jsonschema", "r7-default-changed", "default_changed", "BOTH_OK"),
    ],
)
def test_fact_direction(directory, slug, kind, direction):
    old, new = load_pair(directory, slug)
    matches = [item for item in diff(old, new) if item["kind"] == kind]
    assert matches, "%s/%s 没有产出 %s" % (directory, slug, kind)
    assert matches[0]["direction"] == direction


def test_rename_with_alias_is_not_remove_plus_add():
    """反例：改名但新侧声明 aliases 含旧名 → 不判 remove+add。"""
    old = parse(fixture_path("negatives", "rename-with-alias", "old", fmt="avro"))
    new = parse(fixture_path("negatives", "rename-with-alias", "new", fmt="avro"))
    assert diff(old, new) == []


def test_deleting_reserved_field_is_not_a_removal_fact():
    old = parse(fixture_path("negatives", "delete-reserved", "old", fmt="proto"))
    new = parse(fixture_path("negatives", "delete-reserved", "new", fmt="proto"))
    assert diff(old, new) == []


def test_union_branch_added_is_forward_ok():
    """反例：Avro union 加分支不是"看到类型变就报破"；方向只说明旧读新不保证。"""
    old = parse(fixture_path("negatives", "union-add-type", "old", fmt="avro"))
    new = parse(fixture_path("negatives", "union-add-type", "new", fmt="avro"))
    items = [item for item in diff(old, new) if item["kind"] == "type_changed"]
    assert len(items) == 1
    assert items[0]["direction"] == "FORWARD_OK"
    assert items[0]["detail"] == "union_widened"


def test_add_optional_property_is_both_ok():
    old = parse(fixture_path("negatives", "add-optional-property", "old", fmt="jsonschema"))
    new = parse(fixture_path("negatives", "add-optional-property", "new", fmt="jsonschema"))
    items = [item for item in diff(old, new) if item["kind"] == "field_added"]
    assert items and items[0]["direction"] == "BOTH_OK"


# ── 判定只依赖 IR：改文件名 / 字段声明顺序不改变结论 ──────────────────────


def test_verdict_ignores_filename_and_declaration_order(tmp_path):
    """同一语义、不同文件名、不同字段声明顺序 → 同一份 diff 与同一组 verdict。"""
    import json

    old_payload = {
        "type": "record",
        "name": "Order",
        "namespace": "example.invalid.contracts",
        "fields": [
            {"name": "order_id", "type": "string"},
            {"name": "total_amount", "type": "long", "default": 0},
        ],
    }
    new_payload = {
        "type": "record",
        "name": "Order",
        "namespace": "example.invalid.contracts",
        "fields": [{"name": "order_id", "type": "string"}],
    }
    reversed_old = dict(old_payload, fields=list(reversed(old_payload["fields"])))

    baseline_old = tmp_path / "a.avsc"
    baseline_new = tmp_path / "b.avsc"
    shuffled_old = tmp_path / "zzz-renamed.avsc"
    shuffled_new = tmp_path / "yyy-renamed.avsc"
    baseline_old.write_text(json.dumps(old_payload), encoding="utf-8")
    baseline_new.write_text(json.dumps(new_payload), encoding="utf-8")
    shuffled_old.write_text(json.dumps(reversed_old), encoding="utf-8")
    shuffled_new.write_text(json.dumps(new_payload), encoding="utf-8")

    first = diff(parse(str(baseline_old)), parse(str(baseline_new)))
    second = diff(parse(str(shuffled_old)), parse(str(shuffled_new)))
    assert first == second
    for name in POLICIES:
        history_first = [parse(str(baseline_old))] if name in TRANSITIVE else ()
        history_second = [parse(str(shuffled_old))] if name in TRANSITIVE else ()
        assert judge(first, name, history_first) == judge(second, name, history_second), name


def test_json_schema_enum_reorder_is_not_a_fact(tmp_path):
    """JSON Schema 的 enum 是集合语义：只换顺序不是差异（Avro 的下标会变，那是另一回事）。"""
    import json

    def write(name, values):
        payload = {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": values}},
            "required": ["status"],
        }
        path = tmp_path / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return parse(str(path))

    old = write("old.json", ["STATUS_UNSPECIFIED", "PENDING"])
    new = write("new.json", ["PENDING", "STATUS_UNSPECIFIED"])
    assert diff(old, new) == []
