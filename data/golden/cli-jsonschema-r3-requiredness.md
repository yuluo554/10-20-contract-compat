# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`r3-requiredness-old.json` ｜ new=`r3-requiredness-new.json`
- tool: contractcompat 0.1.1

## 判定表（2 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R3 | /properties/total_amount | non-breaking | BACKWARD_OK | required_list_added | OLD_CONSUMER | add-default |
| R5 | — | — | — | N/A | — | — |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — jsonschema：JSON Schema 无字段号概念（按属性名寻址），本规则不适用

---
digest: `342d85ebad8883d0a23ccbb21afa119dc95e08749f27dc06a76914063a76cbd2`（Markdown 是 JSON 的渲染视图，不参与 digest）
