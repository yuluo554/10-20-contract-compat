# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r5-reserved-conflict-old.pb` ｜ new=`r5-reserved-conflict-new.pb`
- tool: contractcompat 0.1.1

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R5 | 2 | breaking | NONE_OK | field_number_reused_or_conflicts_with_reserved | OLD_CONSUMER | reserve |

---
digest: `1f937083842e7ed272ca266ba712bf907b5f16c8209ba62ef3374fb93144a7c1`（Markdown 是 JSON 的渲染视图，不参与 digest）
