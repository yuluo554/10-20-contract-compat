# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`rename-with-alias-old.avsc` ｜ new=`rename-with-alias-new.avsc`
- tool: contractcompat 0.1.1

## 判定表（2 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R5 | — | — | — | N/A | — | — |
| R6 | — | — | — | N/A | — | — |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — avro：Avro 无字段号概念（按字段名解析），本规则不适用
- `R6` ONEOF_MOVED — avro：Avro 无 oneof 概念；union 分支移动按 R2/R4 归因

---
digest: `d44fbfeb30f4e9f67e3b461c0984764432f328e76846be3ea5fbc13211494796`（Markdown 是 JSON 的渲染视图，不参与 digest）
