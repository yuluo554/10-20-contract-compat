# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r1-field-removed-old.pb` ｜ new=`r1-field-removed-new.pb`
- tool: contractcompat 0.1.1

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R1 | 2 | breaking | FORWARD_OK | field_number_missing_without_reserved | OLD_CONSUMER | reserve |

---
digest: `d63f56c5f47a498b3f125ee6aa2630f51c17b24ae69f8708cb3d89137dd59a08`（Markdown 是 JSON 的渲染视图，不参与 digest）
