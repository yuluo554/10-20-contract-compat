# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`r7-default-changed-old.pb` ｜ new=`r7-default-changed-new.pb`
- tool: contractcompat 0.1.0.dev0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R7 | 2 | non-breaking | BOTH_OK | default_value_changed | OLD_CONSUMER | add-default |

---
digest: `9bc33bd1f7fe44ea7148f464f1bb4b8b5c64726e4af8e1f642faa7e840406056`（Markdown 是 JSON 的渲染视图，不参与 digest）
