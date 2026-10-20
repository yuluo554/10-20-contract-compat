# ContractCompat · 跨格式契约兼容性判定器

> 同一个「删字段」，在 Avro / Protobuf / JSON Schema 三种 IDL 里被两套黑话描述——
> 本工具把它们归一到**同一套判定语汇**，输出同一张表：破例规则、稳定路径（字段号 / JSON Pointer）、
> **砸的是老消费者还是新消费者**、最小修复动作。

`compat <old> <new> --policy backward` —— 两个文件、一条命令、零 registry、零网络、零 Kafka。

**当前版本**：`0.1.0.dev0`（M0 骨架：参数面、退出码契约、规范报告层已可跑；三解析器与判定核在 M2–M5 落地）。

## 为什么需要它

| 工具 | 覆盖 | 它不回答的那一格 |
|---|---|---|
| bufbuild/buf | 仅 Protobuf | 不跨格式；无跨 message 字段号复用检查 |
| Confluent Schema Registry | Avro / Protobuf / JSON Schema | 必须跑 registry + Kafka；JSON Schema 规则官方自承更复杂 |
| getsentry/json-schema-diff | 仅 JSON Schema | README 自述"大量特性未实现因而被忽略" |
| ExpediaGroup/avro-compatibility | 仅 Avro | 停更；无方向性归因 |
| datacontract-cli | 仅 ODCS 契约元数据 | 不吃原始 `.proto` / `.avsc`；不看字段号 / alias / enum 编号 |

**本工具的四个增量**（如实记录，不宣称首创）：

1. **跨格式归一**：一个"删字段"在三种 IDL 里得到同一个 rule_id、同一套方向性判定、同一句修复动作。
2. **方向性 + 归因**：不止 `is_breaking`，而是 `OLD_CONSUMER / NEW_CONSUMER / BOTH / REPLAY_ONLY`，
   且随发布顺序改变。
3. **字段号复用检查**：跨 message 复用与 reserved 冲突是一等规则（buf 的空白格）。
4. **双文件零部署**：不需要 registry、不需要 Kafka、不需要服务端。

> 星数与检索数均为 2026-10-20 的**快照**，会漂移；完整来源与"未逐行审计"的留白见
> `data/README.md` §一。这些数字**不进入代码常量或断言阈值**。

## 安装

```bash
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -e ".[dev]"
compat --version
```

需要 `protobuf`（只有 `.pb` 描述符输入才用）：

```bash
./.venv/Scripts/python.exe -m pip install -e ".[proto]"
```

## 三个最小复现

> 以下三条是**目标形态**（M5 完成后可跑；当前 M0 骨架只保证 `--help` / `--version` 与退出码契约）。

**Avro**：删字段

```bash
compat data/fixtures/avro/r1-field-removed-old.avsc data/fixtures/avro/r1-field-removed-new.avsc --policy backward
echo $?   # 1：backward 下删字段是 breaking
```

**Protobuf**：字段号复用（buf 不查的那一格）

```bash
compat data/fixtures/proto/r5-number-reuse-old.pb data/fixtures/proto/r5-number-reuse-new.pb --policy backward --format json
```

**JSON Schema**：`required` 收窄

```bash
compat data/fixtures/jsonschema/r3-requiredness-old.json data/fixtures/jsonschema/r3-requiredness-new.json --policy forward
```

**归因随发布顺序变化**（同一对文件，两种顺序，两个答案）：

```bash
compat a.avsc b.avsc --policy backward --deploy-order consumers-first   # 砸老消费者
compat a.avsc b.avsc --policy backward --deploy-order producers-first   # 砸新消费者
```

## 退出码

| 码 | 含义 |
|---|---|
| 0 | 该 policy 下无 breaking 项 |
| 1 | 有 breaking 项（含默认计入的 `runtime-dependent`） |
| 2 | 用法 / 输入错误 |
| 3 | 环境或能力不满足（缺 `protoc` / 缺 `protobuf` / IR 不可表达而要求完整） |

唯一定义见 `data/README.md` §4.5。

## 已知边界

- **`.proto` 文本不自行解析**：请先 `protoc --descriptor_set_out=<out.pb> --include_imports <file.proto>`；
  缺失 `protoc` 时退出码 3，**不降级猜测**。
- **不可表达的 JSON Schema 构造**（`patternProperties` / `if-then-else` / 递归 `$ref` / `dependentSchemas`）
  一律进 `ir_unsupported` 并在报告里显式输出，**不静默忽略**；`--require-complete-ir` 时退出码 3。
- **判定的是 schema 层面的可读性**，不是业务语义正确性。`runtime-dependent` 的存在正为此：
  静态必破 ≠ 线上必炸，报告同时给出触发条件，由人决定是否放行。
- **不做** OpenAPI 文档级 diff、Registry 服务、反例见证器、二进制回放验证（见 `plan/00` 弃选项表）。

## 开发

```bash
py tools/check-sprint-layout.py     # 方法论布局门（任何新对话的第一件事）
py -m pytest -q                     # 全量测试
```

本仓库遵循 `ai-tool-project-sprint` 方法论；计划文档在 `plan/`，判定口径的唯一权威在 `data/README.md` §四。

## 当前状态

| 里程碑 | 状态 |
|---|---|
| M0 | ✅ 已完成（2026-10-20） |
| M1 | ⬜ 未开始 |
| M2 | ⬜ 未开始 |
| M3 | ⬜ 未开始 |
| M4 | ⬜ 未开始 |
| M5 | ⬜ 未开始 |
| M6 | ⬜ 未开始 |

CI 状态：**本地等价校验（未接远端，CI 待首推验证）**——双解释器 pytest + 布局门 + CLI 冒烟在 M0 已跑；
GitHub Actions 工作流已落盘但尚未执行过。

## 许可

MIT
