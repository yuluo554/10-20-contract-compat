# data/golden · 冻结产物与期望值台账

> 生成器：`data/tools/gen_golden.py`（**只调用 CLI**，不自己实现判定）。
> 序列化一律走 `canonical.dumps`（`sort_keys` / `indent=2` / LF / 恰好一个结尾换行）。
> `--check`：重生成到临时目录 → 与入库文件**逐字节**比对。

## 一、M1 冻结了什么（以及明确**没有**冻结什么）

| 产物 | 形态 | 状态 |
|---|---|---|
| `ir-<dir>-<slug>.json` × 27 | 规范 JSON：`{inputs, old, new, digest}`，两侧归一后的 IR | ✅ M1 冻结 |
| `policy-*.json`（七档 × 三格式方向性矩阵） | `verdict` / `findings[*].direction` / `severity` | ⬜ **待 M3 生成** |
| `cli-*.md` / `cli-*.json`（端到端输出） | CLI 的 md 与 json 两种渲染 | ⬜ **待 M5 生成** |

**为什么 M1 只冻 IR**：方向性判定（`policy.diff` / `policy.judge`）是 M3 的交付物，
七类规则的命中求值（`rules.evaluate`）是 M4 的。现在把 `verdict` / `severity` 写进
golden，等于**伪造期望值**——两份都不存在的"答案"对上，永远绿。

本文件 §二 的"预期命中"列记的是**夹具的设计意图**（这条夹具是为了演哪条规则而造的），
不是判定输出。判定输出要等 M3/M4 产出后，由生成器重新落盘并在这里登记。

## 二、golden 台账（27 份）

> 这张表与磁盘**双向对账**：表里有而盘上没有 → 红；盘上有而表里没有 → 红
> （`tests/test_golden.py::test_readme_golden_table_is_bidirectional`）。

| golden 文件 | fixture slug | 目录 | 设计意图（演哪条规则） | 判定值 |
|---|---|---|---|---|
| `ir-proto-r1-field-removed.json` | `r1-field-removed` | proto | R1 删字段号且未 reserved | 待 M3 |
| `ir-proto-r2-type-changed.json` | `r2-type-changed` | proto | R2 `int32 → string`（wire 不兼容） | 待 M3 |
| `ir-proto-r3-requiredness.json` | `r3-requiredness` | proto | R3 `optional → required`（proto2 label） | 待 M3 |
| `ir-proto-r4-enum-narrowed.json` | `r4-enum-narrowed` | proto | R4 enum 删值 | 待 M3 |
| `ir-proto-r5-number-reuse.json` | `r5-number-reuse` | proto | R5 同一号换主人（复用） | 待 M3 |
| `ir-proto-r5-reserved-conflict.json` | `r5-reserved-conflict` | proto | R5 新字段号落进 `reserved` | 待 M3 |
| `ir-proto-r6-oneof-moved.json` | `r6-oneof-moved` | proto | R6 字段移出 `oneof` | 待 M3 |
| `ir-proto-r7-default-changed.json` | `r7-default-changed` | proto | R7 `default_value` 变化 | 待 M3 |
| `ir-avro-r1-field-removed.json` | `r1-field-removed` | avro | R1 字段从 `fields` 消失 | 待 M3 |
| `ir-avro-r2-type-changed.json` | `r2-type-changed` | avro | R2 `int → string` | 待 M3 |
| `ir-avro-r3-requiredness.json` | `r3-requiredness` | avro | R3 新增字段无 `default` | 待 M3 |
| `ir-avro-r4-enum-narrowed.json` | `r4-enum-narrowed` | avro | R4 `symbols` 删一个 | 待 M3 |
| `ir-avro-r7-default-changed.json` | `r7-default-changed` | avro | R7 `default` 变化 | 待 M3 |
| `ir-jsonschema-r1-field-removed.json` | `r1-field-removed` | jsonschema | R1 `properties` 键消失 | 待 M3 |
| `ir-jsonschema-r2-type-changed.json` | `r2-type-changed` | jsonschema | R2 `type: integer → string` | 待 M3 |
| `ir-jsonschema-r3-requiredness.json` | `r3-requiredness` | jsonschema | R3 加进 `required` | 待 M3 |
| `ir-jsonschema-r4-enum-narrowed.json` | `r4-enum-narrowed` | jsonschema | R4 `enum` 收窄 | 待 M3 |
| `ir-jsonschema-r6-oneof-moved.json` | `r6-oneof-moved` | jsonschema | R6 `oneOf` 分支移动 | 待 M3 |
| `ir-jsonschema-r7-default-changed.json` | `r7-default-changed` | jsonschema | R7 `default` 变化 | 待 M3 |
| `ir-jsonschema-ir-unsupported-patternproperties.json` | `ir-unsupported-patternproperties` | jsonschema | 不可表达：`patternProperties` | 待 M3 |
| `ir-jsonschema-ir-unsupported-if-then-else.json` | `ir-unsupported-if-then-else` | jsonschema | 不可表达：`if`/`then`/`else` | 待 M3 |
| `ir-jsonschema-ir-unsupported-recursive-ref.json` | `ir-unsupported-recursive-ref` | jsonschema | 不可表达：递归 `$ref` | 待 M3 |
| `ir-jsonschema-ir-unsupported-dependent-schemas.json` | `ir-unsupported-dependent-schemas` | jsonschema | 不可表达：`dependentSchemas` | 待 M3 |
| `ir-negatives-union-add-type.json` | `union-add-type` | negatives | 反例：Avro union 加类型不破 | 待 M3 |
| `ir-negatives-rename-with-alias.json` | `rename-with-alias` | negatives | 反例：改名带 `aliases` 不破 | 待 M3 |
| `ir-negatives-delete-reserved.json` | `delete-reserved` | negatives | 反例：删字段但号已 `reserved` 不破 | 待 M3 |
| `ir-negatives-add-optional-property.json` | `add-optional-property` | negatives | 反例：加可选 property 不破 | 待 M3 |

## 三、覆盖矩阵（由 `tests/test_fixtures.py` 计算并打印，不手填）

`7 规则 × 3 格式 = 21 格`。`N/A` 是**结论**不是缺格——R5 在 Avro / JSON Schema 下没有
字段号概念，R6 在 Avro 下没有 `oneof` 概念，规则表里标 `applies=false` 并给理由
（口径见 `data/README.md` §4.3）。

跑 `py -m pytest tests/test_fixtures.py -q -s` 会打印当前矩阵；覆盖不足或
"N/A 格却有夹具"都会红。

## 四、`--check` 的两层断言

```bash
py data/tools/gen_fixtures.py --check   # fixture 位级一致（.pb 是二进制）
py data/tools/gen_golden.py --check     # golden 位级一致
```

1. **产物形态**：入库文件能解析、`digest` 自洽、`inputs` 只写 basename（无绝对路径）；
2. **重生成**：重新跑 CLI → 与入库文件逐字节比对。

两层都过才算一致。只做第 1 层会漏掉"改了解析器但忘了重新生成 golden"；
只做第 2 层会漏掉"生成器和实现一起错"（不过生成器只调 CLI，这条风险已被结构消灭）。
