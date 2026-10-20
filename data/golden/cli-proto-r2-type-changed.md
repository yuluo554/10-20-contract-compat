# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r2-type-changed-old.pb` ｜ new=`r2-type-changed-new.pb`
- tool: contractcompat 0.1.0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R2 | 2 | breaking | NONE_OK | wire_incompatible_type_change | OLD_CONSUMER | bump-and-version |

---
digest: `1ea7a5d1f9bcf35eb27ec122e45769ba5562aa72887ac1769f807e05dfdd1dab`（Markdown 是 JSON 的渲染视图，不参与 digest）
