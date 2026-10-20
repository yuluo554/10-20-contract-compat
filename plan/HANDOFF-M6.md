# HANDOFF-M5 · 归因与端到端报告交接单

> 用法（用户侧启动命令，绝对路径只在对话里给）：
> `/goal 读取 "<项目绝对路径>\plan\HANDOFF-M6.md" 继续完成任务`
> **第一动作 = 跑 `py tools/check-sprint-layout.py`**（门红了先修布局，再干活）。
> 上一棒：M4（破例规则库：`rules.evaluate`、三值 severity、N/A 结论行、R5 文件级求值），已完成并 commit。

## 一、当前进度与证据

| 项 | 状态 | 证据（可复跑的命令） |
|---|---|---|
| 四态归因 `blast.attribute(findings, deploy_order)` | ✅ | `py -3.12 -X utf8 -m pytest tests/test_blast.py -q`（23 项） |
| 四态 × 四种 `--deploy-order` 各断言一次（不是一条参数化） | ✅ | `tests/test_blast.py::test_consumers_first_attributes_old_consumer` 等 4 条 + `test_same_finding_changes_radius_with_order` |
| `REPLAY_ONLY` 只在显式 `replay` 出现 | ✅ | `tests/test_blast.py::test_replay_only_never_appears_without_replay` |
| 缺 `--deploy-order` → `null` + `deploy_order_not_given` | ✅ | `tests/test_blast.py::test_missing_deploy_order_does_not_guess`、`tests/test_cli.py::test_missing_deploy_order_leaves_null_blast_radius_in_json` |
| 归因层只补 `blast_radius`（不重算 direction、不覆盖 repair_*） | ✅ | `tests/test_blast.py::test_attribute_does_not_recompute_direction_or_overwrite_repair` |
| N/A 行不归因（`severity=None` → `blast_radius=null`） | ✅ | `tests/test_blast.py::test_na_rows_keep_null_blast_radius` |
| `runtime-dependent` 归因后不被压平（两段说明保留） | ✅ | `tests/test_blast.py::test_runtime_dependent_entry_is_not_flattened` |
| `repair_action` 三格式语法落点（`reserved 2;` / `"aliases"` / `"default"`） | ✅ | `tests/test_blast.py::test_r1_repair_hint_matches_format_syntax`（参数化 3 条） |
| 端到端 golden `cli-*.{md,json}` ×62（28 对 ×2 + 四态四联另 3 档 ×2） | ✅ | `py data/tools/gen_golden.py --check` → **118 份**逐字节一致 |
| 四态四联 golden（同一破例四种顺序四种归因） | ✅ | `tests/test_golden.py::test_four_state_quadruple_exists_and_differs` |
| 退出码 0/1 在"四态归因 + 三值 severity"下的 CLI 组合 | ✅ | `tests/test_cli.py::test_deploy_order_*`（5 条）+ `test_runtime_dependent_with_deploy_order_exits_one_strict` |
| `--verify` 重放定位：改 `blast_radius` 一字节 → 非 0 且 `json_path=findings[0].blast_radius` | ✅ | `tests/test_cli.py::test_verify_locates_tampered_blast_radius`（`--replay-old/--replay-new` 重放 baseline，先比内容再比 digest） |
| 测试全量 | ✅ 本地等价校验 | `py -3.12 -X utf8 -m pytest -q` 与 `py -3.8 -X utf8 -m pytest -q` 均 **357 passed** |
| golden | ✅ | `py data/tools/gen_golden.py --check` → **118 份**逐字节一致；`gen_fixtures.py --check` → 76 文件 |
| 布局门 | ✅ | `py tools/check-sprint-layout.py` 全绿（HANDOFF-M6 落盘后） |

**数据状态**：`data/fixtures/` 76 文件未变；`data/golden/` = 28 份 IR + 28 份 policy +
**62 份端到端 `cli-*`（M5 新增）**，`data/golden/README.md` 台账已同轮登记。
`severity` 与 `blast_radius` 由端到端 golden 承载；**policy golden 仍不含 severity**（口径未变）。

## 二、当前事实 · 状态不变量（下一棒动手前必须知道）

| # | 事实 | 后果 / 禁区 |
|---|---|---|
| 1 | 归因映射表 = `blast._RADIUS_BY_ORDER`：`consumers-first→OLD_CONSUMER`、`producers-first→NEW_CONSUMER`、`simultaneous→BOTH`、`replay→REPLAY_ONLY`；口径写在 `data/README.md` §4.6 的落地映射表 | 改映射**两处同轮**（数据 README 是唯一定义处）；不要把"删字段砸老消费者"这类特例写进代码 if——映射只看部署顺序，不看规则 |
| 2 | 归因层**不看 direction**：同一部署顺序下所有命中行拿同一个 radius | 这是刻意的：§4.6 的"版本偏差横在哪一侧"由部署顺序决定，severity 才表达"会不会真炸"。不要"聪明地"按 direction 分派 |
| 3 | `blast.ADDRESSABILITY` 登记三格式可寻址性；不认识的格式 → `null` + `format_not_addressable` | 三元组第三维的落点；新增格式时要来这登记，否则静默不归因 |
| 4 | 归因层给**每条** finding 补齐 `blast_radius` 键（含缺省路径） | `report.FINDING_KEYS` 键面自此完整；`test_rules.py` 的"只缺 blast_radius"断言仍锁规则层输出，别动规则层 |
| 5 | `--verify` 有第二条路：`--replay-old/--replay-new`（`--replay-policy` 可选）→ `report.rebuild_report` 重放同一输入算 baseline → **先比内容再比 digest**，定位到叶子字段 | 重放走的是生产实现（parsers→policy→rules→blast→report），**不是**第二份判定；别在生成器或测试里重算 baseline |
| 6 | 端到端 golden 的固定口径：`--policy backward --deploy-order consumers-first`，退出码 0/1 都接受 | 四态四联样例是 `proto/r1-field-removed`（`gen_golden.py::FOUR_STATE_PAIR`）；换样例要同轮改 `tests/test_golden.py` 的四联断言 |
| 7 | `gen_golden.py` 的 `--check` 现在扫 `cli-` 前缀 + `.md` 后缀；`run_check` 的 `expected` 集合含端到端文件 | 台账按**配对数**对账（不逐份手抄 62 行）；`tests/test_golden.py::test_cli_golden_names_match_disk_bidirectionally` 锁名单闭合 |
| 8 | `severity` 是相对 policy 的判定（K25 未变）：`cli-*-order-replay` golden 里 `r1` 在 backward 下仍是 `breaking` | 不要把某种 policy 下的 severity 值当成"事实"写死进归因层 |
| 9 | `_exit_code` 的回落分支（三计数全 0 且 verdict=breaking → 1）仍在 | K 口径（M4 #10）延续：保留作为防御，别删 |
| 10 | `--emit-policy` / `--emit-ir` 键面未动；policy/IR golden 未重生成（与 M4 逐字节相同） | 不要改导出模式；改了要重生成 56 份 |
| 11 | `report.rebuild_report` 与 `cli._run` 是**同一装配顺序的两份调用代码** | 若改普通路径的装配（比如加 notes），必须同轮改 `rebuild_report`，否则 `--verify` 重放的 baseline 与报告口径漂移 |
| 12 | 状态副本四处：`plan/00` 里程碑表 / `plan/05` 状态表 / `README.md` 状态行 / `plan/06` 缺口列 | 翻 M6 ✅ 时四处同轮改；`plan/06` 缺口列最后一格不得再出现 `M6` |
| 13 | `plan/06` 缺口列 G5 已关闭（只描述、不点名路径） | 缺口列里不要写文件路径（布局门扫该列） |
| 14 | `data/golden/README.md` 已无"待 M5"字样 | 不要再写回 |
| 15 | `tests/fixture_scan.scan_rule_fixtures()` 每侧是列表；`gen_golden.py` 的 `discover_pairs()` 配对规则未变 | 新增夹具只补 `data/golden/README.md` 台账行，生成数字自动跟上 |
| 16 | 无远端；CI 一律写"待首推验证" | `git remote -v` 为空；DoD 的 CI 条目保持"本地等价校验"措辞 |

## 三、下一棒待办（M6：发布）

按顺序做，每步留可复跑证据：

1. **干净环境三场景**：`git clone --no-local` 到仓库外 + 新 venv → 按 `README.md` 三条最小复现
   （Avro / Protobuf / JSON Schema）+ 归因四联逐条跑，退出码符合声明语义。
2. **源码包**：`git tag -a v0.1.0`（annotated）→ `git archive <tag>` + `gzip -9n` + `SHA256SUMS`；
   真下载/解包与 `git archive` 树逐字节比对。
3. **GitHub Release**：`gh repo create yuluo554/10-20-contract-compat --public`（或确认已有）→
   push → CI 全绿 → `gh release create v0.1.0 <附件> --notes-file ...`；CI 的 push 数 = run 数对账。
4. **发布留档**：`plan/RELEASE-M6.md` 两栏（tag 时点事实 / tag 后追加事实）+
   **阶段 7 覆盖对账表**（逐条：实现 / 不适用+理由 / 待首推）。
5. **发布终态自检门**（M6 同轮实现，落地前不在文档点名路径）：无 FAIL 才算发布完成；
   `LAYOUT.RELEASE` 判据激活后补两组变异（删覆盖对账节 / 去掉 §二 的 tag 后标记）。
6. **收尾**：四处状态副本翻 M6 ✅ → 清 `plan/06` 缺口列的 M6 字样 → tag 后只允许非交付面提交。

**不要做**：不要改任何 `src/`、`rules/`、`tests/`、`data/` 交付面文件（tag 后零差异）；
不要在缺口列写文件路径；不要把"本地绿"写成"CI 绿"。

## 四、既定口径清单（K 编号；动了会打挂测试的约定）

> M5 新增 K28–K29；K1–K27 未变（K1–K12 见 `plan/HANDOFF-M1.md` §四，K13–K15 见
> `plan/HANDOFF-M2.md` §四，K16–K18 见 `plan/HANDOFF-M3.md` §四，K19–K23 见 `plan/HANDOFF-M4.md` §四，
> K24–K27 见 `plan/HANDOFF-M5.md` §四——即本文件上一棒的版本，git 历史可查）。

| K | 口径 | 位置（唯一可编辑副本） | 打挂哪条 |
|---|---|---|---|
| K28 | 归因四态只由部署顺序决定：`consumers-first→OLD_CONSUMER`、`producers-first→NEW_CONSUMER`、`simultaneous→BOTH`、`replay→REPLAY_ONLY`；归因层不看 direction、不给 N/A 行归因 | `blast._RADIUS_BY_ORDER` + `data/README.md` §4.6 落地映射表 | `tests/test_blast.py` 四态断言、`tests/test_golden.py::test_four_state_quadruple_exists_and_differs` |
| K29 | `--verify` 的定位面 = 重放 baseline 先比内容再比 digest；baseline 由 `report.rebuild_report` 用生产实现现算 | `report.rebuild_report` / `report.verify_against_inputs` | `tests/test_cli.py::test_verify_locates_tampered_blast_radius` |

## 五、本机环境坑（全部实测，带日期）

| 坑 | 实测 | 处置 |
|---|---|---|
| `python` 是商店占位符 | 2026-10-20 | 一律 `py` / `py -3.12` / `py -3.8` |
| `py -3.12 -X utf8` 选项顺序 | 2026-10-20 | 版本号在 `-X` **之前** |
| 无 `protoc` | 2026-10-20 | `.pb` fixture 走程序化构造；`.proto` 文本 → exit 3（真缺件态） |
| `protobuf` 版本两档不同 | 2026-10-20 | `py -3.12`=7.36.2 / `py -3.8`=5.29.6；描述符字节逐字节相同 |
| 子进程里跑 `py -m contractcompat.cli` 需要 `PYTHONPATH=src` | 2026-10-20 | `gen_golden.py` 已自己拼；新增脚本照抄 `_env()` |
| `py` 启动器下子进程崩溃表现为 `returncode 3221225477`（0xC0000005） | 2026-10-20（M5 实测一次） | 先用 `PYTHONPATH=src py -3.12 -X utf8 -m ...` 直接复现；当时是偶发、重跑即好——**先复现再怀疑代码** |
| 布局门变异靶子会被文档改字打崩 | 2026-10-20（M2–M4 实测） | 靶子用表结构定位；改完文档先跑 `py tools/verify-layout-gate.py` |
| `plan/06` 缺口列会被措辞打红 | 2026-10-20（M4/M5 实测） | 缺口列里只写关闭条件，不写文件路径、不写"已随 M5 关闭"式括号说明 |
| 无远端 | 2026-10-20 | `git remote -v` 为空；CI 一律写"待首推验证" |

## 六、DoD 逐项 checklist（M5 → 交接时点）

- [x] 同一破例四种 `--deploy-order` 归因各断言一次（四态 × 4，非参数化一条）
- [x] 缺 `--deploy-order` → `blast_radius=null` + `deploy_order_not_given`（不猜默认顺序）
- [x] `repair_action` 三格式语法落点正确（`reserved 2;` / `"aliases"` / `"default"`）
- [x] 退出码 0/1/2/3 全覆盖；code 3 走 import 桩/缺件态真跑到（M0–M4 证据 + M5 组合补齐）
- [x] golden（md + json）逐字节；同输入双跑 `diff` 为空（`gen_golden.py --check` ×2 + 双跑一致用例）
- [x] `--verify` 改一字节 → 非 0 且 `json_path` 定位准确（重放 baseline，定位到 `findings[0].blast_radius`）
- [x] 失败路径零副作用（`tests/test_cli.py::test_verify_does_not_modify_target` 等）
- [x] 四态四联 golden 落盘（`cli-proto-r1-field-removed-order-*.md/json`）
- [x] `data/golden/README.md` 台账同轮登记端到端 golden（62 份）
- [x] 双解释器 pytest 全绿（3.8 / 3.12，各 **357** 项）
- [x] 布局门全绿
- [x] HANDOFF-M6 落盘并 commit
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

# 归因 + 修复（M5 交付面）
py -3.12 -X utf8 -m pytest -q tests/test_blast.py tests/test_cli.py tests/test_golden.py

# 四态归因真跑（同一对输入四种顺序四种归因）
PYTHONPATH=src py -3.12 -X utf8 -m contractcompat.cli \
  data/fixtures/avro/r1-field-removed-old.avsc data/fixtures/avro/r1-field-removed-new.avsc \
  --policy backward --deploy-order consumers-first   # OLD_CONSUMER，exit 1
#   producers-first → NEW_CONSUMER；simultaneous → BOTH；replay → REPLAY_ONLY

# --verify 重放定位（改一个归因值 → 指到 findings[0].blast_radius）
PYTHONPATH=src py -3.12 -X utf8 -m contractcompat.cli --verify <report.json> \
  --replay-old <old> --replay-new <new> [--replay-policy backward] [--deploy-order ...]

# 复算门
py data/tools/gen_fixtures.py --check      # 76 个 fixture 位级一致
py data/tools/gen_golden.py --check        # 118 份 golden（IR + policy + 端到端）逐字节一致
```

## 附：本棒做了但题面没要求的（如实记录）

- **`--verify` 增加重放参数（`--replay-old/--replay-new/--replay-policy`，`--help` 里隐藏）**：
  题面只要求"改一字节 → 非 0 且定位到被改字段"，而纯 digest 自洽校验只能指到 `digest` 键。
  要真定位就必须重放同一输入算 baseline——走的是生产实现同一条装配路径（`report.rebuild_report`），
  不是第二份判定。默认路径（无重放参数）行为与 M4 完全一致。
- **归因层补齐 `blast_radius` 键面**：规则层输出"只缺 blast_radius"（K4），归因层哪怕在缺省
  路径也给每条 finding 补上该键（值为 `null`），使键面与 `report.FINDING_KEYS` 完全一致——
  否则下游按固定列读取会踩 KeyError 而不是读到 null。
- **`gen_golden.py` 的 CLI 任务带"允许退出码集合"**：端到端报告的退出码 0/1 都是"判定已完成"
  （compatible / breaking），生成器不能把 breaking 用例当失败；2/3 仍必红。
- **`tests/test_golden.py` 新增端到端对账四条**（名单闭合 / 四态四联 / severity+radius 键面 /
  md-json 成对），并把无绝对路径断言扩到 `cli-*`。
- **`data/README.md` §4.6 补"落地映射表"**：四行 `--deploy-order → blast_radius` 的唯一权威写法，
  代码里的 `_RADIUS_BY_ORDER` 是它的直译（口径单点的纪律与 K25 同源）。
