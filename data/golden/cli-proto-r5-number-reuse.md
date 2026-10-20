# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r5-number-reuse-old.pb` ｜ new=`r5-number-reuse-new.pb`
- tool: contractcompat 0.1.0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R5 | 2 | breaking | NONE_OK | field_number_reused_or_conflicts_with_reserved | OLD_CONSUMER | reserve |

---
digest: `98037a13f0f9bdb08ba1a39f28fe5af41b9579df2366168953ac663ab911d795`（Markdown 是 JSON 的渲染视图，不参与 digest）
