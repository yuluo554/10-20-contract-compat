# HANDOFF-M5 · 归因与端到端报告交接单

> 用法（用户侧启动命令，绝对路径只在对话里给）：
> `/goal 读取 "<项目绝对路径>\plan\HANDOFF-M5.md" 继续完成任务`
> **第一动作 = 跑 `py tools/check-sprint-layout.py`**（门红了先修布局，再干活）。
> 上一棒：M4（破例规则库：`rules.evaluate`、三值 severity、N/A 结论行、R5 文件级求值），已完成并 commit。

## 一、当前进度与证据

| 项 | 状态 | 证据（可复跑的命令） |
|---|---|---|
| 七类规则命中求值 `rules.evaluate(differences, table, policy=, history=)` | ✅ | `py -3.12 -X utf8 -m pytest tests/test_rules.py -q`（50 项） |
| 18 格 `applies=true` 逐格真跑命中（20 对夹具） | ✅ | `tests/test_rules.py::test_each_covered_cell_hits_its_rule`（参数化 20 条） |
| 3 格 `applies=false` 输出有理由的 N/A 行 | ✅ | `tests/test_rules.py::test_na_cells_emit_a_row_with_a_reason`、`test_na_rows_do_not_depend_on_having_a_difference` |
| `severity` 三值 + `runtime-dependent` 两段说明 | ✅ | `py -3.12 -X utf8 -m pytest tests/test_severity.py -q`（13 项） |
| `--ignore-runtime-dependent` 只改退出码、不删条目 | ✅ | `tests/test_severity.py::test_runtime_dependent_entry_survives_ignore_flag_in_json` |
| R5 三形态（同 message / reserved 冲突 / 跨 message） | ✅ | `tests/test_rules.py::test_r5_*`（3 条 + 2 条对照） |
| 4 条反例零误报（含 union 收窄阳性对照） | ✅ | `py -3.12 -X utf8 -m pytest tests/test_negatives.py -q`（14 项） |
| CLI 普通路径改由 `rules.evaluate` 产出 findings（M3 桥已删） | ✅ | `grep -rn "findings_stage_pending_M4\|_findings_from_differences" src/` 应为空 |
| 普通报告 JSON 已带 `rule_id`/`severity`/`format_evidence`/`repair_action` | ✅ | `tests/test_rules.py::test_normal_json_report_carries_rule_fields` |
| transitive 档历史版本也进规则求值 | ✅ | `PYTHONPATH=src py -3.12 -X utf8 -m contractcompat.cli data/fixtures/avro/r7-default-changed-old.avsc data/fixtures/avro/r7-default-changed-new.avsc --policy backward-transitive --history data/fixtures/avro/r1-field-removed-old.avsc --format json`（R1 条目带 `evidence.history`） |
| 测试全量 | ✅ 本地等价校验 | `py -3.12 -X utf8 -m pytest -q` 与 `py -3.8 -X utf8 -m pytest -q` 均 **325 passed** |
| golden | ✅ | `py data/tools/gen_golden.py --check` → **56 份**逐字节一致；`gen_fixtures.py --check` → 76 文件 |
| 布局门 | ✅ | `py tools/check-sprint-layout.py` 全绿 |
| 四态归因 `blast.attribute(findings, deploy_order)` | ⏳ **未实现**（M5 入口） | 给 `--deploy-order` 仍 `NotImplementedError` → 退出码 3 |

**数据状态**：`data/fixtures/` 76 个文件（M4 新增 `proto/r5-cross-message-reuse-{old,new}.{pb,proto}`）；
`data/golden/` = 28 份 IR + 28 份 policy；`data/golden/README.md` 台账已双向登记。
`severity` **仍不进** policy golden（那是规则库的维度，端到端 golden 才承载它）。

## 二、当前事实 · 状态不变量（下一棒动手前必须知道）

| # | 事实 | 后果 / 禁区 |
|---|---|---|
| 1 | `rules.evaluate` 的 severity 是**相对当前 policy** 的判定 | 同一对夹具换 `--policy` 会换 severity（enum 收窄在 `backward` 下 `non-breaking`、在 `forward` 下 `runtime-dependent`）。这是 §4.4 条件①的直译，**不是** bug；写 M5 用例时别把某一种 policy 下的值当成"事实" |
| 2 | `policy.allows(policy, direction)` 是 `judge` 与 `rules` 共用的唯一口径 | 改它同时影响 verdict 与 severity；**不要**在 `rules.py` 里再写一份方向表 |
| 3 | N/A 行**与命中无关**：按输入格式补齐（Avro → R5/R6；JSON Schema → R5） | N/A 行 `severity` 恒为 `None`、`stable_path` 为 `null`，**不参与 summary 计数**。M5 的归因不要给它们填 `blast_radius` |
| 4 | 求值输出键面 = `report.FINDING_KEYS` **减去 `blast_radius`** | M5 的 `attribute` 负责补这一键；补完键面必须与 `FINDING_KEYS` 完全一致（`test_rules.py` 已锁"只缺 blast_radius"） |
| 5 | `field_added` 只有 `direction == BACKWARD_OK` 才算 R3 | 加可选字段不是破例（反例 `add-optional-property` 靠这条不误报）。**不要**把它改成"凡新增就 R3" |
| 6 | R2 的 severity 由 `severity_by_detail` 改写：`union_widened` → `non-breaking` | 反例 `union-add-type` 的落点。**不要**为了"统一"删掉这条改写 |
| 7 | R5 的第三种形态是**文件级**求值（`_cross_message_hits`，读 `meta["messages"]`） | 只有 `DiffResult`（带 `.old/.new`）才做这一格；传普通 list 会静默跳过——`test_cross_message_hits_require_both_sides` 锁住了"不凭空造命中" |
| 8 | `blast.attribute(findings, None)` 返回 `(findings, ["deploy_order_not_given"])` | 缺 `--deploy-order` 时 `blast_radius` 必须留 `null`，**不猜默认顺序** |
| 9 | `tests/test_blast.py` 最后一条断言 `attribute(..., "consumers-first")` 抛 `NotImplementedError` | **M5 必须改写它**（改成四态断言），不得删除 |
| 10 | `_exit_code` 的回落分支（三计数全 0 且 verdict=breaking → 1）仍在 | M4 已锁"有 severity 时以 severity 为准"（`test_severity.py::test_exit_code_prefers_severity_over_verdict_fallback`）。**保留它作为防御**，别删 |
| 11 | `--emit-policy` / `--emit-ir` 都是数据导出模式 | M5 不要改它们的键面；policy golden 由 `--emit-policy` 产出，改一处要重生成 28 份 |
| 12 | `data/golden/README.md` 已无"待 M3"字样；policy 台账 28 行 | 不要再写回；`test_readme_registers_policy_goldens_as_generated` 会红 |
| 13 | 状态副本四处：`plan/00` 里程碑表 / `plan/05` 状态表 / `README.md` 状态行 / `plan/06` 缺口列 | 翻 M5 ✅ 时四处同轮改；`plan/06` 缺口列最后一格不得再出现 `M5` |
| 14 | `gen_golden.py` 的 `--check` 现在按**磁盘配对现算**份数（`test_golden.py::expected_golden_count`） | 新增夹具不需要再手改数字；但 `data/golden/README.md` 台账要同轮补两行（表↔盘双向对账） |
| 15 | `tests/fixture_scan.scan_rule_fixtures()` 每侧现在是**列表** | 同一格可以有多对夹具（R5×proto 3 对）；旧代码里的 `["old"]` 单值写法会 `TypeError` |
| 16 | `report.to_markdown` 新增"该格式不适用的规则（N/A…）"节 | 改 md 结构要同轮看 `test_report.py` 与 M5 的端到端 golden |

## 三、下一棒待办（M5：归因 + 端到端报告）

按顺序做，每步留可复跑证据：

1. **`blast.attribute(findings, deploy_order) -> (findings, notes)`**：按
   `(direction, deploy_order, 该格式的字段可寻址性)` 三元组填 `blast_radius ∈ {OLD_CONSUMER,
   NEW_CONSUMER, BOTH, REPLAY_ONLY}`；`REPLAY_ONLY` **只在显式 `replay` 时出现**。
   - `direction` 用 finding 里已有的值（规则层已带上），**不要**在归因层重算方向。
   - `severity` 为 `None` 的 N/A 行：`blast_radius` 保持 `null`，不参与归因。
   - `repair_hint` 已由规则层填好（带可执行落点）；归因层只补 `blast_radius`，别覆盖它。
2. **改写 `tests/test_blast.py`**：四态 × 四种 `--deploy-order` 各断言一次（不是一条参数化打天下），
   缺省 → `null` + `deploy_order_not_given`，`runtime-dependent` 不被压平。
3. **端到端 golden `cli-*.md` / `cli-*.json`**：扩 `data/tools/gen_golden.py`（**仍只调 CLI**），
   覆盖 20 对规则夹具 + 4 反例；`--check` 逐字节。
4. **退出码 0/1/2/3 全覆盖**：现在 2/3 已有证据，补 0/1 在"四态归因 + 三值 severity"下的组合。
5. **`--verify` 定位**：对含 `blast_radius` 的报告改一字节 → 非 0 且 `json_path` 指到该字段。
6. **收尾**：`ir.IMPLEMENTED_IN["blast"]` / `["report"]` 翻成 M5 → DoD 回写 `plan/00`/`plan/05`/
   `plan/06`/`README` → 写 `plan/HANDOFF-M6.md` → 清 `plan/06` 缺口列里的 `M5` → commit → 跑布局门与变异脚本。

**不要做**：不要改 `rules.evaluate` 的 severity 口径（那是 M4 的验收面）；不要把 `severity` 写进
policy golden；不要在归因层重算 direction；不要给 N/A 行填 `blast_radius`。

## 四、既定口径清单（K 编号；动了会打挂测试的约定）

> M4 新增 K24–K27；K1–K23 未变（K1–K12 见 `plan/HANDOFF-M1.md` §四，K13–K15 见
> `plan/HANDOFF-M2.md` §四，K16–K18 见 `plan/HANDOFF-M3.md` §四，K19–K23 见 `plan/HANDOFF-M4.md` §四）。

| K | 口径 | 位置（唯一可编辑副本） | 打挂哪条 |
|---|---|---|---|
| K24 | 事实 → 规则只有一张表 `KIND_RULES`；`field_added` 仅 `BACKWARD_OK` 归 R3 | `rules.KIND_RULES` / `rules._rule_of` | `test_rules.py::test_every_kind_maps_to_a_declared_rule`、`test_negatives.py::test_add_optional_property_is_not_an_r3_hit` |
| K25 | severity 是相对 policy 的判定：`allows` 为真 → `severity_when_allowed`；为假 → `default_severity`，可被 `severity_by_detail` 改写 | `rules/rule-table.json` + `rules._severity` | `test_severity.py` 全部（含"换 policy 换 severity"） |
| K26 | N/A 行按**输入格式**补齐（`applies=false` 的槽位），`severity=None`、`stable_path=None`、不计数 | `rules._not_applicable_rows` | `test_rules.py::test_na_cells_emit_a_row_with_a_reason`、`test_na_rows_do_not_depend_on_having_a_difference` |
| K27 | R5 第三形态 = 跨 message 复用，只在两侧 IR 都在时求值（`stable_path = "Message.号"`） | `rules._cross_message_hits` | `test_rules.py::test_r5_cross_message_reuse_hits_file_level`、`test_cross_message_hits_require_both_sides` |

## 五、本机环境坑（全部实测，带日期）

| 坑 | 实测 | 处置 |
|---|---|---|
| `python` 是商店占位符 | 2026-10-20 | 一律 `py` / `py -3.12` / `py -3.8` |
| `py -3.12 -X utf8` 选项顺序 | 2026-10-20 | 版本号在 `-X` **之前** |
| 无 `protoc` | 2026-10-20 | `.pb` fixture 走程序化构造；`.proto` 文本 → exit 3（真缺件态） |
| `protobuf` 版本两档不同 | 2026-10-20 | `py -3.12`=7.36.2 / `py -3.8`=5.29.6；描述符字节逐字节相同 |
| 描述符**可能不含 NUL** | 2026-10-20 | 缺 protobuf 桩用例要挑含 NUL 的 `r4-enum-narrowed-old.pb` |
| 测试里的 subprocess 需要 `PYTHONPATH` | 2026-10-20 | `gen_golden.py` 自己拼 `PYTHONPATH=src`；`py -m contractcompat.cli` 在未 editable 安装时也要 `PYTHONPATH=src` |
| 布局门变异靶子会被文档改字打崩 | 2026-10-20（M2/M3/M4 实测） | 靶子用表结构定位；改完文档先跑 `py tools/verify-layout-gate.py` |
| `plan/06` 缺口列会被"提到已完成里程碑"的措辞打红 | 2026-10-20（M4 实测） | 缺口列里不要写"（规则库部分已随 M4 关闭）"这类括号说明；只写关闭条件 |
| 无远端 | 2026-10-20 | `git remote -v` 为空；CI 一律写"待首推验证" |

## 六、DoD 逐项 checklist（M4 → 交接时点）

- [x] `rules/rule-table.json` 7 条 × 3 格式槽位齐（结构性断言）
- [x] 21 格命中用例各一条（18 格真跑 + 3 格 N/A 有理由）
- [x] `runtime-dependent`：条目在 + 两段说明 + 严格档 exit 1；忽略档条目不消失
- [x] R5 三形态（同 message 换主人 / reserved 冲突 / 跨 message）
- [x] `N/A` 行显式存在且带理由，且与本次是否命中解耦
- [x] 4 条反例零误报 + union 收窄阳性对照
- [x] 普通报告 JSON 已带 `rule_id` / `severity` / `format_evidence` / `repair_action`
- [x] CLI 的 M3 过渡桥已删除（`_findings_from_differences` 与 `findings_stage_pending_M4` 不再存在）
- [x] transitive 档历史版本进规则求值（带 `evidence.history`）
- [x] `data/golden/README.md` 台账补 2 行（IR + policy 各一份新 golden）
- [x] 双解释器 pytest 全绿（3.8 / 3.12，各 325 项）
- [x] 布局门全绿 + 8 组变异全红
- [x] HANDOFF-M5 落盘并 commit
- [ ] CI 实跑 —— **未接远端，待首推**（M6）
- [ ] 干净 clone 按 README 跑通 —— M6

## 七、关键命令速查

```bash
# 方法论门（任何新对话第一件事）
py tools/check-sprint-layout.py
py tools/verify-layout-gate.py        # 门自身的 8 组变异（改过文档必跑）

# 全量测试（双解释器）
py -3.12 -X utf8 -m pytest -q
py -3.8  -X utf8 -m pytest -q

# 规则库（M4 交付面）
py -3.12 -X utf8 -m pytest -q tests/test_rules.py tests/test_severity.py tests/test_negatives.py

# 普通判定（真 verdict + 真 severity；blast_radius 仍为 —）
PYTHONPATH=src py -3.12 -X utf8 -m contractcompat.cli \
  data/fixtures/proto/r5-cross-message-reuse-old.pb \
  data/fixtures/proto/r5-cross-message-reuse-new.pb --policy backward   # exit 1，R1 + R5 两条

# runtime-dependent 两段说明（md 与 json 两种出口都要有）
PYTHONPATH=src py -3.12 -X utf8 -m contractcompat.cli \
  data/fixtures/jsonschema/r6-oneof-moved-old.json \
  data/fixtures/jsonschema/r6-oneof-moved-new.json --policy backward    # exit 1

# 复算门
py data/tools/gen_fixtures.py --check      # 76 个 fixture 位级一致
py data/tools/gen_golden.py --check        # 56 份 golden（IR + policy）逐字节一致
```

## 附：本棒做了但题面没要求的（如实记录）

- **新增第 20 对夹具 `r5-cross-message-reuse`**：题面要求 R5 覆盖"跨 message 复用"，但 M1 只造了
  "同 message 换主人"与"reserved 冲突"两对。M4 补上真夹具（`meta.messages` 已有数据），
  让"buf 空白格"这条有可复跑的输入面，而不是只在代码里写个分支。
- **`rules.evaluate` 多了 `policy` 与 `history` 两个参数**：severity 必须相对当前 policy
  （§4.4 条件①），transitive 档的历史差异也必须进规则求值，否则会出现"verdict=breaking 但
  findings 里没有对应条目"。两处都写进了 `plan/03` §7。
- **N/A 行改为按输入格式补齐**：初版按"每个命中补一次"，会随命中数重复出多行；改成按格式补一行，
  并让 `stable_path=None`，避免把"格式结论"伪装成"某字段的结论"。
- **`policy._policy_allows` 改名为公开的 `policy.allows`**：规则层要用同一份方向口径，
  私有函数跨模块借用会把"唯一口径"变成事实上的两处。
- **`gen_fixtures.py` 的 `proto()` 加了 `extra_messages`**：多 message 文件此前造不出来。
- **`fixture_scan.scan_rule_fixtures()` 每侧改为列表**：单值写法会让同格的第二对夹具被静默吞掉
  （R5×proto 现在 3 对），"覆盖了几对"就无从核对。
- **`report.to_markdown` 增加 N/A 小节**：N/A 行带理由，md 视图必须能看到理由，否则
  "有理由的 N/A"只在 json 里成立。
