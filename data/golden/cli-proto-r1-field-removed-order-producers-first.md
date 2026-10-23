# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r1-field-removed-old.pb` ｜ new=`r1-field-removed-new.pb`
- tool: contractcompat 0.1.1

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R1 | 2 | breaking | FORWARD_OK | field_number_missing_without_reserved | NEW_CONSUMER | reserve |

---
digest: `4fca7439e49c09e82e6143c6563a2aae526261c008becfd837e23e8a58e26187`（Markdown 是 JSON 的渲染视图，不参与 digest）
