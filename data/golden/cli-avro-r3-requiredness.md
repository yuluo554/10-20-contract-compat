# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`r3-requiredness-old.avsc` ｜ new=`r3-requiredness-new.avsc`
- tool: contractcompat 0.1.0.dev0

## 判定表（3 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R3 | status | non-breaking | BACKWARD_OK | new_field_without_default | OLD_CONSUMER | add-default |
| R5 | — | — | — | N/A | — | — |
| R6 | — | — | — | N/A | — | — |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — avro：Avro 无字段号概念（按字段名解析），本规则不适用
- `R6` ONEOF_MOVED — avro：Avro 无 oneof 概念；union 分支移动按 R2/R4 归因

---
digest: `c873ccd535ad5741f3d32fc62d6801b009a7ec1e2d9e8346a1a2db82d274a82b`（Markdown 是 JSON 的渲染视图，不参与 digest）
