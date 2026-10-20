# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`ir-unsupported-if-then-else-old.json` ｜ new=`ir-unsupported-if-then-else-new.json`
- tool: contractcompat 0.1.0.dev0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R5 | — | — | — | N/A | — | — |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — jsonschema：JSON Schema 无字段号概念（按属性名寻址），本规则不适用

## 不可表达的构造（ir_unsupported）

- `if` @ `/if` — 首期 IR 不建模 if/then/else 条件分支：需要约束求解，且会破坏「同一输入同一结论」的确定性

---
digest: `b38c85df88d8c30ec7b267ce2b27a28fc954e166e957c277e93a8aca9dae2748`（Markdown 是 JSON 的渲染视图，不参与 digest）
