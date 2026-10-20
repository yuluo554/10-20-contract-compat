# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r1-field-removed-old.avsc` ｜ new=`r1-field-removed-new.avsc`
- tool: contractcompat 0.1.0

## 判定表（3 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R1 | total_amount | breaking | FORWARD_OK | field_absent_or_renamed_without_alias | OLD_CONSUMER | reserve |
| R5 | — | — | — | N/A | — | — |
| R6 | — | — | — | N/A | — | — |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — avro：Avro 无字段号概念（按字段名解析），本规则不适用
- `R6` ONEOF_MOVED — avro：Avro 无 oneof 概念；union 分支移动按 R2/R4 归因

---
digest: `3d9e3e6c482f274f6176bb41906850a79db892e08fe05802a3ca59159ff249ed`（Markdown 是 JSON 的渲染视图，不参与 digest）
