# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`r6-oneof-moved-old.pb` ｜ new=`r6-oneof-moved-new.pb`
- tool: contractcompat 0.1.0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R6 | 2 | non-breaking | BOTH_OK | field_entered_or_left_oneof | OLD_CONSUMER | add-branch |

---
digest: `b4c6b7457ae3b1784514c42c5d8fda3c665e861c144aa02f1350488d14dea256`（Markdown 是 JSON 的渲染视图，不参与 digest）
