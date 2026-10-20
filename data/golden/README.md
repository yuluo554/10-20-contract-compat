# data/golden · 冻结产物与期望值台账

> 生成器：`data/tools/gen_golden.py`（**只调用 CLI**，不自己实现判定）。
> 序列化一律走 `canonical.dumps`（`sort_keys` / `indent=2` / LF / 恰好一个结尾换行）。
> `--check`：重生成到临时目录 → 与入库文件**逐字节**比对。

## 一、冻结了什么（以及明确**没有**冻结什么）

| 产物 | 形态 | 状态 |
|---|---|---|
| `ir-<dir>-<slug>.json` × 28 | 规范 JSON：`{inputs, old, new, digest}`，两侧归一后的 IR | ✅ M1 冻结 |
| `policy-<dir>-<slug>.json` × 28 | 规范 JSON：`{inputs, format, differences[], verdicts{}, history[], notes[], digest}`，**方向性事实 + 七档矩阵** | ✅ M3 冻结 |
| `cli-<dir>-<slug>.{md,json}` × 56 | 端到端报告：`--policy backward --deploy-order consumers-first` 下 CLI 的 md 与 json 两种渲染，**承载三值 `severity` 与 `blast_radius`** | ✅ M5 冻结 |
| `cli-proto-r1-field-removed-order-<顺序>.{md,json}` × 6 | **四态四联**的另三档：`producers-first` / `simultaneous` / `replay` 各一份 md + json（`consumers-first` 那档由上面的 56 份承载）；同一破例四种发布顺序归因不同 | ✅ M5 冻结 |

**端到端 golden 的固定口径**：policy = `backward`、deploy-order = `consumers-first`（默认档）。
报告退出码 0/1 都是"判定已完成"（compatible / breaking），生成器都接受；2/3 是输入或环境问题，必红。
`severity` 从 M5 起由端到端 golden 承载；**policy golden 仍不含它**（那是规则库的维度）。

**为什么 M3 的 policy golden 不含 `severity`**：方向（`direction`）是判定核的事实，七档 `verdict`
是判定核的选择；`severity` 是 M4 规则库的第三维。现在把 severity 写进 golden，等于伪造 M4 的期望值。
M4 接上 `rules.evaluate` 后，端到端 golden（M5）才承载 severity。

**policy golden 的 transitive 基线**：生成器用 `--emit-policy --history <old>`，即把每对夹具的
**old 作为唯一历史版本**。因此七档 verdict 全部是真算出来的；文件里的 `history` 字段如实记录该基线。
没有 `--history` 时 CLI 会把三档 transitive 写成 `null` 并在 `notes` 说明——**不拿单版本冒充 transitive**。

**policy golden 只覆盖可表达的字段差异**：`ir_unsupported` 由同名的 IR golden 承载（`--emit-policy`
不重复列出不可表达构造）；读者看"兼容"结论时必须同时看 IR golden 的 `ir_unsupported`。

> §二 的"预期命中"列记的是**夹具的设计意图**（这条夹具是为了演哪条规则而造的），
> 不是判定输出。M3 的判定输出已由 `policy-*.json` 落盘并登记在 §二·policy 台账。

## 二、golden 台账（IR ×28 + policy ×28 + CLI 端到端 ×62）

> 这张表与磁盘**双向对账**（IR / policy 逐份点名）：表里有而盘上没有 → 红；盘上有而表里没有 → 红
> （`tests/test_golden.py::test_readme_golden_table_is_bidirectional`）。
> CLI 端到端 golden 按**配对数**对账（每对 2 份 md/json + 四态四联样例的另 3 档 ×2），
> 名单由生成器现算，不逐份手抄（`tests/test_golden.py` 的 `cli_files()` 断言份数与名单闭合）。

| golden 文件 | fixture slug | 目录 | 设计意图（演哪条规则） | 判定值 |
|---|---|---|---|---|
| `ir-proto-r1-field-removed.json` | `r1-field-removed` | proto | R1 删字段号且未 reserved | 见 §二·policy 台账 |
| `ir-proto-r2-type-changed.json` | `r2-type-changed` | proto | R2 `int32 → string`（wire 不兼容） | 见 §二·policy 台账 |
| `ir-proto-r3-requiredness.json` | `r3-requiredness` | proto | R3 `optional → required`（proto2 label） | 见 §二·policy 台账 |
| `ir-proto-r4-enum-narrowed.json` | `r4-enum-narrowed` | proto | R4 enum 删值 | 见 §二·policy 台账 |
| `ir-proto-r5-number-reuse.json` | `r5-number-reuse` | proto | R5 同一号换主人（复用） | 见 §二·policy 台账 |
| `ir-proto-r5-cross-message-reuse.json` | `r5-cross-message-reuse` | proto | R5 跨 message 复用（buf 空白格；`meta.messages` 文件级求值） | 见 §二·policy 台账 |
| `ir-proto-r5-reserved-conflict.json` | `r5-reserved-conflict` | proto | R5 新字段号落进 `reserved` | 见 §二·policy 台账 |
| `ir-proto-r6-oneof-moved.json` | `r6-oneof-moved` | proto | R6 字段移出 `oneof` | 见 §二·policy 台账 |
| `ir-proto-r7-default-changed.json` | `r7-default-changed` | proto | R7 `default_value` 变化 | 见 §二·policy 台账 |
| `ir-avro-r1-field-removed.json` | `r1-field-removed` | avro | R1 字段从 `fields` 消失 | 见 §二·policy 台账 |
| `ir-avro-r2-type-changed.json` | `r2-type-changed` | avro | R2 `int → string` | 见 §二·policy 台账 |
| `ir-avro-r3-requiredness.json` | `r3-requiredness` | avro | R3 新增字段无 `default` | 见 §二·policy 台账 |
| `ir-avro-r4-enum-narrowed.json` | `r4-enum-narrowed` | avro | R4 `symbols` 删一个 | 见 §二·policy 台账 |
| `ir-avro-r7-default-changed.json` | `r7-default-changed` | avro | R7 `default` 变化 | 见 §二·policy 台账 |
| `ir-jsonschema-r1-field-removed.json` | `r1-field-removed` | jsonschema | R1 `properties` 键消失 | 见 §二·policy 台账 |
| `ir-jsonschema-r2-type-changed.json` | `r2-type-changed` | jsonschema | R2 `type: integer → string` | 见 §二·policy 台账 |
| `ir-jsonschema-r3-requiredness.json` | `r3-requiredness` | jsonschema | R3 加进 `required` | 见 §二·policy 台账 |
| `ir-jsonschema-r4-enum-narrowed.json` | `r4-enum-narrowed` | jsonschema | R4 `enum` 收窄 | 见 §二·policy 台账 |
| `ir-jsonschema-r6-oneof-moved.json` | `r6-oneof-moved` | jsonschema | R6 `oneOf` 分支移动 | 见 §二·policy 台账 |
| `ir-jsonschema-r7-default-changed.json` | `r7-default-changed` | jsonschema | R7 `default` 变化 | 见 §二·policy 台账 |
| `ir-jsonschema-ir-unsupported-patternproperties.json` | `ir-unsupported-patternproperties` | jsonschema | 不可表达：`patternProperties` | 见 §二·policy 台账 |
| `ir-jsonschema-ir-unsupported-if-then-else.json` | `ir-unsupported-if-then-else` | jsonschema | 不可表达：`if`/`then`/`else` | 见 §二·policy 台账 |
| `ir-jsonschema-ir-unsupported-recursive-ref.json` | `ir-unsupported-recursive-ref` | jsonschema | 不可表达：递归 `$ref` | 见 §二·policy 台账 |
| `ir-jsonschema-ir-unsupported-dependent-schemas.json` | `ir-unsupported-dependent-schemas` | jsonschema | 不可表达：`dependentSchemas` | 见 §二·policy 台账 |
| `ir-negatives-union-add-type.json` | `union-add-type` | negatives | 反例：Avro union 加类型不破 | 见 §二·policy 台账 |
| `ir-negatives-rename-with-alias.json` | `rename-with-alias` | negatives | 反例：改名带 `aliases` 不破 | 见 §二·policy 台账 |
| `ir-negatives-delete-reserved.json` | `delete-reserved` | negatives | 反例：删字段但号已 `reserved` 不破 | 见 §二·policy 台账 |
| `ir-negatives-add-optional-property.json` | `add-optional-property` | negatives | 反例：加可选 property 不破 | 见 §二·policy 台账 |

### policy 台账（28 份：方向事实 + 七档矩阵）

> `backward / forward / full / none` 四列是 verdict（`compatible` / `breaking`）；
> 三档 transitive 也在文件里，基线 = 同目录 old（见 §一）。`none` 恒 `compatible`。

| golden 文件 | fixture slug | 目录 | backward / forward / full / none |
|---|---|---|---|
| `policy-proto-r1-field-removed.json` | `r1-field-removed` | proto | breaking / compatible / breaking / compatible |
| `policy-proto-r2-type-changed.json` | `r2-type-changed` | proto | breaking / breaking / breaking / compatible |
| `policy-proto-r3-requiredness.json` | `r3-requiredness` | proto | compatible / breaking / breaking / compatible |
| `policy-proto-r4-enum-narrowed.json` | `r4-enum-narrowed` | proto | compatible / breaking / breaking / compatible |
| `policy-proto-r5-number-reuse.json` | `r5-number-reuse` | proto | breaking / breaking / breaking / compatible |
| `policy-proto-r5-cross-message-reuse.json` | `r5-cross-message-reuse` | proto | breaking / compatible / breaking / compatible |
| `policy-proto-r5-reserved-conflict.json` | `r5-reserved-conflict` | proto | breaking / breaking / breaking / compatible |
| `policy-proto-r6-oneof-moved.json` | `r6-oneof-moved` | proto | compatible / compatible / compatible / compatible |
| `policy-proto-r7-default-changed.json` | `r7-default-changed` | proto | compatible / compatible / compatible / compatible |
| `policy-avro-r1-field-removed.json` | `r1-field-removed` | avro | breaking / compatible / breaking / compatible |
| `policy-avro-r2-type-changed.json` | `r2-type-changed` | avro | breaking / breaking / breaking / compatible |
| `policy-avro-r3-requiredness.json` | `r3-requiredness` | avro | compatible / breaking / breaking / compatible |
| `policy-avro-r4-enum-narrowed.json` | `r4-enum-narrowed` | avro | compatible / breaking / breaking / compatible |
| `policy-avro-r7-default-changed.json` | `r7-default-changed` | avro | compatible / compatible / compatible / compatible |
| `policy-jsonschema-r1-field-removed.json` | `r1-field-removed` | jsonschema | breaking / compatible / breaking / compatible |
| `policy-jsonschema-r2-type-changed.json` | `r2-type-changed` | jsonschema | breaking / breaking / breaking / compatible |
| `policy-jsonschema-r3-requiredness.json` | `r3-requiredness` | jsonschema | compatible / breaking / breaking / compatible |
| `policy-jsonschema-r4-enum-narrowed.json` | `r4-enum-narrowed` | jsonschema | compatible / breaking / breaking / compatible |
| `policy-jsonschema-r6-oneof-moved.json` | `r6-oneof-moved` | jsonschema | breaking / breaking / breaking / compatible |
| `policy-jsonschema-r7-default-changed.json` | `r7-default-changed` | jsonschema | compatible / compatible / compatible / compatible |
| `policy-jsonschema-ir-unsupported-patternproperties.json` | `ir-unsupported-patternproperties` | jsonschema | compatible / compatible / compatible / compatible |
| `policy-jsonschema-ir-unsupported-if-then-else.json` | `ir-unsupported-if-then-else` | jsonschema | compatible / compatible / compatible / compatible |
| `policy-jsonschema-ir-unsupported-recursive-ref.json` | `ir-unsupported-recursive-ref` | jsonschema | compatible / compatible / compatible / compatible |
| `policy-jsonschema-ir-unsupported-dependent-schemas.json` | `ir-unsupported-dependent-schemas` | jsonschema | compatible / compatible / compatible / compatible |
| `policy-negatives-union-add-type.json` | `union-add-type` | negatives | breaking / compatible / breaking / compatible |
| `policy-negatives-rename-with-alias.json` | `rename-with-alias` | negatives | compatible / compatible / compatible / compatible |
| `policy-negatives-delete-reserved.json` | `delete-reserved` | negatives | compatible / compatible / compatible / compatible |
| `policy-negatives-add-optional-property.json` | `add-optional-property` | negatives | compatible / compatible / compatible / compatible |

## 三、覆盖矩阵（由 `tests/test_fixtures.py` 计算并打印，不手填）

`7 规则 × 3 格式 = 21 格`。`N/A` 是**结论**不是缺格——R5 在 Avro / JSON Schema 下没有
字段号概念，R6 在 Avro 下没有 `oneof` 概念，规则表里标 `applies=false` 并给理由
（口径见 `data/README.md` §4.3）。

跑 `py -m pytest tests/test_fixtures.py -q -s` 会打印当前矩阵；覆盖不足或
"N/A 格却有夹具"都会红。

## 四、`--check` 的两层断言

```bash
py data/tools/gen_fixtures.py --check   # fixture 位级一致（.pb 是二进制）
py data/tools/gen_golden.py --check     # IR + policy + CLI 端到端 golden 逐字节一致
```

1. **产物形态**：入库文件能解析、`digest` 自洽、`inputs` 只写 basename（无绝对路径）；
2. **重生成**：重新跑 CLI → 与入库文件逐字节比对。

两层都过才算一致。只做第 1 层会漏掉"改了解析器但忘了重新生成 golden"；
只做第 2 层会漏掉"生成器和实现一起错"（不过生成器只调 CLI，这条风险已被结构消灭）。
