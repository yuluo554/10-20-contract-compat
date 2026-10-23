# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r6-oneof-moved-old.json` ｜ new=`r6-oneof-moved-new.json`
- tool: contractcompat 0.1.1

## 判定表（2 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R5 | — | — | — | N/A | — | — |
| R6 | /properties/payment | runtime-dependent | NONE_OK | oneof_or_anyof_branch_moved | OLD_CONSUMER | add-branch |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — jsonschema：JSON Schema 无字段号概念（按属性名寻址），本规则不适用

## runtime-dependent 说明

- `R6` @ `/properties/payment` — 静态必破：字段的 oneof 归属改变；静态上按旧 schema 写入的消息与新 schema 的成员约束不一致。 ｜ 触发条件：当消息体中确实携带被移动的成员时才会失败；若该成员在当前流量中从不出现，则线上不会触发。

---
digest: `7003d3d45bc0c78ab85e58cbf7f0aa49ef44fab808e972b580f7a34b3131644f`（Markdown 是 JSON 的渲染视图，不参与 digest）
