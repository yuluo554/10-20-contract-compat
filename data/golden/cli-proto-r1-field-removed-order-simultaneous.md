# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r1-field-removed-old.pb` ｜ new=`r1-field-removed-new.pb`
- tool: contractcompat 0.1.1

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R1 | 2 | breaking | FORWARD_OK | field_number_missing_without_reserved | BOTH | reserve |

---
digest: `a6bc805630601e910e6bf76286eec0372937802b322f89e13021425ee1776445`（Markdown 是 JSON 的渲染视图，不参与 digest）
