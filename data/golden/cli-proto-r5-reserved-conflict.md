# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r5-reserved-conflict-old.pb` ｜ new=`r5-reserved-conflict-new.pb`
- tool: contractcompat 0.1.0.dev0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R5 | 2 | breaking | NONE_OK | field_number_reused_or_conflicts_with_reserved | OLD_CONSUMER | reserve |

---
digest: `bc5d79bb12b736724d8b65d9006f9357f711992cd7f33dbfeced99397c62f56d`（Markdown 是 JSON 的渲染视图，不参与 digest）
