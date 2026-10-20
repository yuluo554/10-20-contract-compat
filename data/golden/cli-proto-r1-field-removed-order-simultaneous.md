# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r1-field-removed-old.pb` ｜ new=`r1-field-removed-new.pb`
- tool: contractcompat 0.1.0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R1 | 2 | breaking | FORWARD_OK | field_number_missing_without_reserved | BOTH | reserve |

---
digest: `2562b141ebd95103031f3c47ef697e1e4a0ee50bf967c4a6cc788616a6313c7c`（Markdown 是 JSON 的渲染视图，不参与 digest）
