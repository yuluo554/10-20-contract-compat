# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r5-number-reuse-old.pb` ｜ new=`r5-number-reuse-new.pb`
- tool: contractcompat 0.1.1

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R5 | 2 | breaking | NONE_OK | field_number_reused_or_conflicts_with_reserved | OLD_CONSUMER | reserve |

---
digest: `d0df5e14b1f6e195485a70eb59833ae9309ead0b41f47a8e7b5a99356c72f38d`（Markdown 是 JSON 的渲染视图，不参与 digest）
