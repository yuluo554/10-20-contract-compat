# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`union-add-type-old.avsc` ｜ new=`union-add-type-new.avsc`
- tool: contractcompat 0.1.1

## 判定表（3 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R2 | total_amount | non-breaking | FORWARD_OK | union_branch_added | OLD_CONSUMER | bump-and-version |
| R5 | — | — | — | N/A | — | — |
| R6 | — | — | — | N/A | — | — |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — avro：Avro 无字段号概念（按字段名解析），本规则不适用
- `R6` ONEOF_MOVED — avro：Avro 无 oneof 概念；union 分支移动按 R2/R4 归因

---
digest: `490479011f90bb9ee16677048c34c6d46e2f89ac1750726e5d3dcdee29c6359e`（Markdown 是 JSON 的渲染视图，不参与 digest）
