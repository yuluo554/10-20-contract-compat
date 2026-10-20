# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`ir-unsupported-recursive-ref-old.json` ｜ new=`ir-unsupported-recursive-ref-new.json`
- tool: contractcompat 0.1.0.dev0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R5 | — | — | — | N/A | — | — |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — jsonschema：JSON Schema 无字段号概念（按属性名寻址），本规则不适用

## 不可表达的构造（ir_unsupported）

- `recursive_ref` @ `/$defs/Node/properties/child/$ref` — 自引用/环引用 '#/$defs/Node'：不展开（会栈溢出），按不可表达登记
- `recursive_ref` @ `/properties/root/$ref` — 自引用/环引用 '#/$defs/Node'：不展开（会栈溢出），按不可表达登记

---
digest: `6704ab953d0cf4bcd6b8cc7a1e3a86ca95dbba9d307dfa4307a3aa3534cab9c0`（Markdown 是 JSON 的渲染视图，不参与 digest）
