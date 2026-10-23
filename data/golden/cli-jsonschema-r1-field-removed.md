# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r1-field-removed-old.json` ｜ new=`r1-field-removed-new.json`
- tool: contractcompat 0.1.1

## 判定表（2 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R1 | /properties/total_amount | breaking | FORWARD_OK | property_absent_or_removed_from_required | OLD_CONSUMER | reserve |
| R5 | — | — | — | N/A | — | — |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — jsonschema：JSON Schema 无字段号概念（按属性名寻址），本规则不适用

---
digest: `d03aae2f60deef04161691d7b12b4327fb0420df67eeed56edaa1160baac35e0`（Markdown 是 JSON 的渲染视图，不参与 digest）
