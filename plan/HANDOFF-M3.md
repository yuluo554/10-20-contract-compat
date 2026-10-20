# HANDOFF-M3 · 方向性判定核交接单

> 用法（用户侧启动命令，绝对路径只在对话里给）：
> `/goal 读取 "<项目绝对路径>\plan\HANDOFF-M3.md" 继续完成任务`
> **第一动作 = 跑 `py tools/check-sprint-layout.py`**（门红了先修布局，再干活）。
> 上一棒：M2（统一 IR 收口：解析器逐项单测 + 双跑确定性 + 缺件态桩 + 报告装配单点），已完成并 commit。

## 一、当前进度与证据

| 项 | 状态 | 证据（可复跑的命令） |
|---|---|---|
| 三格式 IR 七项逐项断言 | ✅ | `py -3.12 -X utf8 -m pytest tests/test_parser_avro.py tests/test_parser_jsonschema.py tests/test_parser_proto.py -q` |
| 双跑逐字节一致（单文件 ×3 格式 + 54 份批量） | ✅ | `py -3.12 -X utf8 -m pytest tests/test_parser_stability.py -q`（`54` = 18 `.pb` + 14 `.avsc` + 22 `.json`） |
| 越界输入（空 message / 无 `properties` / 空 `fields`） | ✅ 空 IR 是**有意**行为 | 同上文件：三个 `yields_empty_ir` 用例 + `--emit-ir` 空 schema 退出 0 |
| 缺 `protobuf` → 退出码 3（import 桩，两处守门） | ✅ | `py -3.12 -X utf8 -m pytest tests/test_parser_proto.py -q -k protobuf`；桩覆盖 `parsers/__init__._protobuf_module()` 与 `parsers/proto.parse_descriptor_set()`，并配"不装桩就正常"阳性对照 |
| `--require-complete-ir` 真跑到退出码 3 | ✅ 且**拒的同时点名构造** | `py -3.12 -X utf8 -m contractcompat.cli data/fixtures/jsonschema/ir-unsupported-patternproperties-new.json <same> --require-complete-ir` → 3，stderr 含 `patternProperties @ /patternProperties` + 理由 |
| 报告装配单点 `cli._assemble_report` + `ir_unsupported` 渲染 | ✅（IR 阶段） | `py -3.12 -X utf8 -m pytest tests/test_cli.py -q -k "ir_stage or require_complete"` |
| 解析层不 import 判定层（AST 守门） | ✅ | `py -3.12 -X utf8 -m pytest tests/test_architecture.py -q` |
| 测试全量 | ✅ 本地等价校验 | `py -3.12 -X utf8 -m pytest -q` 与 `py -3.8 -X utf8 -m pytest -q` 均 **215 passed** |
| fixture / golden 复算 | ✅ | `py data/tools/gen_fixtures.py --check` → 72 文件位级一致；`py data/tools/gen_golden.py --check` → 27 份逐字节一致 |
| 布局门变异验证（8 组） | ✅ 修复后全绿 | `py tools/verify-layout-gate.py` → 8/8 报红 + 还原后全绿（M1 遗留的失效锚点已修，见 §七 附） |
| 普通 `compat <old> <new>` 判定 | ⏳ **未实现**（M3） | `policy.diff` / `policy.judge` 仍 `NotImplementedError` → 退出码 3。**这不是 M2 的遗漏**，是 M3 的入口 |

**数据状态**：`data/fixtures/` 72 文件、`data/golden/` 27 份 IR golden 均未变（本棒**没有**动数据）。
`data/golden/policy-*.json` 仍不存在——七档判定 golden 是 M3 的交付物，`data/golden/README.md` 已标注"待 M3"。

## 二、当前事实 · 状态不变量（下一棒动手前必须知道）

| # | 事实 | 后果 / 禁区 |
|---|---|---|
| 1 | 三解析器**已完成**：字段七项、规范序、enum 编号、reserved 展开、`ir_unsupported` 都有单测钉住 | 不要再"顺手重构"解析器：27 份 golden + 54 份双跑断言会立刻红。要改先跑 `gen_golden.py --check` |
| 2 | 普通 `compat <old> <new>` **仍退出 3**（`policy.diff` 未实现） | M3 接上判定核之前，任何"demo 跑出判定表"的做法都是伪造。`tests/test_cli.py::test_avro_mapping_not_implemented_exit_three` 是这条的守门，**M3 必须改写它**（改成真判定断言），不得删除 |
| 3 | `--emit-ir` 是**唯一** IR 出口、**绕过判定**（在 `policy.diff` 之前 `return 0`） | 退出码 0 ≠ "兼容"；这是数据导出模式。M3 不要把它改成"顺手判定" |
| 4 | `verdict` **只有两值** `compatible` / `breaking`（`data/README.md` §4.1） | **禁止**新增 `inconclusive`/`unknown`。IR 阶段无法判定时只能"拒"（退出码 3）+ 说明，不能渲染空 findings 的报告（会被读成"检查通过"） |
| 5 | 报告装配**单点** = `cli._assemble_report(...)`，收 IR 侧 `Unsupported` 对象 | M3 的普通路径要把同一份 `unsupported` 交给它；不要在 `_run` 里另写一份 `report.build(...)` 调用 |
| 6 | `--require-complete-ir` 的拒收信息**逐条点名** `construct @ pointer — reason` | 保持这个形态：M3 里"报告渲染"与"拒收说明"必须说的是同一组事实 |
| 7 | `detect_format` 判描述符用**往返校验**，不是 NUL | 缺 protobuf 的桩用例必须挑**含 NUL** 的描述符（`r4-enum-narrowed-old.pb`）才走得到缺件分支；不含 NUL 的 `.pb` 在桩下会变成"未知形态"(2)——那是判据的真实盲区，别用错 fixture 得出假结论 |
| 8 | Avro 的 `Field.number` 与 `json_pointer` **都是 None**；Avro 顶层只收 `record` / `error` | 不要为了"七项齐"给 Avro 编字段号（R5/R6 的 N/A 会假命中）；顶层 enum/fixed/map → 退出码 2（`plan/03` §4 已按实现校准） |
| 9 | Protobuf enum/message 字段 `type` 用**短类型名**（`Status`） | 与 Avro 同说法；写 `enum` 会破坏跨格式可比（K6） |
| 10 | JSON Schema 的 enum 标签用 `_literal_label`（`true` / `{a:1}`），**不是** `json.dumps` | 全仓 `json.dumps(` 只允许 `canonical.py`（AST 守门） |
| 11 | 空 schema 合法 → 空 IR（`fields == ()`），不是报错 | 改坏了会让"没有差异"冒充"判定通过" |
| 12 | 布局门的 `LAYOUT.GAPS` 会扫 plan/06 缺口表的**最后一列**；提到已 ✅ 的里程碑即红 | 每翻一个里程碑 ✅，必须同步清理 `plan/06` §三 关闭条件里的 `M<k>` 字样（M2 已清 M2 的） |
| 13 | `tools/verify-layout-gate.py` 的靶子只可用**表结构**定位，不可写死行文案 | M1 改了一句 G5 文案，M3 组变异直接崩（锚点缺失）。本棒已改成"取缺口表第一条数据行"——下一棒改文档别再依赖整行文本 |
| 14 | 规则表两份（源 + 包内镜像）必须同步 | `test_packaged_mirror_matches_source` 会红（M4 才会动） |
| 15 | 退出码 2/3 的分流写死在异常类上（`UsageError`=2 / `CapabilityError`=3） | 新错误先归到这两类，别在 CLI 里写散落的 `return 2` |

## 三、下一棒待办（M3：方向性判定核）

按顺序做，每步留可复跑证据：

1. **`policy.diff(old_ir, new_ir) -> list[DiffItem]`**：只产出**事实**（新增/删除/类型变/基数变/默认值变/
   enum 收窄/oneof 移动/字段号复用），每项带 `direction ∈ {BACKWARD_OK, FORWARD_OK, BOTH_OK, NONE_OK}`
   （`DIRECTIONS` 已在 `policy.py`，口径见 `data/README.md` §4.1）。
   ⚠️ **direction 是事实、policy 是选择**：换 `--policy` 不得改变 `direction`。
2. **`policy.judge(differences, policy, history)`**：把方向 × 七档映射成 `verdict ∈ {compatible, breaking}`；
   `none` 恒 `compatible`；`*-transitive` 逐历史版本重复 `diff + judge`（缺 `--history` 已由
   `resolve_policy` 退 2，别在 judge 里再判一次）。
3. **三格式 direction 一致**：同一"删字段"在 Avro / Protobuf / JSON Schema 夹具上必须给出**同一个 direction**
   （backward 破 / forward 不破）。这是红线①的机械检查面，必须有专门用例。
4. **七档 golden**：`data/golden/policy-*.json`（七份或一份矩阵，命名先定再写生成器；
   生成器仍**只调 CLI**，不得自己算判定）。同时更新 `data/golden/README.md` 台账，并让
   `tests/test_golden.py::test_readme_marks_policy_goldens_as_pending` 翻转成"已生成"。
5. **`--explain-mapping` 四行齐**且整表含"只表达最接近、不宣称等价"（`policy.mapping_table()` 已就绪，
   只差测试断言 + 渲染端到端）。
6. **普通报告接上 `ir_unsupported`**：把 M2 的 `_assemble_report` 真正走通（`--require-complete-ir` 之外）。
   断言：md 有"不可表达的构造"节、json 的 `summary.ir_unsupported` 与 `ir_unsupported[]` 等长。
7. **判定只依赖 IR**：改文件名 / 字段声明顺序不改变结论（报告里 `inputs` 只写 basename 已有守门，
   这条要断言"结论字段不变"）。
8. **收尾**：`ir.IMPLEMENTED_IN` 的 `policy` 翻成 M3 → DoD 回写 `plan/00`/`plan/05`/`plan/06`/`README`
   → 写 `plan/HANDOFF-M4.md` → 清理 `plan/06` 缺口列里的 `M3` 字样 → commit → 跑布局门与变异脚本。

**不要做**：不要为"demo 好看"把 `rules.evaluate` / `blast.attribute` 也写成返回空列表的壳（M4/M5 才轮到它们）；
不要手写 `policy-*.json` golden；不要把 `direction` 的判定塞进解析层。

## 四、既定口径清单（K 编号；动了会打挂测试的约定）

> M2 新增 K16–K18；K1–K15 未变（K1–K12 原文见 `plan/HANDOFF-M1.md` §四，K13–K15 见 `plan/HANDOFF-M2.md` §四）。

| K | 口径 | 位置（唯一可编辑副本） | 打挂哪条 |
|---|---|---|---|
| K1–K15 | 见前述交接单（规范 JSON / digest / IR 序 / 三态 default / 12 键 / 排序 / 七档 / transitive / 规则表 / 退出码 / 版本 / 口径唯一处 / fixture 命名 / golden 命名 / `--emit-ir` 形态） | 同左 | 同左 |
| K16 | 报告装配单点 = `cli._assemble_report`；`ir_unsupported` 以 IR 侧 `Unsupported` 对象传入，由 `report.build` 归一成三键 | `src/contractcompat/cli.py:_assemble_report` | `tests/test_cli.py::test_ir_stage_report_assembly_renders_unsupported`、M3 的整报告 golden |
| K17 | 缺 `protobuf` 的退出码 3 用 `builtins.__import__` 桩验证；必须覆盖 `parsers/__init__._protobuf_module` 与 `parsers/proto.parse_descriptor_set` 两处，且每条桩用例配阳性对照 | `tests/test_parser_proto.py` | 该文件 `-k protobuf` 的 4 条用例 |
| K18 | 解析确定性断言面 = **54 份 schema 输入**（18 `.pb` + 14 `.avsc` + 22 `.json`）；18 份 `.proto` 是人读源文本、不进解析面 | `tests/test_parser_stability.py:EXPECTED_SCHEMA_INPUTS` | 增删 fixture 而不改常数 → 该用例红（**红是对的**） |

## 五、本机环境坑（全部实测，带日期）

| 坑 | 实测 | 处置 |
|---|---|---|
| `python` 是商店占位符 | 2026-10-20 | 一律 `py` / `py -3.12` / `py -3.8` |
| `py -3.12 -X utf8` 选项顺序 | 2026-10-20 | 版本号在 `-X` **之前** |
| 本机无 `protoc` | 2026-10-20 | `.pb` fixture 走程序化构造；`.proto` 文本 → exit 3（真缺件态） |
| `protobuf` 版本两档不同 | 2026-10-20 | `py -3.12`=7.36.2 / `py -3.8`=5.29.6；描述符字节逐字节相同。**桩用例里两处 import 形态不同**（`import google.protobuf` / `from google.protobuf import descriptor_pb2`），桩按 `name == "google.protobuf" or name.startswith("google.protobuf.")` 拦 |
| 描述符**可能不含 NUL** | 2026-10-20 | `r4-enum-narrowed-old.pb` 含 NUL、多数 fixture 不含。缺 protobuf 的"判不了"分支只在含 NUL 时可达——桩用例别用错 fixture |
| 测试里的 subprocess 需要 `PYTHONPATH` | 2026-10-20 | `tests/test_golden.py` 自己拼 `PYTHONPATH=src`；CI 里是 `pip install -e .`，两种都要能跑 |
| 布局门变异靶子会被文档改字打崩 | 2026-10-20（M2 实测） | 靶子用表结构定位（表头 + 首条数据行），不写死正文；改完文档先跑 `py tools/verify-layout-gate.py` |
| 无远端 | 2026-10-20 | `git remote -v` 为空；CI 一律写"待首推验证" |

## 六、DoD 逐项 checklist（M2 → 交接时点）

- [x] 三格式 IR 七项齐——`test_parser_{avro,jsonschema,proto}.py` 逐项断言（名/号/类型/基数/默认/enum 编号/reserved）
- [x] `fields` 规范序（含"描述符声明乱序 → IR 按字段号排"真解析用例；无号字段按名字，不比较 `None`）
- [x] 同文件双跑 `to_json` 逐字节一致：单文件 ×3 格式 + 54 份 schema 输入批量
- [x] 不可表达构造进 `ir_unsupported`：4 条夹具的构造名与指针逐条断言（含 `if/then/else` 只记一条）
- [x] 报告必渲染：`_assemble_report` 的 md/json 双断言（IR 阶段路径）；完整判定报告待 M3（如实登记）
- [x] `--require-complete-ir` 真跑到退出码 3，且逐条点名构造 + 理由
- [x] 缺 `protobuf` → 退出码 3（import 桩覆盖两处守门 + 阳性对照）
- [x] 非法输入 → 退出码 2（三格式各一条，且与缺件态(3)分开断言）
- [x] 越界输入行为钉住：空 message / 无 `properties` / 空 `fields` → 空 IR（有意）
- [x] AST 守门：`parsers/*` 不 import `policy`/`rules`/`blast`（M0 起在位，本棒未破）
- [x] `gen_fixtures.py --check` 与 `gen_golden.py --check` 仍全绿（M2 未动数据）
- [x] 双解释器 pytest 全绿（3.8 / 3.12，各 215 项）
- [x] 布局门全绿 + 8 组变异全红（含修复后的 M3 组）
- [x] `plan/03` §3/§4 与实现校准（proto 文本不代跑 `protoc`；Avro 顶层只收 record/error）
- [x] HANDOFF-M3 落盘并 commit
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

# 解析器（M2 交付面）
py -3.12 -X utf8 -m pytest -q tests/test_parser_avro.py tests/test_parser_jsonschema.py tests/test_parser_proto.py
py -3.12 -X utf8 -m pytest -q tests/test_parser_stability.py
py -3.12 -X utf8 -m pytest -q tests/test_parser_proto.py -k protobuf   # 缺件态桩

# 退出码 3 的两条 IR 阶段路径
py -3.12 -X utf8 -m contractcompat.cli data/fixtures/jsonschema/ir-unsupported-patternproperties-new.json data/fixtures/jsonschema/ir-unsupported-patternproperties-new.json --require-complete-ir
py -3.12 -X utf8 -m contractcompat.cli data/fixtures/proto/r1-field-removed-old.proto data/fixtures/proto/r1-field-removed-old.proto

# 复算门
py data/tools/gen_fixtures.py --check      # 72 个 fixture 位级一致
py data/tools/gen_golden.py --check        # 27 份 golden 逐字节一致

# 看一份 IR（三格式同一个出口）
py -3.12 -X utf8 -m contractcompat.cli \
  data/fixtures/avro/r1-field-removed-old.avsc \
  data/fixtures/avro/r1-field-removed-new.avsc --emit-ir
```

## 附：本棒做了但题面没要求的（如实记录）

- **抽出 `cli._assemble_report`**：M2 要求"报告侧渲染 `ir_unsupported`"，但 `verdict` 只有两值
  （不能造 `inconclusive`），判定核又没接上——所以本棒把装配抽成单点并直接可测，
  而不是渲染一份"空 findings + compatible"的假报告（那会被读成检查通过）。
- **修好 `tools/verify-layout-gate.py` 的 M3 组**：M1 改过 plan/06 的 G5 文案，写死的锚点失效，
  变异脚本在第 3 组直接崩（不是"门是假的"，是"验证脚本自己坏了"）。改成按表结构定位。
- **`plan/03` §3/§4 校准**：原文写"`allow_proto_text=True` 时尝试 protoc"与"支持 enum 顶层"，
  与实现（零子进程、只收顶层 record/error）不一致；按实现改写，不新增实现面。
