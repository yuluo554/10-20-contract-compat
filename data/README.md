# data · 依据查证、数据源可获取性与数值口径

> 本文件是**数值口径的唯一权威**。plan/01、plan/03 与代码里的公式/枚举均为便于阅读的摘录；若冲突，以本文件 §四 为准，并在同一提交内修正摘录。
> **基准日：2026-10-20。** 星数、push 时间、issue/PR 检索 total_count 均为**基准日快照**（会漂移），只用于选型与文档说明，**不得写进代码常量或断言阈值**。

## 一、依据查证记录（三态：✅ 已核对原文 / ⬜ 待核对或软论据）

### 1.1 已占位工具的覆盖边界（✅ 官方文档 / 仓库 README 原文，基准日 2026-10-20）

| 编号 | 工具 | 星数 | 覆盖格式 | 关键边界（✅ 已核对） |
|---|---|---|---|---|
| BUF | bufbuild/buf | 11,491 | Protobuf | 描述符级 diff；四档 `FILE` / `PACKAGE` / `WIRE_JSON` / `WIRE`；规则名如 `FIELD_NO_DELETE_UNLESS_NUMBER_RESERVED` / `FIELD_WIRE_COMPATIBLE_TYPE` / `ENUM_VALUE_SAME_NAME`；官方文档明写 **"Custom options are intentionally out of scope"**；**无跨 message 字段号复用检查**；只读 `.proto` |
| PROTOCOL | protolock | 631 | Protobuf | 最后 push 2024-02-12（停更约 2.7 年） |
| PBDE | googleapis/proto-breaking-change-detector | 23 | Protobuf | README 自述 **"not an officially supported Google project"** |
| JSDIFF | getsentry/json-schema-diff | 32 | JSON Schema（draft-07） | 输出 `is_breaking`；README 自述 **"work in progress… a lot of JSON Schema features are not implemented and therefore ignored"** |
| JSONCOMPAT | ostrowr/jsoncompat | 18 | JSON Schema 2020-12 + OpenAPI 3.1 Schema Object | 自称 **alpha**、"intentionally conservative"；无 Protobuf/Avro |
| AVROEXP | ExpediaGroup/avro-compatibility | 61 | Avro | 最后 push 2024-03-05；degauss 13★ / avrocheck 0★ |
| CG | Confluent Schema Registry | 2,470 | Avro / Protobuf / JSON Schema | 7 档 `BACKWARD` / `FORWARD` / `FULL` / `NONE` + `*_TRANSITIVE`；**必须跑 registry + Kafka**；JSON Schema 规则官方自承 **"looser based on Avro, but more complex"** |
| APICURIO | Apicurio / karapace / stencil | 944 / 639 / 237 | 多格式（服务端） | 均需部署 |
| OASDIFF | oasdiff / openapi-diff / openapi-changes / optic | 1,423 / 1,098 / 361 / 1,531（**archived**） | OpenAPI | 弃选方向（市场收敛） |
| DCF | datacontract-cli | 1,094 | **ODCS 契约元数据** | `datacontract breaking` 的规则在 `rules.py`：`property-added-or-removed` / `required-changed` / `type-changed` / `physical-name-changed`，基于 changelog path；**不吃原始 `.proto` / `.avsc` / JSON Schema**；不看字段号 / Avro alias / enum 编号 |
| STRICTLAND | event-driven-io/strictland | 25 | 快照式 | 要跑 Java 代码 |
| CW | **leodevnc/contract-witness** | 0 | **仅 JSON Schema** | created **2026-10-17**；方向性 `L(P) ⊆ L(C)` + 反例 + 混合版本矩阵；profile 已 drifted |
| SPECW | ateeqdesktop-dot/specwitness | 0 | 单格式 | — |

**判定（⬜ 检索推断，非市场调查）**：没有任何工具把三种 IDL 归一后给出同一套判定语汇，也没有工具回答"这个破坏砸在老消费者还是新消费者身上"。

### 1.2 需求侧原话（✅ 逐条核对链接，基准日 2026-10-20）

| 编号 | 类别 | 原话（节选，未改写） | 来源 |
|---|---|---|---|
| HN-22411747 | Avro 黑话导致误判 | "Adding a new type to a union? Breaking change. Adding a new element to an enum? Breaking change. **This is incorrect.** … you just need to use the resolving decoder that takes both schemas." | https://news.ycombinator.com/item?id=22411747 |
| CG-1778 | JSON Schema 兼容规则不可用（2021-02-22，标题 "Unclear Schema Evolution for JSON Schemas"） | "Compatibility checks related problems are stated as to be resolvable with Confluent Schema Registry **but they are not if JSON Schema used.**"；引官方文档："The JSON Schema compatibility rules are loosely based on similar rules for Avro, however, **the rules for backward compatibility are more complex.**" | https://github.com/confluentinc/schema-registry/issues/1778 |
| HN-21429460 | 删"无用"列导致灰度期老版本报错（2019-11-02） | "non-backward compatible schema migration (dropping an « unused » column) **triggered errors on the previous authentication service version during rollout**" | https://news.ycombinator.com/item?id=21429460 |
| HN-28034882 | 事件驱动架构整体焦虑（284 pts / 168 comments） | "Is there any company out there that has fully embraced this type of architecture… handling **breaking schema changes**… Every event-driven architectural pattern I've read about can quite easily fall apart." | https://news.ycombinator.com/item?id=28034882 |
| HN-23931907 | 头部实践确有自建工具（618 pts） | "There's some **in-house tooling that checks the schemas of producers against consumers against known versions** (aka the versions in production), and we run it as part of the CI." | https://news.ycombinator.com/item?id=23931907 |
| HN-33408887 | 需求直白的缺口（205 pts） | "**I don't know of any existing linter that could check for backwards compatibility**, but I am interested in one. Buf, from the OP, does this with `buf breaking`." | https://news.ycombinator.com/item?id=33408887 |

### 1.3 反向证据与"不可采信来源"声明

| 编号 | 事项 | 状态 | 说明 |
|---|---|---|---|
| SHOWHN-47519460 | jsoncompat 第一次 Show HN（2026-03-25）**2 pts / 0 评论** | ✅ | 单格式 JSON Schema diff 工具的曝光度基准线 |
| SHOWHN-47656093 | jsoncompat 第二次 Show HN（2026-04-06）**7 pts / 0 评论** | ✅ | 同上；两次都没有讨论 |
| GH-ISSUE-POLLUTION | GitHub **issue** 检索 `"breaking change" schema consumer producer` → **13212 条**，**已被合成 / AI 生成仓库严重污染**（0★ 仓库挂大编号 issue） | ⬜ **不作需求证据** | 题面 / README / 本文件一律**不得**把这个数字当需求强度论据。需求强度只用 §1.2 的原话 |

### 1.4 开源空白检索（⬜ 软论据：`gh api` 检索式 + total_count，基准日 2026-10-20）

| 检索式 | total_count | 头部 / 说明 |
|---|---|---|
| `protobuf avro json schema compatibility multi-format` | **0** | — |
| `protobuf avro json schema unified` | **0** | — |
| `schema evolution compatibility cross-format` | **0** | — |
| `schema compatibility matrix avro protobuf json` | **0** | — |
| `protobuf avro thrift compatibility check` | **0** | — |
| `avro protobuf schema equivalence` | **0** | — |
| `rolling upgrade schema compatibility` | **0** | — |
| `consumer driven contract schema evolution` | **0** | — |
| `schema registry compatibility file based` | **0** | — |
| `jsonschema compatibility checker in:name` | **0** | — |
| `thrift schema compatibility` | **0** | — |
| `schema compatibility witness counterexample` | 2 | contract-witness 0★、specwitness 0★ |
| `schema evolution compatibility` | 34 | 最高 7★ |
| `avro schema resolution` | 6 | 最高 1★ |
| `protobuf breaking change` | 20 | buf-action 63★，第 2 名即 2★ |
| `avro compatibility` | 49 | ExpediaGroup 61★ |
| `json schema diff` | 179 | getsentry 32★ |
| `schema compatibility` | 401 | stencil 237★、revapi 223★ |
| `schema breaking change` | 293 | **graphql-inspector 1,767★**（GraphQL 已占） |

**结论（⬜）**：十条跨格式检索式 total_count 为 0；单格式各有成熟工具；唯一在建的"方向性 + 反例"项目只覆盖 JSON Schema。**这是检索推断，不是市场调查；题面与 README 不得写"首创 / 无人做过"。**

## 二、数据源可获取性记录

| 数据源 | 三态 | 获取方式 | 备注 / 阻断原因 |
|---|---|---|---|
| 需求侧原话（HN ×5 + GitHub issue ×1，共 6 条） | ✅ 已获取 | 直接打开链接核对，原话照抄 | 基准日 2026-10-20；链接若失效，按"原话已存档于本文件"处理，**不重新编造** |
| 反向证据（两次 Show HN 的分数与评论数） | ✅ 已获取 | 直接打开 HN item 页 | 分数会随时间变化，引用须带基准日 |
| 竞品仓库元信息（星数 / 语言 / 建仓与最后 push） | ✅ 已获取（快照） | GitHub 仓库页 / `gh api` | 星数与时间会漂移，属 ⬜ 软论据 |
| buf 四档与规则名、custom options 范围 | ✅ 已获取 | buf 官方文档 | 只引用**规则语义与档位语义**，不复制文档全文 |
| Confluent 七档与 JSON Schema 规则说明 | ✅ 已获取 | Confluent 官方文档 + issue 引文 | 同上；"more complex" 为官方原文引文 |
| datacontract-cli 的 breaking 规则集 | ✅ 已获取 | 仓库源码 `rules.py` | 只记录规则名与作用面（ODCS 元数据），不做能力评价 |
| getsentry/json-schema-diff 与 jsoncompat 的自述 | ✅ 已获取 | 两个仓库 README | 引号内为原文，其余为转述 |
| Avro 1.12 规范的字段演化与 alias 语义 | ⬜ 待逐条核对入库 | 规范原文 | **仅引用规则语义，不复制全文**；入库时补条目编号 |
| JSON Schema 集合语义（`required` / `enum` / `oneOf`） | ⬜ 待逐条核对入库 | 规范原文 | 同上；首期只覆盖可在 IR 里表达的构造 |
| Protobuf `FileDescriptorProto` 字段语义 | ⬜ 待逐条核对入库 | protobuf 描述符文档 | 首期只用到 `field` / `number` / `label` / `type` / `default_value` / `reserved_*` / `oneof_index` |
| `.proto` 文本解析 | ✅ 已确认不可达（不走） | — | **阻断原因**：不自行解析，必须由用户提供 `FileDescriptorSet`（`protoc --descriptor_set_out`）；缺 `protoc` → 退出码 3 |
| 不可表达的 JSON Schema 构造清单 | ⬜ 待 M2 定稿 | 实现期枚举 | 首期至少覆盖 `patternProperties` / `if-then-else` / 递归 `$ref`，落 `ir_unsupported` |
| 真实生产 schema 语料 | **不采信** | — | 阻断原因：没有任何公开、可复算、许可清晰的跨格式生产语料；**全部 fixture 自建**，不引用他人 schema |

## 三、合成数据纪律

- **全部 fixture 为自建最小 schema**，字段名一律使用中性占位（`order_id` / `total_amount` / `status` 这类通用词），**不含任何真实公司、产品、人员或内部字段名**。
- **不使用真实手机号 / 身份证 / 邮箱 / DOI / 文号**。若需要示例值，一律用保留值：手机号 `19900000000` 段、邮箱 `example.invalid` 域、DOI 前缀 `10.9999/`、文档编号以 `SYNTH-` 开头。**白名单即此四类，超出即视为泄露**。
- **反例必须存在**：每个"破例"用例都要配一条"看起来破但实际不破"的反例（如 Avro union 新增类型在 resolving decoder 下不破、Protobuf 删字段但已 `reserved` 号）。反例的作用是**防止规则退化成"看到变化就报破"**。
- **同一语义必须三格式各一份**：`data/fixtures/{proto,avro,jsonschema}/` 下对同一破例（如"删字段"）各放一对 `old` / `new`，供 M2/M3 断言"三格式语义一致"。**不允许只做一个格式然后宣称跨格式**（红线①的可机械检查形态）。
- **fixture 与 golden 的关系**：fixture 是输入，golden 是期望输出。golden 由生成脚本按 §四 口径产出并入库；测试只读 golden 比对，**不在测试里重算期望值**（否则实现错、期望也错，永远绿）。

## 四、数值口径（唯一定义处）

> 本节是全部枚举与阈值的**唯一权威**。plan/01、plan/03、代码、README 只说"见 data/README.md §4.x"，不得复制第二份表述。

### 4.1 七档兼容策略（语义对齐 Confluent 七档）

记 `P_old` = 旧 schema（线上已写入数据的那版），`P_new` = 新 schema。

| policy | 定义 | 判定式 |
|---|---|---|
| `backward` | **新生产者 → 老消费者**：新 schema 写出的数据，必须能被按旧 schema 读取的消费者解析 | 读路径 `P_new → P_old` 全部必填字段可解析 |
| `forward` | **旧数据 → 新消费者**：按旧 schema 写出的数据，必须能被新 schema 的消费者解析 | 读路径 `P_old → P_new` 全部必填字段可解析 |
| `full` | `backward` 且 `forward` | 两者同时成立 |
| `none` | 只列差异，不判定 | `verdict` 恒 `compatible`，差异项照常输出 |
| `backward-transitive` | 与**所有历史版本**（`--history` 给定序列）都满足 `backward` | 对 `--history` 中每个版本 `h`：`P_new → h` 可解析 |
| `forward-transitive` | 与所有历史版本都满足 `forward` | 对 `--history` 中每个版本 `h`：`h → P_new` 可解析 |
| `full-transitive` | 上述两者同时成立 | 两者同时成立 |

- `*-transitive` **必须**带 `--history`（版本文件序列）；缺省 → 退出码 2，**不降级为单版本**（降级会把"与历史不兼容"静默报成"兼容"）。
- `verdict` ∈ `{compatible, breaking}` 只有两值；**方向性信息在 `direction` 字段**，`severity` 的三值是另一维度（见 4.4）。三个字段不得互相替代。

### 4.2 buf 四档映射（只表达"最接近"，**不宣称等价**）

| 本题 policy | buf 档 | 关系说明 |
|---|---|---|
| `backward` | `WIRE`（JSON 视图取 `WIRE_JSON`） | buf 的档 = **检查哪些规则**；本题的 policy = **允许哪个方向**。二者维度不同 |
| `forward` | **无直接对应** | buf 不区分方向，只判"是否破坏" |
| `full` | `WIRE` + `WIRE_JSON` 同时通过 | 最接近的近似，不等价 |
| `none` | — | buf 无"只列差异不判定"档 |

**使用规则**：`--explain-mapping` 输出的表**必须**逐行带"关系说明"，且必须包含"只表达最接近、不宣称等价"字样；测试断言这两点。**不得**在 README 或报告里写成"兼容 buf 四档"或"等效于 `buf breaking --against`"。

### 4.3 七类破例规则（rule_id / 三格式证据形态 / 默认 severity）

| rule_id | 名称 | 稳定路径 | 默认 severity | Protobuf 证据 | Avro 证据 | JSON Schema 证据 |
|---|---|---|---|---|---|---|
| R1 | `FIELD_REMOVED` | P: 字段号 / A: 字段名 / J: JSON Pointer | `breaking`（`backward`） | 字段号消失且未 `reserved`（`FIELD_NO_DELETE_UNLESS_NUMBER_RESERVED` 的语义） | 字段从 `fields` 消失；**改名未声明 `aliases` 时判定为 remove + add** | `properties` 键消失或从 `required` 移除 |
| R2 | `TYPE_CHANGED` | 同上 | `breaking`（非 wire 兼容）/ `runtime-dependent`（wire 兼容但语义变） | wire 兼容性判定（`FIELD_WIRE_COMPATIBLE_TYPE` 语义）+ 非兼容类型改 | `type` / `logicalType` 变化 | `type` / `format` 变化 |
| R3 | `REQUIREDNESS_CHANGED` | 同上 | `breaking`（加必填无默认）/ `non-breaking`（加可选） | `optional ↔ required`、新增无默认字段 | 新增字段无 `default` | `required` 列表增删 |
| R4 | `ENUM_NARROWED` | 同上（enum 值名/编号） | **`runtime-dependent`** | enum 值删除或改名（`ENUM_VALUE_SAME_NAME` 语义） | `symbols` 删除 | `enum` 列表收窄 |
| R5 | `FIELD_NUMBER_REUSED` | P: 字段号 | `breaking` | 字段号复用（含**跨 message** 复用）或与 `reserved` 冲突 | `N/A`（Avro 无字段号，**显式标注**） | `N/A`（JSON Schema 无字段号，**显式标注**） |
| R6 | `ONEOF_MOVED` | P: 字段号 + oneof 名 / A: union 索引 / J: JSON Pointer | `runtime-dependent` | 字段进出 `oneof` / oneof 改名 | `N/A`（Avro 无 oneof；union 分支移动按 R4/R2 归因） | `oneOf` / `anyOf` 分支移动 |
| R7 | `DEFAULT_CHANGED` | 同上 | `non-breaking`（读侧） / `runtime-dependent`（写侧含义变） | `default_value` 变更 | `default` 变更 | `default` 变更 |

- **`N/A` 是显式结论，不是缺失值**：R5/R6 在 Avro、JSON Schema 下的 `N/A` 必须出现在输出里（`format_evidence: "N/A"` + 一行理由），**不得省略该行**。省略就等于"这个格式没这问题"，而事实是"这个格式没有这个概念"。
- **同一个语义、三种证据、同一修复动作**：R1 在 Avro 下的"alias 缺失"不单列为第八条规则——它就是 R1 的 Avro 证据形态，修复动作同为中心化 `alias`。

### 4.4 `runtime-dependent` 标注条件（红线③的定义处）

`severity` 是**三值枚举**：`breaking` / `runtime-dependent` / `non-breaking`。**禁止把任一命中压成二选一。**

一条命中标 `runtime-dependent` **当且仅当同时满足**：

1. **静态上必然不满足**当前 policy 的判定式（即静态分析判它 `breaking`）；
2. **且**是否真的触发取决于运行时数据或发布顺序，而不是 schema 本身：
   - 被收窄的 enum 值在现有数据流中从未出现；
   - 新增必填字段在所有生产者的现有消息里恒有值；
   - 被移动的 `oneof` 成员在当前流量中从不出现；
   - 字段号被复用但旧编号的字段在保留期内从未写入。

输出要求（缺一即视为违约）：

- `severity: "runtime-dependent"`；
- `why_static_breaking`：一段文字，说明它在静态上破坏了哪条判定式；
- `what_would_trigger`：一段文字，说明什么条件下会真的炸；
- **条目必须出现在 `--format=md` 与 `--format=json` 两种输出里**。

判定强度（与条目存在性解耦）：

- `--strict-runtime-dependent`（**默认开**）：`runtime-dependent` 计入退出码 1。
- `--ignore-runtime-dependent`：只把它从"是否退出 1"里摘出，**条目与两段说明照旧输出**。

### 4.5 退出码矩阵（唯一定义处）

| 退出码 | 含义 | 触发条件 |
|---|---|---|
| `0` | 该 policy 下无 breaking 项 | `--policy none`；或全部命中为 `non-breaking`；或仅有 `runtime-dependent` 且给了 `--ignore-runtime-dependent` |
| `1` | 有 breaking 项 | 存在 `breaking`；或存在 `runtime-dependent` 且处于默认严格档 |
| `2` | 用法 / 输入错误 | 未知 policy；`*-transitive` 缺 `--history`；schema 文件解析失败（含非法 JSON / 非法 `FileDescriptorSet`）；`--history` 版本数 0 |
| `3` | 环境或能力不满足 | 需要 `protoc` 而未安装；`--require-complete-ir` 且存在 `ir_unsupported`；输入格式不受支持 |

退出码**只有这四个值**，不新增、不复用。`2` 与 `3` 的区别是：`2` 是调用方写错，`3` 是环境给不了。

### 4.6 归因四态（"谁会炸"）

| `blast_radius` | 含义 | 典型触发 |
|---|---|---|
| `OLD_CONSUMER` | 线上**老版本消费者**会读不懂新数据 | `consumers-first` 部署下的删字段 / 类型收窄 |
| `NEW_CONSUMER` | **新版本消费者**会读不懂还在流里的老数据 | `producers-first` 部署下的删字段 / 加必填 |
| `BOTH` | 两个方向都读不懂 | `simultaneous` 部署下的 `full` 违反 |
| `REPLAY_ONLY` | 只有**历史数据重放**时炸，实时流量不炸 | `--deploy-order replay` 下的 enum 收窄 |

- **归因只由三元组决定**：`(direction 判定, deploy_order, 该格式的字段可寻址性)`。字段可寻址性：Protobuf 按字段号（可跳过未知字段）、Avro 按字段名 + alias、JSON Schema 按属性名（未知属性默认容忍，除非 `additionalProperties: false`）。
- **不给 `--deploy-order` 时 `blast_radius` 为 `null`**，`notes` 写 `deploy_order_not_given`，**不猜、不给默认顺序**。
- `REPLAY_ONLY` **只在显式给 `replay` 时出现**，不默认推断。

### 4.7 报告确定性口径

- 规范 JSON：键序固定（按本文件 §4.x 顺序），差异项按 `(rule_id, stable_path)` 排序，`fields` 按 `(number 若存在, json_pointer, name)` 排序。
- **禁止字段**：`as_of`、扫描耗时、绝对路径、主机名、用户名、locale、Python 版本、`protoc` 版本（版本信息可写进 `environment` 节但**不参与 digest**）。
- `digest = sha256(规范化 JSON 字节)`；`--verify` 读回报告后用同一份输入重算并逐字节比对，先比内容再比 digest（先比 digest 会把"哪一处被改了"盖掉）。
