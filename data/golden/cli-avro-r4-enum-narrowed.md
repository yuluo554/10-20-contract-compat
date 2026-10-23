# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`r4-enum-narrowed-old.avsc` ｜ new=`r4-enum-narrowed-new.avsc`
- tool: contractcompat 0.1.1

## 判定表（3 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R4 | status | non-breaking | BACKWARD_OK | symbol_removed | OLD_CONSUMER | bump-and-version |
| R5 | — | — | — | N/A | — | — |
| R6 | — | — | — | N/A | — | — |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — avro：Avro 无字段号概念（按字段名解析），本规则不适用
- `R6` ONEOF_MOVED — avro：Avro 无 oneof 概念；union 分支移动按 R2/R4 归因

---
digest: `f5fcec33ad6a57f531513ba8941dd72cad28acfff4e0dca05c89949cd0f7dc15`（Markdown 是 JSON 的渲染视图，不参与 digest）
