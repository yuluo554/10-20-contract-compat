# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`ir-unsupported-recursive-ref-old.json` ｜ new=`ir-unsupported-recursive-ref-new.json`
- tool: contractcompat 0.1.1

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
digest: `f3e04174bdbf56cb07f81a068643c53e0b72945b0af591f2cce0dce60db1e607`（Markdown 是 JSON 的渲染视图，不参与 digest）
