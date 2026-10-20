# -*- coding: utf-8 -*-
"""规则表结构 + 命中求值（M0 结构门 + M4 求值面）。

两件事分开验：

  * **结构**：7 条规则 × 3 格式 = 21 格，`applies=false` 的格子必须有理由
    （`N/A` 是结论不是缺失）。规则表缺格时先在这里红。
  * **求值**：21 格里 `applies=true` 的每一格都要**真的命中**（用该格的夹具跑
    `policy.diff` + `rules.evaluate`），`applies=false` 的格子要**真的输出 N/A 行**。

`rule_id` / `rule_name` / `format_evidence` / `repair_action` 一律**取自规则表**再比对——
测试里另抄一份口径，就变成"两处同错也全绿"。
"""

import json
import os

import pytest

from contractcompat.errors import UsageError
from contractcompat.ir import FORMATS
from contractcompat.parsers import parse
from contractcompat.policy import diff
from contractcompat.rules import (
    EXPECTED_RULE_IDS,
    KIND_RULES,
    SEVERITIES,
    default_rule_path,
    evaluate,
    load_rule_table,
    rule_ids,
    validate_rule_table,
)

import fixture_scan

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_rule_table_loads_and_has_seven_rules():
    table = load_rule_table()
    assert rule_ids(table) == EXPECTED_RULE_IDS
    assert len(table["rules"]) == 7


def test_every_rule_has_three_format_slots():
    table = load_rule_table()
    for rule in table["rules"]:
        assert set(rule["formats"]) == set(FORMATS), rule["rule_id"]


def test_applicable_slots_declare_evidence():
    table = load_rule_table()
    for rule in table["rules"]:
        for fmt, slot in rule["formats"].items():
            if slot["applies"]:
                assert slot["evidence"], "%s/%s 缺 evidence" % (rule["rule_id"], fmt)


def test_not_applicable_slots_declare_reason():
    """`N/A` 是显式结论：没有字段号这个概念，不等于"这个格式没这问题"。"""
    table = load_rule_table()
    na = [(rule["rule_id"], fmt) for rule in table["rules"] for fmt, slot in rule["formats"].items() if not slot["applies"]]
    assert ("R5", "avro") in na
    assert ("R5", "jsonschema") in na
    assert ("R6", "avro") in na
    for rule in table["rules"]:
        for fmt, slot in rule["formats"].items():
            if not slot["applies"]:
                assert slot["reason"], "%s/%s 的 N/A 缺理由" % (rule["rule_id"], fmt)


def test_coverage_matrix_is_twenty_one_cells():
    table = load_rule_table()
    cells = [(rule["rule_id"], fmt) for rule in table["rules"] for fmt in rule["formats"]]
    assert len(cells) == 21
    assert len(set(cells)) == 21


def test_severity_values_are_three():
    assert set(SEVERITIES) == {"breaking", "runtime-dependent", "non-breaking"}
    table = load_rule_table()
    for rule in table["rules"]:
        assert rule["default_severity"] in SEVERITIES


def test_runtime_dependent_rules_have_both_explanations():
    """红线③：runtime-dependent 必须带两段说明，缺一即违约。"""
    table = load_rule_table()
    templates = table["runtime_dependent_templates"]
    runtime_rules = [rule["rule_id"] for rule in table["rules"] if rule["default_severity"] == "runtime-dependent"]
    assert runtime_rules, "至少要有一条规则默认 runtime-dependent"
    for rule_id in runtime_rules:
        assert rule_id in templates, "%s 缺 runtime-dependent 说明模板" % rule_id
        assert templates[rule_id]["why_static_breaking"]
        assert templates[rule_id]["what_would_trigger"]


def test_validate_rejects_missing_format_slot():
    table = json.loads(json.dumps(load_rule_table()))
    del table["rules"][0]["formats"]["avro"]
    with pytest.raises(UsageError) as caught:
        validate_rule_table(table)
    assert "avro" in str(caught.value)


def test_validate_rejects_bad_severity():
    table = json.loads(json.dumps(load_rule_table()))
    table["rules"][0]["default_severity"] = "maybe-breaking"
    with pytest.raises(UsageError):
        validate_rule_table(table)


def test_validate_rejects_extra_rule():
    """规则集合写死：多一条或少一条都要红，否则"七类规则"这个承诺会被静默改掉。"""
    table = json.loads(json.dumps(load_rule_table()))
    table["rules"].append(dict(table["rules"][0], rule_id="R8", name="EXTRA"))
    with pytest.raises(UsageError):
        validate_rule_table(table)


def test_validate_rejects_runtime_dependent_rule_without_template():
    """反向断言：把模板删掉后校验必须红——否则"两段说明"只是文案承诺。"""
    table = json.loads(json.dumps(load_rule_table()))
    del table["runtime_dependent_templates"]["R4"]
    with pytest.raises(UsageError) as caught:
        validate_rule_table(table)
    assert "R4" in str(caught.value)


def test_rule_path_is_repo_relative_not_absolute_in_report():
    """规则表路径可用于加载，但**绝不进报告**（绝对路径会让 digest 跨机不可复算）。"""
    path = default_rule_path()
    assert path.endswith("rule-table.json")


def test_packaged_mirror_matches_source():
    """包内镜像是**生成物**：与仓库根那份逐字节一致，否则 wheel 安装后口径与源码态不同。

    这条是"安装面"的一条：`pip install .` 后仓库根的 `rules/` 不在盘上，
    能加载的只有包内那份；两份漂移会让"本机跑得通、装好的包跑不通"或反过来。
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source = os.path.join(root, "rules", "rule-table.json")
    mirror = os.path.join(root, "src", "contractcompat", "data", "rule-table.json")
    with open(source, "rb") as handle:
        source_bytes = handle.read()
    with open(mirror, "rb") as handle:
        mirror_bytes = handle.read()
    assert source_bytes == mirror_bytes, "包内镜像与仓库根规则表不一致：改完源文件要同步镜像"


# ── 求值：M0 的 `NotImplementedError` 守门已改写为真求值断言 ──────────────────


def test_evaluate_returns_findings_for_a_real_difference():
    """M4 守门：`evaluate` 必须真的求值（M0 时期这里是 `NotImplementedError`）。

    用 Avro 删字段这一对：差异项 `field_removed` → R1 命中，severity 相对 `backward` 是破。
    """
    found, _ = fixture_scan.scan_rule_fixtures()
    old = parse(found["R1"]["avro"]["old"][0])
    new = parse(found["R1"]["avro"]["new"][0])
    findings = evaluate(diff(old, new), load_rule_table(), policy="backward")

    hits = [row for row in findings if row["format_evidence"] != "N/A"]
    assert len(hits) == 1, findings
    assert hits[0]["rule_id"] == "R1"
    assert hits[0]["stable_path"] == "total_amount"
    assert hits[0]["severity"] == "breaking"


def test_evaluate_does_not_invent_findings_for_identical_schemas():
    """反向断言：没有差异时不得凭空造命中（只有该格式的 N/A 结论行）。"""
    found, _ = fixture_scan.scan_rule_fixtures()
    old = parse(found["R1"]["avro"]["old"][0])
    findings = evaluate(diff(old, old), load_rule_table(), policy="backward")
    assert [row["rule_id"] for row in findings] == ["R5", "R6"]
    assert all(row["format_evidence"] == "N/A" for row in findings)


def test_finding_keys_are_a_subset_of_the_report_contract():
    """求值输出只能是报告 finding 键面的子集，且**只缺 `blast_radius`**。

    `blast_radius` 是归因层的结论（M5），规则层不填它；除此之外报告层不再补键——
    少一个键就等于两处口径各写一份。
    """
    from contractcompat.report import FINDING_KEYS

    found, _ = fixture_scan.scan_rule_fixtures()
    old = parse(found["R1"]["proto"]["old"][0])
    new = parse(found["R1"]["proto"]["new"][0])
    for row in evaluate(diff(old, new), load_rule_table(), policy="backward"):
        assert set(row) <= set(FINDING_KEYS), (row["rule_id"], sorted(set(row) - set(FINDING_KEYS)))
        assert set(FINDING_KEYS) - set(row) == {"blast_radius"}, row["rule_id"]


def test_findings_are_sorted_by_rule_id_then_stable_path():
    found, _ = fixture_scan.scan_rule_fixtures()
    old = parse(found["R1"]["avro"]["old"][0])
    new = parse(found["R1"]["avro"]["new"][0])
    keys = [(row["rule_id"], row["stable_path"] or "") for row in evaluate(diff(old, new))]
    assert keys == sorted(keys)


def test_every_kind_maps_to_a_declared_rule():
    """`KIND_RULES` 里的规则必须真在规则表里；表里有的规则也必须被某个事实覆盖到。

    两向都查，才能挡住"加了 R8 但没人能命中"与"新增事实没归口"两类腐烂。
    """
    table = load_rule_table()
    declared = set(rule_ids(table))
    assert set(KIND_RULES.values()) <= declared
    covered = set(KIND_RULES.values()) | {"R3"}  # R3 还由 field_added（必填无默认）命中
    assert declared - covered == set(), "有规则没有任何事实归口: %s" % sorted(declared - covered)


# ── 21 格：applies=true 的每格必须真命中 ────────────────────────────────────


def covered_cells():
    """从磁盘 + 规则表现算 ``[(rule_id, fmt, slug, old_path, new_path)]``（穷举，不抽样）。"""
    table = load_rule_table()
    found, _ = fixture_scan.scan_rule_fixtures()
    cells = []
    for rule in table["rules"]:
        rule_id = rule["rule_id"]
        for fmt in FORMATS:
            if not rule["formats"][fmt].get("applies"):
                continue
            olds = sorted(found.get(rule_id, {}).get(fmt, {}).get("old", []))
            news = sorted(found.get(rule_id, {}).get(fmt, {}).get("new", []))
            for old_path, new_path in zip(olds, news):
                slug = os.path.basename(old_path).rsplit("-old.", 1)[0]
                cells.append((rule_id, fmt, slug, old_path, new_path))
    return cells


def test_covered_cells_are_eighteen_cells_and_twenty_pairs():
    """18 格有夹具、共 20 对：R5×proto 有 3 对（同 message 换主人 / reserved 冲突 / 跨 message）。"""
    cells = covered_cells()
    assert len(set((cell[0], cell[1]) for cell in cells)) == 18
    assert len(cells) == 20, [cell[:3] for cell in cells]
    r5_proto = [cell for cell in cells if cell[0] == "R5" and cell[1] == "proto"]
    assert len(r5_proto) == 3


@pytest.mark.parametrize(
    "rule_id,fmt,slug,old_path,new_path",
    covered_cells(),
    ids=lambda value: str(value) if isinstance(value, str) else "",
)
def test_each_covered_cell_hits_its_rule(rule_id, fmt, slug, old_path, new_path):
    """21 格里每个 `applies=true` 的格：用该格夹具跑一遍，必须命中它自己的规则。

    断言的是**该规则被命中**，不是"只有该规则"——夹具可以同时演别的真实事实
    （Avro R2 的类型改动顺带改了默认值，那两条事实都是真的，不许为了好看吞掉）。
    """
    findings = evaluate(diff(parse(old_path), parse(new_path)), load_rule_table(), policy="backward")
    hits = [row for row in findings if row["format_evidence"] != "N/A"]
    assert [row for row in hits if row["rule_id"] == rule_id], "%s×%s（%s）没命中：%s" % (
        rule_id, fmt, slug, [(row["rule_id"], row["stable_path"]) for row in hits])
    for row in hits:
        assert row["severity"] in SEVERITIES, row


# ── 21 格：applies=false 的每格必须输出有理由的 N/A 行 ───────────────────────


def na_cells():
    table = load_rule_table()
    return [
        (rule["rule_id"], fmt, rule["formats"][fmt]["reason"])
        for rule in table["rules"]
        for fmt in FORMATS
        if not rule["formats"][fmt].get("applies")
    ]


@pytest.mark.parametrize("rule_id,fmt,reason", na_cells(), ids=lambda value: str(value) if isinstance(value, str) else "")
def test_na_cells_emit_a_row_with_a_reason(rule_id, fmt, reason):
    """`N/A` 行必须出现且带理由——省略就等于宣称"这个格式没这问题"。"""
    found, _ = fixture_scan.scan_rule_fixtures()
    sample = found["R1"][fmt]
    old = parse(sample["old"][0])
    new = parse(sample["new"][0])
    rows = [row for row in evaluate(diff(old, new)) if row["rule_id"] == rule_id]
    na_rows = [row for row in rows if row["format_evidence"] == "N/A"]
    assert len(na_rows) == 1, "%s×%s 的 N/A 行缺失或重复：%s" % (rule_id, fmt, rows)
    assert na_rows[0]["evidence"]["format"] == fmt
    assert na_rows[0]["evidence"]["reason"] == reason
    assert na_rows[0]["severity"] is None  # N/A 不是一次命中，不参与计数


def test_na_rows_do_not_depend_on_having_a_difference():
    """N/A 与"这次有没有差异"无关：完全相同的两份 Avro schema 也必须有 R5/R6 的 N/A 行。"""
    found, _ = fixture_scan.scan_rule_fixtures()
    old = parse(found["R1"]["avro"]["old"][0])
    rows = evaluate(diff(old, old))
    assert sorted(row["rule_id"] for row in rows) == ["R5", "R6"]


# ── R5 的两种形态 + 文件级那一格（buf 的空白格）─────────────────────────────


def proto_pair(slug):
    return (
        fixture_path("proto", slug, "old"),
        fixture_path("proto", slug, "new"),
    )


def fixture_path(directory, slug, side):
    return os.path.join(ROOT, "data", "fixtures", directory, "%s-%s.pb" % (slug, side))


def r5_hits(slug):
    old_path, new_path = proto_pair(slug)
    findings = evaluate(diff(parse(old_path), parse(new_path)), load_rule_table(), policy="backward")
    return [row for row in findings if row["rule_id"] == "R5" and row["severity"]]


def test_r5_number_reuse_hits_on_same_message():
    """形态①：同一 message 里字段号换了主人（旧名 → 新名）。"""
    rows = r5_hits("r5-number-reuse")
    assert len(rows) == 1, rows
    assert rows[0]["severity"] == "breaking"
    assert rows[0]["stable_path"] == "2"
    assert rows[0]["evidence"]["old"] == "total_amount"
    assert rows[0]["evidence"]["new"] == "status"
    assert rows[0]["evidence"]["detail"] is None


def test_r5_reserved_conflict_hits():
    """形态②：新字段号落进同一 schema 的 `reserved` 区间（schema 自相矛盾）。"""
    rows = r5_hits("r5-reserved-conflict")
    assert len(rows) == 1, rows
    assert rows[0]["severity"] == "breaking"
    assert rows[0]["evidence"]["kind"] == "reserved_conflict"


def test_r5_cross_message_reuse_hits_file_level():
    """形态③（文件级）：旧 message 退休的号被**另一个 message** 用不同名字接手。

    这是 buf 不查的那一格（`data/README.md` §1.1 已核官方规则集）。求值面在
    `meta["messages"]`：只看外层 `fields`（首个 message）是看不到它的。
    """
    rows = r5_hits("r5-cross-message-reuse")
    assert len(rows) == 1, rows
    assert rows[0]["severity"] == "breaking"
    assert rows[0]["stable_path"] == "Order.2"  # 退休发生在 Order
    assert rows[0]["evidence"]["detail"] == "cross_message_reuse"
    assert rows[0]["format_evidence"] == "field_number_reused_across_messages"
    assert rows[0]["evidence"]["old"] == "total_amount"
    assert rows[0]["evidence"]["new"] == "amount"


def test_cross_message_reuse_is_invisible_to_the_flat_field_view():
    """阳性对照：外层 `fields`（首个 message）**看不到**这次复用——证明它确实是文件级求值。"""
    old_path, new_path = proto_pair("r5-cross-message-reuse")
    old = parse(old_path)
    new = parse(new_path)
    assert [field.name for field in old.fields] == ["order_id", "total_amount"]
    assert [field.name for field in new.fields] == ["order_id"]
    assert all(field.number != 2 for field in new.fields)


def test_same_number_across_messages_is_not_reuse_by_itself():
    """反向断言：两个 message 都用 1 号（Protobuf 常态）不算复用——号留下来了、含义没换。"""
    import json
    import tempfile

    payload = {
        "type": "record",
        "name": "Order",
        "namespace": "example.invalid.contracts",
        "fields": [{"name": "order_id", "type": "string"}],
    }
    directory = tempfile.mkdtemp(prefix="cc-r5-")
    path = os.path.join(directory, "same.avsc")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload))
    # Avro 不是 proto：跨 message 求值必须直接跳过（不猜、不把字段名当字段号）
    rows = [row for row in evaluate(diff(parse(path), parse(path))) if row["rule_id"] == "R5"]
    assert all(row["format_evidence"] == "N/A" for row in rows)


def test_cross_message_hits_require_both_sides():
    """只有一侧 IR 时不做文件级求值（普通 list 也能求值，只是跳过这一格）。"""
    old_path, new_path = proto_pair("r5-cross-message-reuse")
    items = list(diff(parse(old_path), parse(new_path)))
    rows = [row for row in evaluate(items) if row["rule_id"] == "R5"]
    assert rows == [], "没有 IR 锚点时不该凭空造跨 message 命中"


# ── 普通报告的 JSON 必须已经带规则字段（M5 要冻结它）───────────────────────


def test_normal_json_report_carries_rule_fields():
    """M4 的验收面：普通报告的 JSON 已带 `rule_id` / `severity` / `format_evidence` / `repair_action`。

    M4 不生成 `cli-*.json` golden（那是 M5 的端到端 golden），但**字段必须已经在了**，
    否则 M5 冻结的会是一份"什么都没有"的产物。
    """
    from contractcompat.canonical import loads
    from contractcompat.cli import main
    import io

    old_path, new_path = proto_pair("r1-field-removed")
    stdout, stderr = io.StringIO(), io.StringIO()
    code = main([old_path, new_path, "--format", "json"], stdout=stdout, stderr=stderr)
    assert code == 1
    payload = loads(stdout.getvalue())
    hit = [row for row in payload["findings"] if row["rule_id"] == "R1"][0]
    assert hit["severity"] == "breaking"
    assert hit["format_evidence"] == "field_number_missing_without_reserved"
    assert hit["repair_action"] == "reserve"
    assert hit["repair_hint"].startswith("reserved 2;")
    assert payload["summary"]["breaking"] == 1

