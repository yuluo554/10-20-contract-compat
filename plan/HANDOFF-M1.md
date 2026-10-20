# HANDOFF-M1 · 数据先行交接单

> 用法（用户侧启动命令，绝对路径只在对话里给）：
> `/goal 读取 "<项目绝对路径>\plan\HANDOFF-M1.md" 继续完成任务`
> **第一动作 = 跑 `py tools/check-sprint-layout.py`**（门红了先修布局，再干活）。
> 上一棒：M0（定稿 + 骨架 + 方法论装订），已完成并 commit。

## 一、当前进度与证据

| 项 | 状态 | 证据（可复跑的命令） |
|---|---|---|
| 计划套件 `plan/00–06` | ✅ | `py tools/check-sprint-layout.py` → `LAYOUT.SECTIONS` PASS（8 份小节齐备） |
| 方法论装订（锚点 + 布局门 + plan/00 行） | ✅ | 同上 → `LAYOUT.BINDING_HEAD` / `LAYOUT.DOC_TOOLS` PASS |
| 布局门自身有效性 | ✅ | `py tools/verify-layout-gate.py` → 8 组变异逐组报红、还原后全绿 |
| 可安装骨架 | ✅ | `pip install -e .` → `compat --version` 输出 `compat 0.1.0.dev0` |
| 退出码 2 / 3 路径真跑 | ✅ | `py -m pytest tests/test_cli.py -q`（`test_*_exit_two` / `test_*_exit_three` 各若干条） |
| 退出码 0 / 1 装配层 | ✅ | 同上（`_exit_code` 直接验，不依赖未实现的判定核） |
| 规范报告层（序列化 / digest / --verify） | ✅ | `tests/test_canonical.py`、`tests/test_report.py` 全绿 |
| 安装面（editable + wheel） | ✅ | 新 venv `pip install -e ".[dev]"` → 仓库外跑 `compat --version` 得 `compat 0.1.0.dev0`；`pip wheel` → 再建一个**干净 venv** 装 wheel → `load_rule_table()` 读到 7 条、`default_rule_path()` 指向 site-packages 内的镜像 |
| 测试全量 | ✅ 本地等价校验 | `py -3.12 -m pytest -q` 与 `py -3.8 -m pytest -q` 均 `128 passed` |
| CI | ⏳ **未接远端，CI 待首推验证** | workflow 已落盘且本地 `yaml.safe_load` 通过（`tests/test_workflow.py`） |

**数据集状态**：`data/fixtures/{proto,avro,jsonschema}/`、`data/golden/`、`data/tools/` 均已建目录并留
`.gitkeep`，**内容为空**——这是 M1 的主要工作量（见 §三）。

## 二、当前事实 · 状态不变量（下一棒动手前必须知道）

| # | 事实 | 后果 / 禁区 |
|---|---|---|
| 1 | **骨架期的未实现路径一律退出码 3**（`CapabilityError` / `NotYetImplemented`），绝不返回 0 | 不要为了"让 demo 好看"改成 `return 0`：那会让"没检查"被读成"检查通过"。测试 `test_avro_mapping_not_implemented_exit_three` 会当场红 |
| 2 | `json.dumps(` **全仓只允许**出现在 `canonical.py` | 新增任何落盘/输出都必须走 `canonical.dumps`；`tests/test_architecture.py::test_json_dumps_only_in_canonical` 是守门 |
| 3 | `parsers/*` **不得 import** `policy` / `rules` / `blast` / `report` | 解析层不判定。M2 写解析器时若"顺手"想复用 policy 的常量，改 `ir.py` 或 `errors.py`，别反向依赖 |
| 4 | 版本号**单一来源** = `src/contractcompat/__init__.py:__version__`；`pyproject.toml` 走 `dynamic` | 定版只改一处；README 顶部与 tag 由 M6 的测试核对 |
| 5 | 规则表是**数据**（`rules/rule-table.json`），7 条 × 3 格式 = 21 槽 | 加规则/改语义改 JSON，不要写进 `rules.py` 的 if；`validate_rule_table` 会拒绝 8 条或 6 条 |
| 6 | 退出码 0/1 只由 `report["summary"]` 的三个计数决定 | 不要在任何地方直接 `return 1`；`--policy none` 恒 0 是**语义**不是特例 |
| 7 | `--deploy-order` 缺省时 `blast_radius = null` + `notes` 含 `deploy_order_not_given` | 不提供默认顺序——默认值会被当结论用（红线） |
| 8 | `.pb` fixture 的生成方式**尚未定**（`plan/04` §八 推荐程序化构造） | 若选 `protoc` 生成，要在 `data/README.md` 登记"fixture 由哪个 protoc 版本产出"；否则 `--check` 无法复现 |
| 9 | 本机**无 `protoc`、无 `protobuf`** | M1 开工先装 `protobuf`（`py -m pip install protobuf`）；`protoc` 只在验"缺 protoc → exit 3"时需要，可用 PATH 桩模拟 |
| 10 | 布局门的 `LAYOUT.RELEASE` 判据**尚未被任何变异覆盖**（要等 M6 翻 ✅ 后才激活） | M6 收尾必须补两组变异（删覆盖对账节 / 去掉 §二 的"tag 后"标记），见 `plan/05` §三 |
| 11 | 规则表有**两份**：`rules/rule-table.json`（唯一可编辑源）与 `src/contractcompat/data/rule-table.json`（包内镜像） | 改源文件后**必须同步镜像**，否则 `test_packaged_mirror_matches_source` 红；wheel 安装后盘上只有镜像那份 |
| 12 | 布局门的 `LAYOUT.DOC_TOOLS` 只扫 `tools/` **根目录**形态（负向前瞻排除 `data/tools/...`） | 若把生成器放到 `tools/` 下又不在仓里，门会红——这是有意的（文档点名就必须有实物）；放进 `data/tools/` 则不在扫描面 |

## 三、下一棒待办（M1：数据先行）

按顺序做，每步都留可复跑证据：

1. **装依赖**：`py -3.12 -m pip install protobuf`；确认 `py -3.8 -c "import google.protobuf"` 也过（两档解释器都要）。
2. **决定 `.pb` 生成方式**（`plan/04` §八 的决策点）：推荐**程序化构造 `FileDescriptorSet`**——
   可入仓、可 `--check` 位级复现、CI 不装 protoc 也能跑。定夺后写进 `plan/00` 决策记录。
3. **造 21 格 fixture**：`data/fixtures/{proto,avro,jsonschema}/<rule_id>-<slug>-{old,new}.<ext>`，
   最小 schema（1–3 字段），字段名用中性占位（`order_id` / `total_amount` / `status`）。
   规则与证据形态见 `data/README.md` §4.3，本表就是 M1 的验收矩阵。
4. **造 4 条反例**（`data/fixtures/negatives/`）：
   ① Avro union 加类型 ② Avro 改名带 `aliases` ③ Protobuf 删字段但已 `reserved` ④ JSON Schema 加可选 property。
   **反例的作用是防规则退化成"看到变化就报破"**——没有反例，误报率无门可守。
5. **造 4 条 `ir_unsupported` fixture**：`patternProperties` / `if-then-else` / 递归 `$ref` / `dependentSchemas`。
6. **写 `data/tools/gen_golden.py`**：只调 CLI（生产实现），**不得自己实现判定**——两份实现同错会让 golden 永远绿。
   提供 `--check`：重生成到临时目录 → 与入库 golden 逐字节比对。
7. **写覆盖度测试** `tests/test_coverage.py`：遍历 `data/fixtures` 断言 21/21 + 4/4 + 4/4 并**打印矩阵**（不手填）。
8. **加 M1 的 golden**（`data/golden/policy-*.json`）：七档 × 三格式的方向性矩阵。
   ⚠️ 但 M3 才实现 `diff`/`judge`——所以 M1 的 golden 只落 **IR 形态**，"七档矩阵"golden 顺延到 M3，
   在 `data/golden/README.md` 里如实标注"待 M3 生成"。**别伪造期望值**。
9. **收尾**：DoD → 回写 `plan/00`/`plan/05`/`plan/06`/`README` 状态 → 写 `plan/HANDOFF-M2.md` → commit → 跑布局门。

## 四、既定口径清单（K 编号；动了会打挂测试的约定）

| K | 口径 | 位置（唯一可编辑副本） | 打挂哪条 |
|---|---|---|---|
| K1 | 规范 JSON：`sort_keys=True` / `ensure_ascii=False` / `indent=2` / LF / 恰好一个结尾换行 | `canonical.dumps` | 全部 golden、`test_dumps_matches_upstream_json...` |
| K2 | `digest = sha256(dumps(去掉顶层 digest 的对象))` | `canonical.digest` | `test_digest_excludes_itself`、`--verify` 全部用例 |
| K3 | IR `fields` 规范序：有号在前（按号），无号在后（按 `json_pointer`,`name`），**不比较 None** | `ir.sort_fields` | `test_fields_sorted...`、`test_sort_does_not_compare_none...` |
| K4 | `default` 三态：`{present:false}` / `{present:true,value:null}` / `{present:true,value:X}` | `ir.Field.to_json` | `test_default_is_three_state` |
| K5 | 报告 finding 键集合 = 12 个固定键，不适用写 `null`（不省略键） | `report.FINDING_KEYS` | `test_finding_keys_are_fixed_and_nullable` |
| K6 | findings 排序 = `(rule_id, stable_path)` | `report.build` | `test_report_findings_are_sorted` |
| K7 | 七档名单与名字（含 `-transitive` 后缀） | `policy.POLICIES` | `test_seven_policies_exist`、CLI `choices` |
| K8 | `*-transitive` 缺 `--history` → 退出码 2；非 transitive 给了 `--history` → 也 2 | `policy.resolve_policy` | `test_transitive_requires_history` 等 |
| K9 | 规则集合必须恰好 R1–R7，每条 3 个格式槽位，N/A 必须带 `reason` | `rules.validate_rule_table` | `test_validate_rejects_*` 三条 |
| K10 | 退出码 0/1 只由 `summary` 计数决定；`policy=none` 恒 0 | `cli._exit_code` | `test_exit_*`、`test_policy_none_is_always_compatible` |
| K11 | 版本单一来源 = `__init__.__version__`（`pyproject` 走 dynamic） | `src/contractcompat/__init__.py` | `test_readme_version_line_matches_package` |
| K12 | 规范/口径类枚举**只**在 `data/README.md` §四定义；代码里是副本，文档不复制第二份 | `data/README.md` | 人工复核（M6 的覆盖对账） |

## 五、本机环境坑（全部实测，带日期）

| 坑 | 实测 | 处置 |
|---|---|---|
| `python` 是商店占位符 | 2026-10-20 | 一律 `py` / `py -3.12` / `py -3.8` |
| `py -3.12 -X utf8` 选项顺序 | 2026-10-20 | 版本号要在 `-X` **之前**（`py -3.12 -X utf8 -m pytest`）；写成 `py -X utf8 -3.12` 会报 `Unknown option: -3` |
| 控制台中文 / emoji | 2026-10-20 | 跑脚本加 `-X utf8`；门内部对 stdout 做了 `reconfigure(errors="replace")` 兜底 |
| 本机无 `protoc`、无 `protobuf` | 2026-10-20 | M1 先 `pip install protobuf`；`protoc` 缺失正是 exit 3 要验的路径 |
| 无远端 | 2026-10-20 | `git remote -v` 为空；CI 一律写"待首推验证" |

## 六、DoD 逐项 checklist（M0 → 交接时点）

- [x] `plan/00–06` 齐且 `plan/00` 顶部有装订行（三锚点同行）
- [x] `AGENTS.md` 落盘（方法论名 / 布局门命令 / 装订日期 / 强制布局清单 / 分层约束）
- [x] 布局门可跑、非空跑自证（打印扫到几个）
- [x] **8 组变异逐组报红，还原后全绿**（`py tools/verify-layout-gate.py`）
- [x] `pyproject.toml` + `src/contractcompat/` 骨架 + `compat` console script
- [x] `compat --version` / `--help` 可跑
- [x] 退出码 2 与 3 的路径真跑；0/1 的装配层真跑
- [x] `.github/workflows/ci.yml` 本地 `yaml.safe_load` + job/step 数断言
- [x] 双解释器 pytest 全绿（3.8 / 3.12，各 128 项）
- [x] 安装面：editable 与 wheel 两种装法都能在**仓库外**跑通（`compat --version` + 规则表加载）
- [x] `plan/HANDOFF-M1.md` 落盘并 commit
- [ ] CI 实跑 —— **未接远端，待首推**（M6）
- [ ] 干净 clone 按 README 跑通 —— M6

## 七、关键命令速查

```bash
# 方法论门（任何新对话第一件事）
py tools/check-sprint-layout.py

# 门自身是否有效（8 组变异）
py tools/verify-layout-gate.py

# 全量测试（双解释器）
py -3.12 -X utf8 -m pytest -q
py -3.8  -X utf8 -m pytest -q

# 安装 + 冒烟
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -e ".[dev]"
./.venv/Scripts/compat.exe --version

# 局部验证
py -3.12 -X utf8 -m pytest -q tests/test_cli.py          # 退出码矩阵与参数面
py -3.12 -X utf8 -m pytest -q tests/test_readme_gate.py  # README → parser 反射
py -3.12 -X utf8 -m pytest -q tests/test_workflow.py     # CI YAML 本地解析
```

## 附：本棒做了但题面没要求的（如实记录）

- 增加了 `errors.py`（异常 → 退出码的分类载体）。题面 §三.2 只列五个模块 + `canonical.py`；
  `errors.py` 是"退出码矩阵"这条判分的落点，**不改变题面的模块清单**（五模块仍在各自文件里）。
- 增加了 `tools/verify-layout-gate.py`（方法论门的自证脚本）。它不是产品功能，不进发布面判定路径。
- 增加了 `src/contractcompat/data/rule-table.json`（规则表的包内镜像）。题面 §三.2 只点名
  `src/contractcompat/{ir,policy,rules,blast,report}.py` + `canonical.py`，镜像不影响该清单；
  它的必要性由"wheel 安装后仓库根不存在"这条实测事实决定（干净 venv 装 wheel → 仍能加载 7 条规则）。
- `README.md` 现在写的是"目标形态"的三场景命令（fixture 尚未产出）。`tests/test_readme_gate.py`
  只验**参数面**，因此不会因 fixture 缺失而红——M1 产出 fixture 后要补一条"文件存在"的断言。
