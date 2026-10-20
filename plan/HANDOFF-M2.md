# HANDOFF-M2 · 统一 IR 收口交接单

> 用法（用户侧启动命令，绝对路径只在对话里给）：
> `/goal 读取 "<项目绝对路径>\plan\HANDOFF-M2.md" 继续完成任务`
> **第一动作 = 跑 `py tools/check-sprint-layout.py`**（门红了先修布局，再干活）。
> 上一棒：M1（数据先行：fixture + 反例 + IR golden + 生成器），已完成并 commit。

## 一、当前进度与证据

| 项 | 状态 | 证据（可复跑的命令） |
|---|---|---|
| 21 格覆盖（7 规则 × 3 格式） | ✅ | `py -3.12 -X utf8 -m pytest tests/test_coverage.py -q -s` → 打印矩阵 + `21 格登记 21/21（18 对夹具 + 3 格 N/A）` |
| 反例 4/4 | ✅ | `py -3.12 -X utf8 -m pytest tests/test_fixtures.py -q`（4 条反例的 IR 形态逐条断言） |
| `ir_unsupported` 4/4 | ✅ | 同上：`patternProperties` / `if` / `recursive_ref` / `dependentSchemas` 各一条，new 侧非空、old 侧为空 |
| fixture 生成器 + 位级复算 | ✅ | `py data/tools/gen_fixtures.py --check` → `全绿（72 个文件逐字节一致）` |
| IR golden ×27 + 逐字节复算 | ✅ | `py data/tools/gen_golden.py --check` → `全绿（27 份 golden 逐字节一致）` |
| golden 生成器只调 CLI | ✅ | `data/tools/gen_golden.py` 全文只有 `subprocess` 调 `python -m contractcompat.cli ... --emit-ir`，无判定逻辑 |
| 三解析器 → IR | ✅（M1 提前落地） | `compat <old> <new> --emit-ir`；27 份 golden 就是三格式真实解析结果 |
| 测试全量 | ✅ 本地等价校验 | `py -3.12 -X utf8 -m pytest -q` 与 `py -3.8 -X utf8 -m pytest -q` 均 **161 passed** |
| 安装面 | ✅ | wheel 装进**干净 venv**、仓库外跑 `--emit-ir`，digest 与入库 golden **完全相同**；sdist 含 27 golden + 72 fixture + 两个生成器 |
| CI | ⏳ **未接远端，CI 待首推验证** | workflow 加了 fixture/golden 复算两步，本地 `yaml.safe_load` + 步数与步名断言通过（`tests/test_workflow.py`） |

**数据状态**：`data/fixtures/` 72 个文件（54 份 schema 输入 + 18 份 `.proto` 人读源文本）已入仓；
`data/golden/` 27 份 IR golden + `README.md` 台账已入仓。**`data/golden/policy-*.json` 不存在**——
七档方向性判定 golden 要等 M3，`data/golden/README.md` 已如实标注"待 M3 生成"。

## 二、当前事实 · 状态不变量（下一棒动手前必须知道）

| # | 事实 | 后果 / 禁区 |
|---|---|---|
| 1 | **M1 提前实现了三解析器**（IR 映射体），因为"IR 形态 golden"只能用真实解析结果产出 | 别当成"M2 已经做完了"：`policy.diff` / `rules.evaluate` / `blast.attribute` 仍是 `NotImplementedError`，普通 `compat <old> <new>` **仍退出 3** |
| 2 | `--emit-ir` 是**唯一**的 IR 出口，且**绕过判定**（在 `policy.diff` 之前 return 0） | 它不产出 `verdict`/`findings`；别把它的退出码 0 读成"兼容"——这是数据导出模式，不是判定 |
| 3 | `.pb` 由 `data/tools/gen_fixtures.py` **程序化构造**（`SerializeToString(deterministic=True)`），不经 protoc | 改 fixture 必须改生成器再 `--check`；直接手改 `.pb` 必红。protobuf 大版本改序列化也会红——**红是对的** |
| 4 | `detect_format` 判描述符用**往返校验**（Parse → 重新序列化 → 逐字节比），不是"NUL 字节" | 实测踩过：合法的 `FileDescriptorSet` 可以全是可打印 ASCII；用 NUL 判会把 `.pb` 判成 proto 文本（exit 3） |
| 5 | Avro 的 `Field.number` 与 `json_pointer` **都是 None** | 稳定路径 = 字段名（`data/README.md` §4.3）。**不要**为了"七项齐"给 Avro 编字段号——那会让 R5 在 Avro 下假命中（N/A 结论就假了） |
| 6 | Protobuf 的 enum/message 字段 `type` 用**短类型名**（`Status`），不用 `enum` | 跨格式可比：Avro 那边也叫 `Status`；写成 `enum` 会让"同一语义"在三格式里三种说法 |
| 7 | JSON Schema 的 enum 取值标签用 `_literal_label`（手写字面量），**不是** `json.dumps` | 全仓 `json.dumps(` 只允许在 `canonical.py`（`test_architecture.py` 守门） |
| 8 | 递归 `$ref` **不跟随展开**：`$defs`/`definitions` 子树本来就会被遍历 | 跟随会让同一构造报两次，还会把指针变成相对递归点的怪路径 |
| 9 | `walk_unsupported` 对 `if/then/else` 一组**只记一条**（`break`） | `UNSUPPORTED_CONSTRUCTS` 里仍列 `then`/`else` 供未来扩展；别以为漏了 |
| 10 | 规则表两份（源 + 包内镜像）必须同步 | `test_packaged_mirror_matches_source` 会红 |
| 11 | 布局门的 `LAYOUT.DOC_TOOLS` 只扫**根目录** `tools/`；`data/tools/` 不在扫描面 | 写到 `data/tools/` 的脚本文档点名了也不会被这条判据检查——所以本棒另加了 `tests/test_golden.py` 的实物断言 |
| 12 | 退出码 2/3 的分流写死在异常类上（`UsageError`=2 / `CapabilityError`=3） | 新错误先归到这两类，别在 CLI 里写散落的 `return 2` |

## 三、下一棒待办（M2：统一 IR 收口）

M1 已把解析体的主干做完，M2 只做**收口与证伪**。按顺序做，每步留可复跑证据：

1. **补解析器单测**（`plan/03` §3/§4/§5 列了测试点，现在只有 fixture 级覆盖）：
   `tests/test_parser_avro.py` / `test_parser_jsonschema.py` / `test_parser_proto.py`。
   重点：字段七项逐个断言、`$ref` 可达与不可达、非法输入 → 退出码 2。
2. **缺 protobuf → 退出码 3 的桩测试**：`builtins.__import__` 桩（**不要**依赖本机装没装）。
   现在 `protobuf_available()` 只回答"能不能 import"，桩要打在 `descriptor_pb2` 的 import 上。
   ⚠️ `parsers/proto.py` 里 `_protobuf_module()` 在 `parsers/__init__.py`，`parse_descriptor_set` 在
   `parsers/proto.py`；桩要覆盖两处（`detect_format` 与 `parse` 各走一次）。
3. **同文件双跑 `to_json` 逐字节一致**：`parse(p)` 两次 → `canonical.dumps` 相等。
   批量版可用 `data/tools/gen_golden.py --check` 的两层断言，但 M2 要一条**单文件**断言。
4. **`--require-complete-ir` 的 exit 3 真跑到**：现在 `cli._run` 的这条分支只在 parse 之后
   检查 `ir_unsupported`，可以真跑：
   `compat data/fixtures/jsonschema/ir-unsupported-patternproperties-new.json <same> --require-complete-ir`
   → **必须 3**，不得 0。
5. **报告侧渲染 `ir_unsupported`**：`report.to_markdown` 已有"不可表达构造"小节，但普通路径
   现在到不了（`policy.diff` 未实现）。M2 可以先把"IR 阶段就拒/就报"的路径跑通；
   真正进判定报告要等 M3。
6. **解析器对越界输入的行为**：空 message、无 `properties` 的 JSON Schema、Avro 空 `fields`。
   现在的实现返回空 IR，**这是有意的**（空 schema 合法）；但要有用例把这条钉住，
   否则以后改坏了没人知道。
7. **收尾**：DoD → 回写 `plan/00`/`plan/05`/`plan/06`/`README` 状态 → 写 `plan/HANDOFF-M3.md` → commit → 跑布局门。

**不要做**：不要为了"demo 好看"把 `policy.diff` 写个返回 `[]` 的壳；不要手写 `policy-*.json` golden。

## 四、既定口径清单（K 编号；动了会打挂测试的约定）

> M1 新增 K13–K15；K1–K12 未变（原文见 `plan/HANDOFF-M1.md` §四）。

| K | 口径 | 位置（唯一可编辑副本） | 打挂哪条 |
|---|---|---|---|
| K1–K12 | 见 `plan/HANDOFF-M1.md` §四（规范 JSON / digest / IR 序 / 三态 default / 12 键 / 排序 / 七档 / transitive / 规则表 / 退出码 / 版本 / 口径唯一处） | 同左 | 同左 |
| K13 | fixture 命名 = `<rule_id>-<slug>-{old,new}.<ext>`；反例 = `negatives/<slug>-{old,new}.<ext>`；不可表达 = `jsonschema/ir-unsupported-<slug>-{old,new}.json` | `tests/fixture_scan.py`（扫描判据）+ `data/tools/gen_fixtures.py`（产出） | `tests/test_coverage.py`、`test_fixtures.py`、`gen_golden.py` 的配对 |
| K14 | IR golden 文件名 = `ir-<dir>-<slug>.json`；`<dir>` ∈ {proto, avro, jsonschema, negatives} | `data/tools/gen_golden.py:golden_name` | `tests/test_golden.py` 的台账双向对账 |
| K15 | `--emit-ir` 输出 = `{inputs, old, new, digest}`，`inputs` 只写 basename | `cli.py:_render_ir` | 全部 27 份 golden |

## 五、本机环境坑（全部实测，带日期）

| 坑 | 实测 | 处置 |
|---|---|---|
| `python` 是商店占位符 | 2026-10-20 | 一律 `py` / `py -3.12` / `py -3.8` |
| `py -3.12 -X utf8` 选项顺序 | 2026-10-20 | 版本号在 `-X` **之前** |
| 本机无 `protoc` | 2026-10-20 | `.pb` 走程序化构造；`.proto` 文本 → exit 3（真缺件态） |
| `protobuf` 版本两档不同 | 2026-10-20 | `py -3.12`=7.36.2 / `py -3.8`=5.29.6；**描述符字节逐字节相同**（实测 sha256 一致）。大版本升级要重跑 `gen_fixtures.py --check` |
| 描述符不含 NUL 字节 | 2026-10-20 | `\\n[` 开头的描述符曾被判成"非法 JSON"；判据改成往返校验 |
| 测试里的 subprocess 需要 `PYTHONPATH` | 2026-10-20 | `tests/test_golden.py` 自己拼 `PYTHONPATH=src`；CI 里是 `pip install -e .`，两种都要能跑 |
| 无远端 | 2026-10-20 | `git remote -v` 为空；CI 一律写"待首推验证" |

## 六、DoD 逐项 checklist（M1 → 交接时点）

- [x] 21 格（7 规则 × 3 格式）**全部登记**：18 对夹具 + 3 格 N/A（理由来自规则表）
- [x] 反例 4 条，且**每条都有 IR 形态断言**（alias 在、reserved 在、union 只加分支、可选不进 required）
- [x] `ir_unsupported` 用例 4 条，new 侧非空、old 侧为空、构造名对号
- [x] `data/tools/gen_golden.py` 只调 CLI（无判定逻辑）
- [x] `gen_golden.py --check` 逐字节一致（27 份）；`gen_fixtures.py --check` 位级一致（72 份）
- [x] 覆盖矩阵由脚本计算并打印（`tests/test_coverage.py`），不手填
- [x] IR golden 27 份（19 规则对 + 4 反例 + 4 不可表达），落盘并 `--check` 逐字节一致
- [x] `data/golden/README.md` 台账与磁盘**双向对账**（`test_readme_golden_table_is_bidirectional`）
- [x] README 台账里 `policy-*.json` 明确标"待 M3"，且盘上**确实没有**
- [x] 双解释器 pytest 全绿（3.8 / 3.12，各 161 项）
- [x] 干净 venv 装 wheel → 仓库外 `--emit-ir` → digest 与 golden 相同
- [x] HANDOFF-M2 落盘并 commit
- [ ] CI 实跑 —— **未接远端，待首推**（M6）
- [ ] 干净 clone 按 README 跑通 —— M6

## 七、关键命令速查

```bash
# 方法论门（任何新对话第一件事）
py tools/check-sprint-layout.py

# 全量测试（双解释器）
py -3.12 -X utf8 -m pytest -q
py -3.8  -X utf8 -m pytest -q

# 覆盖矩阵（打印出来，不是手填）
py -3.12 -X utf8 -m pytest tests/test_coverage.py -q -s

# 复算门
py data/tools/gen_fixtures.py --check      # 72 个 fixture 位级一致
py data/tools/gen_golden.py --check        # 27 份 golden 逐字节一致

# 看一份 IR（三格式同一个出口）
py -3.12 -X utf8 -m contractcompat.cli \
  data/fixtures/avro/r1-field-removed-old.avsc \
  data/fixtures/avro/r1-field-removed-new.avsc --emit-ir

# 局部
py -3.12 -X utf8 -m pytest -q tests/test_fixtures.py   # fixture 语义
py -3.12 -X utf8 -m pytest -q tests/test_golden.py     # golden 形态 + 复算
py -3.12 -X utf8 -m pytest -q tests/test_workflow.py   # CI YAML 本地解析
```

## 附：本棒做了但题面没要求的（如实记录）

- **`--emit-ir` 是新增的 CLI 出口**。题面只要求 `compat <old> <new>` 出判定报告；
  但"golden 生成器只调 CLI"这条纪律要求 CLI 能产出 IR，否则生成器只能自己去 import 解析器，
  那就退化成"生成器与实现各写一遍"。它不参与判定，也不改变任何退出码语义。
- **三解析器在 M1 落地**（原计划 M2）。理由同上：IR 形态 golden 的期望值必须是真实解析结果。
  代价是 M2 的解析器部分已基本满足，所以 HANDOFF-M2 §三 把 M2 收窄成"补单测 + 补双跑 + 真跑 exit 3"。
- **`data/fixtures/negatives/` 按 plan/04 的 N/A 口径只放了 4 对**（三格式混放，扩展名区分）。
  `plan/04` §一 原写"三格式各一组"，实际是"四条反例，分别落在它真正成立的那个格式上"——
  Protobuf 没有 union，Avro 没有 property，硬凑三格式会让反例本身失真。
- **CI 增了两步复算门**，并把 `protobuf` 加进 `dev` extras：缺依赖时 pytest 会 skip，
  而 skip 与 pass 在日志里长得一样——那正是本项目反复要避免的形态。
