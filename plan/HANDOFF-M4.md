# HANDOFF-M4 · 破例规则库交接单

> 用法（用户侧启动命令，绝对路径只在对话里给）：
> `/goal 读取 "<项目绝对路径>\plan\HANDOFF-M4.md" 继续完成任务`
> **第一动作 = 跑 `py tools/check-sprint-layout.py`**（门红了先修布局，再干活）。
> 上一棒：M3（方向性判定核：`policy.diff` / `policy.judge`、七档矩阵、policy golden），已完成并 commit。

## 一、当前进度与证据

| 项 | 状态 | 证据（可复跑的命令） |
|---|---|---|
| `policy.diff` 产出事实 + `direction` | ✅ | `py -3.12 -X utf8 -m pytest tests/test_policy.py -q`（52 项） |
| 同一"删字段"三格式 direction 一致（`FORWARD_OK`） | ✅ | `tests/test_policy.py::test_same_field_removal_has_same_direction_in_three_formats` |
| 七档 policy 全部可用（含 transitive 逐历史版本 diff+judge） | ✅ | `tests/test_policy.py::test_seven_policies_each_have_a_verdict`、`test_transitive_checks_every_history_version` |
| `--policy=none` 全差异 + `verdict=compatible` | ✅ | `tests/test_cli.py::test_policy_none_exits_zero_but_still_lists_differences` |
| 普通 `compat <old> <new>` 出真判定（删字段 backward → 退出 1） | ✅ | `py -3.12 -X utf8 -m contractcompat.cli data/fixtures/avro/r1-field-removed-old.avsc data/fixtures/avro/r1-field-removed-new.avsc --policy backward` |
| `--explain-mapping` 四行 + "只表达最接近、不宣称等价"（md/json 两出口） | ✅ | `tests/test_cli.py::test_explain_mapping_end_to_end_has_four_rows_and_phrase`、`test_explain_mapping_json_stays_parseable` |
| 普通报告渲染 `ir_unsupported`（非 `--require-complete-ir` 路径） | ✅ | `tests/test_cli.py::test_normal_report_renders_ir_unsupported_without_require_flag` |
| 判定只依赖 IR（改文件名/字段声明顺序不改变结论） | ✅ | `tests/test_policy.py::test_verdict_ignores_filename_and_declaration_order` |
| `policy-*.json` 七档矩阵 golden ×27 | ✅ | `py data/tools/gen_golden.py --check` → 54 份逐字节一致 |
| 测试全量 | ✅ 本地等价校验 | `py -3.12 -X utf8 -m pytest -q` 与 `py -3.8 -X utf8 -m pytest -q` 均 **261 passed** |
| 布局门 | ✅ | `py tools/check-sprint-layout.py` 全绿 |
| 七类规则命中求值 `rules.evaluate` | ⏳ **未实现**（M4 入口） | `rules.evaluate` 仍 `NotImplementedError`；CLI 的普通路径**当前不调用它**（见 §二 #3） |

**数据状态**：`data/fixtures/` 72 文件未变；`data/golden/` = 27 份 IR + 27 份 policy（M3 新增），
`data/golden/README.md` 台账已双向登记。`severity` **没有**进入任何 M3 golden（那是 M4 的维度）。

## 二、当前事实 · 状态不变量（下一棒动手前必须知道）

| # | 事实 | 后果 / 禁区 |
|---|---|---|
| 1 | `diff` 返回 `DiffResult`（`list` 子类，额外带 `.old` / `.new`） | M4 的 `rules.evaluate` 可直接遍历；**不要**把 `.old/.new` 序列化进报告或 golden |
| 2 | 差异项固定 10 键：`kind / format / field / number / stable_path / direction / old / new / detail / reason` | 新增键会打挂 policy golden（`--check` 逐字节）与 `test_golden.py` 的形态断言；要加先同轮重生成 |
| 3 | **CLI 的普通路径当前不调用 `rules.evaluate`**：M3 用 `cli._findings_from_differences` 把差异项桥接成 findings（`rule_id`/`severity` 为 `null`），并在 `notes` 写 `findings_stage_pending_M4` | **M4 必须删掉这条桥**，改成 `rules.evaluate(differences, table)`；否则"规则命中"永远是假的。桥的存在是因为直接传空 findings 会渲染成"（无命中）"，被读成检查通过 |
| 4 | `_exit_code` 有 M3 过渡分支：当 `breaking/runtime_dependent/non_breaking` 三计数全为 0 且 `verdict=breaking` 时返回 1 | M4 接上 severity 后，这条回落不应再被触发；**保留它作为防御**（全部 severity 为 null 时不能返回 0），但测试要锁住"有 severity 时以 severity 为准" |
| 5 | `blast.attribute(findings, None)` 返回 `(findings, ["deploy_order_not_given"])`；显式 `--deploy-order` 仍 `NotImplementedError` → 退出码 3 | M4 **不要**实现归因（M5）；只保证规则命中能被 `blast.attribute` 原样接收 |
| 6 | `--emit-policy` 是数据导出模式（退出 0 ≠ 兼容），`verdicts` 七档 + `differences` + `history` | 不要改它的键面；policy golden 由它产出，改一处就要重生成 27 份 |
| 7 | `--emit-ir` 仍是最早的 `return 0` 出口；`--emit-ir` / `--emit-policy` 互斥 | 不要在导出模式里"顺手判定"或"顺手渲染报告" |
| 8 | 方向是事实、policy 是选择 | 换 `--policy` 不改变 `direction`；`severity` 是第三维，**不得**用 direction 直接冒充 severity |
| 9 | **`union-add-type` 反例当前产出 `type_changed / FORWARD_OK / detail=union_widened`** | M4 不能把它无条件映射成 R2 的 `breaking`——那是"看到变化就报破"。规则求值必须用 `detail`/方向降级（至少 `non-breaking` 或 `runtime-dependent`），并让反例断言成立 |
| 10 | Avro `r2-type-changed` 同时产出 `default_changed`（默认值也变了） | M4 的"每条规则至少一条命中"允许一条夹具多命中；不要为了"一对夹具只演一条规则"去吞掉真实事实 |
| 11 | `verbatim` 规则表两份（`rules/rule-table.json` + 包内镜像）必须同步 | `test_packaged_mirror_matches_source` 会红；M4 若扩表要同轮复制 |
| 12 | `tests/test_rules.py::test_evaluate_not_implemented_yet` 是 M0 的守门 | **M4 必须改写它**（改成真求值断言），不得删除；与 M3 改写 CLI 守门同一纪律 |
| 13 | `tests/test_blast.py` 最后一条断言 `attribute(..., "consumers-first")` 抛 `NotImplementedError` | 这是 M5 的入口守门，M4 **不要**动 |
| 14 | `data/golden/README.md` 已无"待 M3"字样 | 不要再写回；`test_readme_registers_policy_goldens_as_generated` 会红 |
| 15 | 状态副本三处 + 缺口列：`plan/00` 里程碑表 / `plan/05` 状态表 / `README.md` 状态行 / `plan/06` 缺口列 | 翻 M4 ✅ 时四处同轮改；`plan/06` 缺口列最后一格不得再出现 `M4` |
| 16 | `plan/03` §6 已按实现校准（`DiffResult`、`--emit-policy`、方向语义） | 改实现要同轮改这里，别让文档滞后 |

## 三、下一棒待办（M4：破例规则库）

按顺序做，每步留可复跑证据：

1. **`rules.evaluate(differences, table) -> list[Finding]`**：把差异项按 `(kind, format, detail)`
   映射成七类规则命中；`rule_id` / `rule_name` / `format_evidence` / `repair_action` 一律取自
   `rules/rule-table.json`，**不在代码里写第二份口径**。
   - 命中顺序固定：`(rule_id, stable_path)`（`report.build` 会再排一次，但规则层自己也要确定）。
   - `applies=false` 的格式槽位 → 输出 `format_evidence: "N/A"` + 一行理由，**不得省略该行**。
   - R5 的两种形态：① 同号换主人（`field_number_reused`）；② 与 `reserved` 冲突
     （`reserved_conflict`）。跨 message 复用是 M4 的文件级求值面（IR 的 `meta.messages` 已有数据）。
2. **severity 三值**：`breaking` / `runtime-dependent` / `non-breaking`；`runtime-dependent`
   必须带 `why_static_breaking` + `what_would_trigger`（模板已在规则表的
   `runtime_dependent_templates`，逐规则取，不在代码里拼 if）。
   - `--ignore-runtime-dependent` 只改退出码，**不删条目**（现有 `_exit_code` 已实现，别破坏）。
3. **CLI 接线**：删除 `_findings_from_differences` 与 `findings_stage_pending_M4` note，
   改为 `findings = rules.evaluate(differences, rules.load_rule_table())`，再交给
   `blast.attribute(findings, args.deploy_order)` 与 `cli._assemble_report`。
4. **改写守门**：`tests/test_rules.py::test_evaluate_not_implemented_yet` → 真求值断言；
   新增 21 格命中用例（7 规则 × 3 格式，N/A 格断言"有理由的 N/A 行"）。
5. **反例锁误报**：4 条 negatives 的 findings 必须为空或全 `non-breaking`（至少不能有
   `breaking`）；`union-add-type` 用 `detail=union_widened` 降级，**不得**被 R2 报成 breaking。
6. **报告与 golden**：M4 **不**生成 `cli-*.md/json`（M5 的端到端 golden）；但普通报告的 JSON
   必须已经带 `rule_id` / `severity` / `format_evidence` / `repair_action`，供 M5 冻结。
7. **收尾**：`ir.IMPLEMENTED_IN["rules"]` 翻成 M4 → DoD 回写 `plan/00`/`plan/05`/`plan/06`/`README`
   → 写 `plan/HANDOFF-M5.md` → 清理 `plan/06` 缺口列里的 `M4` 字样 → commit → 跑布局门与变异脚本。

**不要做**：不要实现 `blast.attribute` 的四态映射（M5）；不要把 `severity` 写进 policy golden；
不要为了"反例好看"删掉真实的 `default_changed` 事实；不要手写 `cli-*.json` golden。

## 四、既定口径清单（K 编号；动了会打挂测试的约定）

> M3 新增 K19–K23；K1–K18 未变（K1–K12 见 `plan/HANDOFF-M1.md` §四，K13–K15 见
> `plan/HANDOFF-M2.md` §四，K16–K18 见 `plan/HANDOFF-M3.md` §四）。

| K | 口径 | 位置（唯一可编辑副本） | 打挂哪条 |
|---|---|---|---|
| K19 | `diff` 返回 `DiffResult`（`list` 子类 + `.old/.new`），差异项固定 10 键（见 §二 #2） | `src/contractcompat/policy.py:_item` / `DiffResult` | `test_policy.py` 全部方向断言 + 27 份 policy golden |
| K20 | direction 是事实、policy 是选择；`judge` 映射：`backward*` 接受 `BACKWARD_OK/BOTH_OK`，`forward*` 接受 `FORWARD_OK/BOTH_OK`，`full*` 只接受 `BOTH_OK`，`none` 恒 compatible | `policy._policy_allows` | `test_policy.py::test_seven_policies_each_have_a_verdict`、`test_direction_does_not_depend_on_policy` |
| K21 | transitive = 当前对 + 每个历史版本都重算 `diff`；`judge` 不重复做"缺 history"校验（`resolve_policy` 负责，退出码 2） | `policy._history_differences` / `_run` | `test_transitive_checks_every_history_version`、`test_transitive_without_history_exit_two` |
| K22 | policy golden 由 `--emit-policy` 产出；transitive 基线 = 同目录 old，输出 `history` 如实记录；verdict 缺基线时写 `null` + note，不拿单版本冒充 | `cli._render_policy` + `data/tools/gen_golden.py` | `gen_golden.py --check`（54 份）+ `test_golden.py::test_policy_golden_shape_digest_and_no_fake_severity` |
| K23 | M3 过渡桥：普通报告用差异项填 findings（`rule_id/severity=null`）+ note `findings_stage_pending_M4`；退出码在无 severity 分类时回落 verdict | `cli._findings_from_differences` / `_exit_code` | `test_cli.py::test_avro_field_removed_backward_exits_one_with_verdict`；**M4 必须替换桥** |

## 五、本机环境坑（全部实测，带日期）

| 坑 | 实测 | 处置 |
|---|---|---|
| `python` 是商店占位符 | 2026-10-20 | 一律 `py` / `py -3.12` / `py -3.8` |
| `py -3.12 -X utf8` 选项顺序 | 2026-10-20 | 版本号在 `-X` **之前** |
| 无 `protoc` | 2026-10-20 | `.pb` fixture 走程序化构造；`.proto` 文本 → exit 3（真缺件态） |
| `protobuf` 版本两档不同 | 2026-10-20 | `py -3.12`=7.36.2 / `py -3.8`=5.29.6；描述符字节逐字节相同 |
| 描述符**可能不含 NUL** | 2026-10-20 | 缺 protobuf 桩用例要挑含 NUL 的 `r4-enum-narrowed-old.pb` |
| 测试里的 subprocess 需要 `PYTHONPATH` | 2026-10-20 | `gen_golden.py` 自己拼 `PYTHONPATH=src`；`py -m contractcompat.cli` 在未 editable 安装时也要 `PYTHONPATH=src` |
| 布局门变异靶子会被文档改字打崩 | 2026-10-20（M2/M3 实测） | 靶子用表结构定位；改完文档先跑 `py tools/verify-layout-gate.py` |
| 无远端 | 2026-10-20 | `git remote -v` 为空；CI 一律写"待首推验证" |

## 六、DoD 逐项 checklist（M3 → 交接时点）

- [x] `policy.diff` 产出事实 + direction；换 policy 不改 direction
- [x] `policy.judge` 七档全覆盖；`none` 恒 compatible；transitive 逐历史版本
- [x] 同一"删字段"三格式 direction 完全一致（`FORWARD_OK`）
- [x] 普通 `compat <old> <new>` 出真 verdict；删字段 backward → 1、forward → 0
- [x] `--policy=none` 全差异 + 退出 0
- [x] `--explain-mapping` 四行 + "只表达最接近、不宣称等价"（md/json）
- [x] 普通报告渲染 `ir_unsupported`（md 节 + json 等长）
- [x] 判定只依赖 IR（文件名/字段顺序不影响结论）
- [x] `data/golden/policy-*.json` ×27；生成器只调 CLI；`--check` 54 份逐字节一致
- [x] `tests/test_rules.py::test_evaluate_not_implemented_yet` 仍如实登记 M4 未实现
- [x] `plan/03` §6 / `data/golden/README.md` / `plan/04` 与实现校准
- [x] 双解释器 pytest 全绿（3.8 / 3.12，各 261 项）
- [x] 布局门全绿 + 8 组变异全红
- [x] HANDOFF-M4 落盘并 commit
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

# 方向性判定核（M3 交付面）
py -3.12 -X utf8 -m pytest -q tests/test_policy.py
py -3.12 -X utf8 -m pytest -q tests/test_cli.py

# 普通判定（真 verdict；当前 findings 是 M3 过渡桥）
PYTHONPATH=src py -3.12 -X utf8 -m contractcompat.cli \
  data/fixtures/avro/r1-field-removed-old.avsc \
  data/fixtures/avro/r1-field-removed-new.avsc --policy backward   # exit 1

# 七档矩阵导出（policy golden 的唯一入口）
PYTHONPATH=src py -3.12 -X utf8 -m contractcompat.cli \
  data/fixtures/avro/r1-field-removed-old.avsc \
  data/fixtures/avro/r1-field-removed-new.avsc \
  --emit-policy --history data/fixtures/avro/r1-field-removed-old.avsc

# 复算门
py data/tools/gen_fixtures.py --check      # 72 个 fixture 位级一致
py data/tools/gen_golden.py --check        # 54 份 golden（IR + policy）逐字节一致
```

## 附：本棒做了但题面没要求的（如实记录）

- **新增 `--emit-policy`**：policy golden 必须由 CLI 产出（生成器不自己算判定），而规则/归因还没实现。
  导出模式让 M3 能冻结方向与七档真值，同时不把 `severity` 伪造成期望值。它与 `--emit-ir` 同构：
  退出 0 只表示导出成功。
- **M3 过渡桥**：普通报告把差异项填进 `findings`（`rule_id/severity=null`）。不这样做只能传空列表，
  报告会渲染"（无命中）"——与 `verdict=breaking` 同时出现就是假阴性。M4 必须替换，已列为 §二 #3。
- **`--explain-mapping` 的 json 出口修正**：原实现会在 JSON 后追加一段 Markdown，破坏可解析性；
  现在 json 只把 `buf_mapping` 放进报告，md 才追加渲染表。
- **`IR.IMPLEMENTED_IN["policy"]` 已是 M3**（骨架期就按计划登记），本棒未改值，只把实现补上。
