# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`add-optional-property-old.json` ｜ new=`add-optional-property-new.json`
- tool: contractcompat 0.1.1

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R5 | — | — | — | N/A | — | — |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — jsonschema：JSON Schema 无字段号概念（按属性名寻址），本规则不适用

---
digest: `18e86fd781a633bbda6e7acdcedb205ec15a6a8f25476901229f4da86ec1750a`（Markdown 是 JSON 的渲染视图，不参与 digest）
