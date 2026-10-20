# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r2-type-changed-old.json` ｜ new=`r2-type-changed-new.json`
- tool: contractcompat 0.1.0.dev0

## 判定表（2 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R2 | /properties/total_amount | breaking | NONE_OK | type_or_format_change | OLD_CONSUMER | bump-and-version |
| R5 | — | — | — | N/A | — | — |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — jsonschema：JSON Schema 无字段号概念（按属性名寻址），本规则不适用

---
digest: `c89a5ea2bce77cb7ae11f8318e051faddf3e9cc7cefc02af280a3065d988a610`（Markdown 是 JSON 的渲染视图，不参与 digest）
