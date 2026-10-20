# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r1-field-removed-old.pb` ｜ new=`r1-field-removed-new.pb`
- tool: contractcompat 0.1.0.dev0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R1 | 2 | breaking | FORWARD_OK | field_number_missing_without_reserved | REPLAY_ONLY | reserve |

---
digest: `502b38132e9f8bf2d3a0ac7e04e2a627b8f3f757edd680348077bdf4075cdcab`（Markdown 是 JSON 的渲染视图，不参与 digest）
