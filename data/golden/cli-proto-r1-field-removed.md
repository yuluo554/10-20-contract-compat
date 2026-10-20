# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r1-field-removed-old.pb` ｜ new=`r1-field-removed-new.pb`
- tool: contractcompat 0.1.0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R1 | 2 | breaking | FORWARD_OK | field_number_missing_without_reserved | OLD_CONSUMER | reserve |

---
digest: `18bd3281bf921a7fe29bce637246b6700477fe80e7970ed896e02a8d5e9423a5`（Markdown 是 JSON 的渲染视图，不参与 digest）
