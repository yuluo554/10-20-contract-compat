# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r2-type-changed-old.avsc` ｜ new=`r2-type-changed-new.avsc`
- tool: contractcompat 0.1.0.dev0

## 判定表（4 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R2 | total_amount | breaking | NONE_OK | type_or_logical_type_change | OLD_CONSUMER | bump-and-version |
| R5 | — | — | — | N/A | — | — |
| R6 | — | — | — | N/A | — | — |
| R7 | total_amount | non-breaking | BOTH_OK | default_changed | OLD_CONSUMER | add-default |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — avro：Avro 无字段号概念（按字段名解析），本规则不适用
- `R6` ONEOF_MOVED — avro：Avro 无 oneof 概念；union 分支移动按 R2/R4 归因

---
digest: `8914707275f52ca8d96f7cb836568763880c640abf539d11573cee1a79581376`（Markdown 是 JSON 的渲染视图，不参与 digest）
