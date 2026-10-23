# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r5-cross-message-reuse-old.pb` ｜ new=`r5-cross-message-reuse-new.pb`
- tool: contractcompat 0.1.1

## 判定表（2 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R1 | 2 | breaking | FORWARD_OK | field_number_missing_without_reserved | OLD_CONSUMER | reserve |
| R5 | Order.2 | breaking | NONE_OK | field_number_reused_across_messages | OLD_CONSUMER | reserve |

---
digest: `299274a7fe988304c5adb12eb8bc41642583bab4ea4c1a15e93386aa1cc12c1a`（Markdown 是 JSON 的渲染视图，不参与 digest）
