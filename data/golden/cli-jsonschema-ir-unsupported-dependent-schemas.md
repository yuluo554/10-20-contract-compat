# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`ir-unsupported-dependent-schemas-old.json` ｜ new=`ir-unsupported-dependent-schemas-new.json`
- tool: contractcompat 0.1.1

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R5 | — | — | — | N/A | — | — |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — jsonschema：JSON Schema 无字段号概念（按属性名寻址），本规则不适用

## 不可表达的构造（ir_unsupported）

- `dependentSchemas` @ `/dependentSchemas` — 首期 IR 不建模 dependentSchemas：无法在不做正则/依赖求解的前提下枚举其语义

---
digest: `fcaa724c3b54834d02416b902f9347a90f763af9c411d1b6ea61dca1fe581614`（Markdown 是 JSON 的渲染视图，不参与 digest）
