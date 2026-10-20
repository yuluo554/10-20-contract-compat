# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r1-field-removed-old.pb` ｜ new=`r1-field-removed-new.pb`
- tool: contractcompat 0.1.0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R1 | 2 | breaking | FORWARD_OK | field_number_missing_without_reserved | NEW_CONSUMER | reserve |

---
digest: `d6285d0f0c33cfd5950aab6744333b3bc6412ee7f7e31ae88dd8cee16a75d4bf`（Markdown 是 JSON 的渲染视图，不参与 digest）
