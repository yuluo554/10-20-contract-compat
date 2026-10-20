# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r5-reserved-conflict-old.pb` ｜ new=`r5-reserved-conflict-new.pb`
- tool: contractcompat 0.1.0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R5 | 2 | breaking | NONE_OK | field_number_reused_or_conflicts_with_reserved | OLD_CONSUMER | reserve |

---
digest: `f4d6c4a398132ba36dc9aed4cbc89afe084e634a268c87f61749d8b632fc4eab`（Markdown 是 JSON 的渲染视图，不参与 digest）
