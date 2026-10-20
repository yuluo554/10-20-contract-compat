# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`r7-default-changed-old.json` ｜ new=`r7-default-changed-new.json`
- tool: contractcompat 0.1.0

## 判定表（2 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R5 | — | — | — | N/A | — | — |
| R7 | /properties/status | non-breaking | BOTH_OK | default_changed | OLD_CONSUMER | add-default |

## 该格式不适用的规则（N/A 是结论，不是缺格）

- `R5` FIELD_NUMBER_REUSED — jsonschema：JSON Schema 无字段号概念（按属性名寻址），本规则不适用

---
digest: `0ed82b93059be8c4c64f141e8906f86352cb49f2c41796ae3c487491204bf35f`（Markdown 是 JSON 的渲染视图，不参与 digest）
