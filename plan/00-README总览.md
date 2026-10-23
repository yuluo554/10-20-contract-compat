# 00 · README 总览 — 10-20-contract-compat（跨格式契约兼容性判定器）

> 方法论：`ai-tool-project-sprint`（装订 2026-10-20）｜布局门：`py tools/check-sprint-layout.py`｜续接对话第一件事 = 跑它

- 性质：不参赛项目题 · 发布 GitHub **公开仓库** · 署名 yuluo554
- 定位宣言："buf 用 `FILE/PACKAGE/WIRE_JSON/WIRE` 四档，Confluent 用 `BACKWARD/FORWARD/FULL` 七档，JSON Schema 生态各说各话——**同一个『删字段』在三种格式里被两套黑话描述，跨格式团队必然误判**。本工具把 Avro / Protobuf / JSON Schema 三种 schema 归一到同一套判定语汇，输出同一张表：破例规则、稳定路径（字段号 / JSON Pointer）、**砸的是老消费者还是新消费者**、最小修复动作。"
- 交付形态：**纯本地双文件 CLI（`compat <old> <new>`；零 registry、零网络、零 Kafka、零模型）**。单一形态，不设备选。
- 发布：GitHub 公开仓库，v0.1.0（tag + Release 附产物 + 发布留档 `plan/RELEASE-M6.md`）。
- 查证基准日：**2026-10-20**。

## 文档索引表

| 文档 | 内容 | 状态 |
|---|---|---|
| plan/00-README总览.md | 本文档：索引 / 决策记录（含四条红线）/ 弃选项 / 承诺-证据台账 / 里程碑 | ✅ v1 |
| plan/01-题目文档.md | 十段式题目定稿（含已占位工具覆盖表、需求原话、反向证据、空白检索、招牌动词表） | ✅ v1 |
| plan/02-架构与技术选型.md | 分层架构、IR 设计、判定核、确定性架构、退出码契约、选型与弃选 | ✅ v1（M0） |
| plan/03-模块详设.md | 五模块接口、数据结构、处理顺序、失败路径、测试点 | ✅ v1（M0） |
| plan/04-数据计划.md | 三格式 fixture 设计、golden 纪律、覆盖度口径 | ✅ v1（M0） |
| plan/05-里程碑.md | 每周可演示物、出口门、环境事实、风险预案 | ✅ v1（M0） |
| plan/06-交付对标.md | 题面 §三/§四逐条落位、发布前检查清单 | ✅ v1（M0） |
| plan/HANDOFF-M1.md | 第 1 棒（数据先行）交接快照 | ✅ M0 收尾产出 |
| plan/HANDOFF-M2.md | 第 2 棒（统一 IR 收口）交接快照 | ✅ M1 收尾产出 |
| plan/HANDOFF-M3.md | 第 3 棒（方向性判定核）交接快照 | ✅ M2 收尾产出 |
| plan/HANDOFF-M4.md | 第 4 棒（破例规则库）交接快照 | ✅ M3 收尾产出 |
| data/README.md | 依据查证记录（三态）/ 数据源可获取性 / 合成数据纪律 / 数值口径（唯一定义处） | ✅ v1 |
| README.md | 面向使用者的首屏：一句话定位、三条最小复现、已占位工具覆盖表摘录 | ✅ 骨架版（M6 定稿） |
| pyproject.toml / src/contractcompat/ / rules/ / tests/ | 可安装 CLI、五模块（参数面 + 退出码契约 + 三解析器 + 方向性判定核 + 规则库 + 归因）、规则表、测试（357 项） | ✅ M0 骨架 + M1–M5 |
| tools/check-sprint-layout.py | 方法论布局门（8 组变异验证通过） | ✅ M0 |
| tools/verify-layout-gate.py | 布局门的变异验证脚本（门自身的证伪） | ✅ M0 |
| .github/workflows/ci.yml | CI 三腿矩阵（`matrix = os × py`，`exclude: ubuntu × 3.8`）；**已实跑**：run `39457916512` 三腿全绿（各 357 passed，镜像 `ubuntu-24.04`） | ✅ M0（首推 + M6 实跑验证） |
| data/fixtures/{proto,avro,jsonschema,negatives}/ | 三格式最小 fixture：20 对规则夹具（21 格中 18 格有夹具 + 3 格 N/A 结论）+ 4 反例 + 4 不可表达 | ✅ M1 |
| data/golden/ | IR 形态 golden ×28 + policy 判定 golden ×28 + 端到端 cli-*.md/json ×62 + 台账 | ✅ M1（IR）+ M3（policy）+ M5（端到端） |
| data/tools/ | `gen_fixtures.py`（`.pb` 程序化构造 + `--check`）、`gen_golden.py`（只调 CLI + `--check`） | ✅ M1 |
| plan/RELEASE-M6.md | 发布留档（tag 时点事实 / tag 后追加事实两栏） | ✅ M6（两栏 + 覆盖对账 + 判据变异验证） |
| .gitignore | Python 标准模板 | ✅ M0（首提交） |

## 决策记录表

> 本表同时登记已定案决策与**弃选项**（含弃选理由），后续里程碑不再重复论证。

### 四条红线（任何里程碑都不得越过；越过即视为设计变更，须先改本表）

| # | 红线 | 为什么是红线 |
|---|---|---|
| ① | **不做第三个单格式工具**：**首屏（README 第一屏 + CLI 第一个示例）必须同时给出 Avro 与 Protobuf 的同一张表**，这是本题唯一护城河 | 单格式方向已被占满：Protobuf 有 buf 11,491★，Avro 有 ExpediaGroup 61★，JSON Schema 有 getsentry 32★ / jsoncompat 18★。第三个单格式工具既无增量，也过不了"LLM 聊天为什么做不到"的拷问。**任何时候交付物退化成"单格式 diff"，本题即失败**——这条同时是可机械检查的：首屏示例若只出现一种格式，视为红线违反 |
| ② | **不碰 OpenAPI** | oasdiff 1,423★ / openapi-diff 1,098★ / openapi-changes 361★ 已占，且 **optic 1,531★ 已 archived** = 该方向进入市场收敛期；新入者拿不到增量，还会把"跨 IDL 归一"的窄缝冲淡。OpenAPI 只允许作为 JSON Schema 的**承载容器**被间接读到（Schema Object），绝不提供 OpenAPI 文档级 diff |
| ③ | **`runtime-dependent` 必须显式标注，不能把 enum 收窄含糊成二选一** | HN-22411747 骂的正是这件事（"Breaking change… **This is incorrect.** … you just need to use the resolving decoder that takes both schemas."）；Confluent 官方也自承 JSON Schema 规则 "more complex"。**压成 breaking/non-breaking 二选一，就是把现存工具被骂的毛病再犯一遍**。实现上 `severity` 是三值枚举，`--ignore-runtime-dependent` 只能改变退出码，**不能删条目** |
| ④ | **同期竞品盯防**：**leodevnc/contract-witness（created 2026-10-17，0★）** 已在做"方向性 + 反例 + 混合版本矩阵" | 它证明"方向性判定"这个点子已有人动手，而且就在 3 天前。**判断（⬜ 非实测数据）：窗口期约 1–2 个月**（依据：0★、单格式、单作者、建仓 3 天；若它扩到 Avro/Protobuf 则窗口关闭）。**差异化只能靠跨格式**——本题不得把竞争力押在"方向性"本身，也不得做反例见证器（那是它的主场）。每周复核一次该仓库是否新增格式支持 |

### 已定案决策

| 日期 | 决策 | 结论与理由 |
|---|---|---|
| 2026-10-20 | **如实记录：本题不是无人区** | Protobuf 侧 buf 11,491★ 已把规则名做成事实标准；Avro 侧 ExpediaGroup 61★；JSON Schema 侧 getsentry 32★ / jsoncompat 18★；多格式**服务端**有 Confluent 2,470★ / Apicurio 944★ / karapace 639★。**本题的增量只有四条：跨格式 IR 归一、方向性判定归一、"谁会炸"归因、双文件零部署。** 题面 / README / data/README 一律不得写"首创 / 空白 / 无人做过"，只能写"未检索到"并附检索式与基准日 |
| 2026-10-20 | **交付形态收敛为唯一：纯本地双文件 CLI** | 输入两个 schema 文件，输出一张表。不做 GUI、不做桌面、不做 Web、不做服务端；这样"交付路径 == 验收路径"（验收就是跑那条命令），也避免空壳形态 |
| 2026-10-20 | **`severity` 是三值，且三值都是"结论"** | `breaking` / `runtime-dependent` / `non-breaking`。默认 `runtime-dependent` 计入退出码（宁可让人看一眼），`--ignore-runtime-dependent` 只降判定强度、不删条目。理由：静默丢条目比误报危害大（HN-21429460 的教训正是"看起来没用"） |
| 2026-10-20 | **归因必须随 `--deploy-order` 变化，不提供"默认顺序"** | 不给默认值：不给 `--deploy-order` 时归因字段为 `null` 并在 `notes` 写 `deploy_order_not_given`，**不猜**。理由：默认值会被当成结论用，而这恰恰是本题要消除的误判 |
| 2026-10-20 | **`.proto` 文本不自行解析，必须走 `protoc --descriptor_set_out`** | buf 已经用 `FileDescriptorProto` 做事实标准；自写 `.proto` 文本解析器是首期最大的伪工作量，且会引入与 buf 不一致的语义。缺 `protoc` → 退出码 3，不降级猜测 |
| 2026-10-20 | **JSON Schema 不可表达的构造必须落 `ir_unsupported`** | getsentry/json-schema-diff 的 README 自述 "a lot of JSON Schema features are **not implemented and therefore ignored**"——这正是本题要避免的失败模式。`patternProperties` / `if-then-else` / 递归 `$ref` 等未支持构造**显式列出**；`--require-complete-ir` 时以退出码 3 拒绝出结论 |
| 2026-10-20 | **报告不写时间戳 / 路径 / 主机名** | 报告要能被 `--verify` 重算 sha256 digest；这些字段会让同一输入在不同机器上产生不同字节 |
| 2026-10-20 | **规则表是数据不是代码** | 七类规则的命中条件放在 `rules/` 的定值表里（可被测试逐条遍历），不在代码里散落 if；这样"每条规则三格式各有用例"才能机械核对 |
| 2026-10-20 | **Python 底线 = 3.8** | 本机可提供的解释器含 3.8 与 3.12 两档；不依赖 3.9+ 语法，避免下游 CI 装不上。首期唯一第三方依赖 `protobuf`（用于 `FileDescriptorSet` 解析），其余为标准库 |
| 2026-10-20 | **DoD 产物口径 = A) Release 附产物** | `git archive <tag>` + `gzip -9n` + `SHA256SUMS`，本地留副本；**M6 行写死"Release 附产物"，不得在重写里程碑表时省略这三个字** |
| 2026-10-20 | **布局门用 Python 实现**（`tools/check-sprint-layout.py`） | 项目是 Python 项目，CI 与本地都不必额外装 Node；判据集与模板一致（判据不改，只换语言）。8 组变异验证已过，见 `tools/verify-layout-gate.py` |
| 2026-10-20 | **`protobuf` 是可选依赖**（extra `proto`），不进核心依赖 | 核心判定路径（Avro / JSON Schema / 判定 / 报告）零第三方依赖；只有 `.pb` 输入才需要它。缺它时退出码 3，不降级 |
| 2026-10-20 | **版本单一来源 = `__init__.__version__`**，`pyproject` 走 `dynamic` | 避免两处手改漏一处 |
| 2026-10-20 | **规则表双份：仓库根为源、包内 `data/` 为镜像** | wheel 安装后仓库根的 `rules/` 不存在，判定仍必须可用；镜像由逐字节测试守住（干净 venv 装 wheel 已实测） |
| 2026-10-20 | **骨架期未实现路径一律退出码 3**，绝不返回 0 | 返回 0 的空壳会把"没检查"读成"检查通过"（本 skill 明令禁止的形态） |
| 2026-10-20 | **`.pb` fixture 用 `protobuf` 库程序化构造，不用 `protoc` 生成** | 本机无 protoc；程序化构造可入仓、可 `--check` 位级复现、CI 不装 protoc 也能跑全量 fixture。实测 py3.8（protobuf 5.29.6）与 py3.12（protobuf 7.36.2）产出的描述符**逐字节相同**。代价：protobuf 大版本若改序列化，`--check` 会红——这是**有意**的（漂移必须显眼） |
| 2026-10-20 | **M2 只做"收口与证伪"，不改判定语义**：报告装配抽成 `cli._assemble_report`（判定阶段与 IR 阶段共用一条路径），`--require-complete-ir` 拒收时逐条点名构造；**不新增 `inconclusive` verdict** | `verdict` 只有 `compatible`/`breaking` 两值（`data/README.md` §4.1）——在 IR 阶段造第三值或渲染空 findings 的报告，会被读成"检查通过"。所以 M2 的 IR 阶段只做"拒 + 报构造名"，完整报告仍等 M3 判定核接上 |
| 2026-10-20 | **M1 提前落地三解析器（IR 映射）**，因为 M1 的 golden 以 **IR 形态**存在 | 交付物必须是真值："IR 形态 golden"只能用真实解析结果产出；手写期望 IR 等于伪造。副作用：M2 的解析器部分已基本满足，HANDOFF-M2 已如实登记 M2 剩余面（报告侧 `ir_unsupported` 渲染路径 + 双跑断言 + 解析器单测补齐） |
| 2026-10-20 | **M3 的普通报告用"差异项桥"进 `findings`**（`rule_id` / `severity` 留 `null`，附 `findings_stage_pending_M4`），退出码在没有 severity 分类时回落到 `verdict` | 不这样做，报告会把"有 breaking"渲染成"（无命中）"——那正是本项目最忌的假阴性。桥只搬运事实，不做规则求值；M4 接上 `rules.evaluate` 后必须替换，M4 交接单已列为硬约束 |
| 2026-10-20 | **`--emit-policy` 是数据导出模式（与 `--emit-ir` 同构）**，退出码 0 只表示导出成功 | policy golden 必须由 CLI 产出（生成器不自己算判定），但规则/归因尚未实现；导出模式让 M3 能冻结真值而不伪造 severity。transitive 档缺 `--history` 时写 `null` + note，**不拿单版本冒充** |

### 弃选项（含理由）

| 日期 | 弃选项 | 理由 |
|---|---|---|
| 2026-10-20 | 弃：OpenAPI 文档级 diff | oasdiff 1,423★ / openapi-diff 1,098★ / openapi-changes 361★ 已占；**optic 1,531★ 已 archived** = 市场已收敛，新入者无增量（红线②） |
| 2026-10-20 | 弃：纯 JSON Schema diff | 红海（`json schema diff` 179 条）；反向证据：jsoncompat 两次 Show HN 分别 **2 pts / 7 pts、均 0 评论**（47519460 / 47656093），说明单格式 diff 工具很难被看见 |
| 2026-10-20 | 弃：纯 Protobuf 破例检查 | buf 11,491★ 已覆盖全部规则且规则名成事实标准；protolock 631★、proto-breaking-change-detector 23★ 也已占 |
| 2026-10-20 | 弃：Schema Registry 服务 | Confluent 2,470★ / Apicurio 944★ / karapace 639★ / stencil 237★ 都需部署；本题的卖点恰恰是"不部署" |
| 2026-10-20 | 弃：Avro-only | ExpediaGroup/avro-compatibility 61★（2024-03-05 停更）、degauss 13★、avrocheck 0★ 已占 |
| 2026-10-20 | 弃：Thrift | `thrift schema compatibility` 检索 total_count **0**，生态已死，无受众 |
| 2026-10-20 | 弃：GraphQL | graphql-inspector 1,767★ 已占（`schema breaking change` 头部） |
| 2026-10-20 | 弃：反例见证器（`L(P) ⊆ L(C)` + 反例输出） | leodevnc/contract-witness（2026-10-17 建仓）与 ateeqdesktop-dot/specwitness 已占；且**跨格式反例需要编码器**（随机生成满足 P 不满足 C 的实例），会引入采样与随机种子，破坏"同一输入两次运行逐字节一致"的确定性纪律。仅作扩展项的可选输出（红线④） |
| 2026-10-20 | 弃：二进制回放验证 | 结论取决于采样数据，不可复算；与确定性纪律直接冲突，且会把题面从"schema 层判定"拖进"数据层验证" |
| 2026-10-20 | 弃：混合版本部署矩阵进首期 | 需要 N 版本 × 部署版本的矩阵求解，依赖 M2 内核但工作量独立；首期只做四种发布顺序的**归因**，矩阵列二期。**不在首期承诺它，避免空转** |
| 2026-10-20 | 弃：自写 `.proto` 文本解析器 | 见"已定案决策"；与 buf 语义对齐的成本远高于收益 |
| 2026-10-20 | 弃：运行时拦截 / 代理 / 服务端门禁 | 不介入生产流量；本题只在 CI 与本地读文件，隐私红线要求纯本地零网络 |

## 承诺-证据台账

> 全项目只此一份；其他文档只可引用，不得复制。状态列随里程碑删成"不适用"或翻转，**不得滞后**。

| 承诺项 | 素材来源 | 交付物内可达性 | 核验方式 | 状态 |
|---|---|---|---|---|
| 三格式归一 IR | `google.protobuf.descriptor_pb2`（`FileDescriptorProto`）/ Avro `.avsc` 纯 JSON / JSON Schema `dict` 树（✅ 规则语义已核，⬜ 逐条入库） | `compat <old> <new> --emit-ir`（规范 JSON：`{inputs, old, new, digest}`） | M2：三格式 fixture 的 IR 七项逐项断言（`tests/test_parser_{avro,jsonschema,proto}.py`）+ 54 份 schema 输入双跑逐字节一致 + 与 `data/golden/ir-*.json` 逐字节一致（`gen_golden.py --check`） | ✅ M2 |
| 方向性判定七档 | Confluent 官方档位语义（✅ 文档已核，见 CG-1778 引文） | `--policy` 参数 + `verdict` / `differences[*].direction` | M3 `data/golden/policy-*.json` 七档矩阵（transitive 基线 = old）+ `tests/test_policy.py` | ✅ M3 |
| buf 四档映射 | buf 官方文档档位与规则名（✅） | `--explain-mapping` 输出表 | 测试断言映射表逐行存在且含"只表达最接近、不宣称等价"字样（md/json 两种出口） | ✅ M3 |
| 七类破例规则 | 三格式规范语义（⬜ 逐条核对入库，不复制全文） | `findings[*].rule_id` | M4 `tests/test_rules.py` 逐格真跑命中（18 格 20 对）+ `test_severity.py` 三值 + `test_negatives.py` 4 反例无误报 | ✅ M4 |
| `runtime-dependent` 三值语义 | HN-22411747 原话（✅）+ Confluent JSON Schema 自承（✅） | `findings[*].severity` + 两段说明 | M4：条目存在、两段说明在 md/json 两个出口、严格档退出码 1、`--ignore-runtime-dependent` 不删条目 | ✅ M4 |
| 字段号复用检查（跨 message / 与 reserved 冲突） | buf 规则集未覆盖该格（✅ 已核官方规则名） | R5 命中记录 | M4：三种形态各一条用例（同 message 换主人 / reserved 冲突 / **跨 message**），后者由 `meta.messages` 文件级求值 | ✅ M4 |
| "谁会炸"归因四态 | HN-21429460 事故原话（✅） | `blast_radius` + `--deploy-order` | M5：`tests/test_blast.py` 四顺序各断言一次 + `tests/test_golden.py::test_four_state_quadruple_exists_and_differs` 的 golden 四联 | ✅ M5 |
| 最小修复动作 | 三格式语法落点（✅ 语法明确） | `repair_action` + 描述文本 | M5：`tests/test_blast.py::test_r1_repair_hint_matches_format_syntax` 三格式各一条（文本取自规则表）；`cli-proto/avro/jsonschema-*.md` golden 落盘 | ✅ M5 |
| CLI + 退出码矩阵 | 退出码定义唯一在 `data/README.md` §4.5 | `compat` 命令 | M5：0/1 在"四态归因 + 三值 severity"下补齐（`tests/test_cli.py`），2/3 沿用 M0–M4 证据 | ✅ M5 |
| 报告 digest 与 `--verify` | 规范 JSON（固定键序、无时间戳/路径/主机名） | `digest` + `--verify` | M5：改 `blast_radius` 一字节 → 非 0 且 `json_path` 指到 `findings[0].blast_radius`（重放 baseline，`tests/test_cli.py`）；换时区 digest 不变 | ✅ M5 |
| golden 逐字节比对 | `data/golden/*.json` / `*.md` | CLI 输出 | M5：`--check` 全绿（IR ×28 + policy ×28 + 端到端 cli-* ×62） | ✅ M5 |
| README 三场景复现 | 三条最小命令 | `README.md` | M6 仓库外干净 clone + 新 venv 逐条真跑，退出码 0/1/1 符合声明；归因四联逐条真跑 | ✅ M6 |
| 已占位工具覆盖表 | 官方文档 / 仓库 README / `gh api` 快照（✅ 除星数会漂移） | `README.md` 首屏 | M6 逐行对账完成（快照日期 2026-10-20 声明保留；竞品当周复核） | ✅ M6 |

## 里程碑

> 出口门写死；**DoD 列只能加不能减**——要减必须在决策记录新增一行理由并同步改题面。

| 里程碑 | 内容 | 出口门 | 状态 |
|---|---|---|---|
| M0 | 出题定稿 + 计划套件 + 方法论装订 + 可运行骨架 | plan/00–06 齐且 `plan/00` 顶部有装订行；`AGENTS.md` 与布局门在位（8 组变异逐组变红）；`data/README.md` 口径落定；`pyproject.toml` + 包骨架 + `compat` 命令可跑；`--help`/`--version` 可用；退出码 2/3 路径真跑；CI workflow 本地 YAML 解析通过；双解释器 pytest 全绿 | ✅ 已完成（2026-10-20） |
| M1 | **数据先行**：三格式 fixture + golden | `data/fixtures/{proto,avro,jsonschema}/` 每条规则 × 每种格式一对 old/new（21 格登记 21/21 = 18 对 + 3 格 N/A 结论）；**同一个"删字段"在三种格式下各一套 fixture**；golden 生成脚本 `--check` 位级一致（M1 只冻 **IR 形态**——七档判定 golden 顺延 M3，**未伪造**）；反例 4/4（"看起来破但不破"，如 Avro union 加类型） | ✅ 已完成（2026-10-20） |
| M2 | 统一 IR | 三格式各 fixture 解析出同构 IR（字段名/字段号/类型/基数/默认值/enum 编号/reserved 七项齐全）；不可表达构造落 `ir_unsupported`；同机双跑逐字节一致 | ✅ 已完成（2026-10-20） |
| M3 | 方向性判定核 | 七档 policy 全部可用；同一"删字段"三格式语义一致（backward 破 / forward 不破）；`--explain-mapping` 输出 buf 四档映射表；`*-transitive` 缺 `--history` 时退出码 2；`policy-*.json` 七档矩阵 ×27 | ✅ 已完成（2026-10-20） |
| M4 | 破例规则库 | 七类规则三格式各有用例；`severity` 三值完整；`runtime-dependent` 带 `why_static_breaking` + `what_would_trigger` 两段；字段号复用（跨 message / 与 reserved 冲突）命中正确 | ✅ 已完成（2026-10-20） |
| M5 | 归因与 CLI | `blast_radius` 随 `--deploy-order` 变化（四种顺序各断言）；`repair_action` 三格式语法落点正确；退出码 0/1/2/3 全覆盖；golden 逐字节；`--verify` 篡改可定位 | ✅ 已完成（2026-10-20） |
| M6 | 发布 | 干净环境按 README 跑通三场景；**`git tag` + GitHub Release（附产物：`git archive` 源码包 + `SHA256SUMS`，本地留副本）+ `plan/RELEASE-M6.md` 发布留档（tag 时点事实 / tag 后追加事实两栏）**；发布 GitHub **公开仓库**；收尾跑发布终态自检门（M6 同轮实现，落地前不在本表点名路径）无 FAIL | ✅ 已完成（2026-10-20，v0.1.0） |

## 台账使用说明

- 台账状态列在对应里程碑完成的**同一次提交**里翻转，不得滞后。
- 任何一条承诺若在开发中被砍，必须在决策记录表新增一行说明理由，并同步删除题面对应措辞；**不得只改台账不改题面**。
- 台账里"⬜ Mx"的行是欠债：M6 标完成时它们必须已翻转，或明确写"永不进判定路径"并说明。
