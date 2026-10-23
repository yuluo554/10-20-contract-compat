# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`r4-enum-narrowed-old.json` ｜ new=`r4-enum-narrowed-new.json`
- tool: contractcompat 0.1.1

## 判定表（2 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R4 | /properties/status | non-breaking | BACKWARD_OK | enum_list_narrowed | OLD_CONSUMER | bump-and-version |
| R5 | — | — | — | N/A | — | — |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — jsonschema：JSON Schema 无字段号概念（按属性名寻址），本规则不适用

---
digest: `75d70de402c093d535d409fb9557c8132129c782eebcfef039836a09e968f634`（Markdown 是 JSON 的渲染视图，不参与 digest）
