# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`ir-unsupported-patternproperties-old.json` ｜ new=`ir-unsupported-patternproperties-new.json`
- tool: contractcompat 0.1.0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R5 | — | — | — | N/A | — | — |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — jsonschema：JSON Schema 无字段号概念（按属性名寻址），本规则不适用

## 不可表达的构造（ir_unsupported）

- `patternProperties` @ `/patternProperties` — 首期 IR 不建模 patternProperties：无法在不做正则/依赖求解的前提下枚举其语义

---
digest: `b7da4d4240af32619a33f3a26aa33c567a3a80617564417a842830fb1323ff92`（Markdown 是 JSON 的渲染视图，不参与 digest）
