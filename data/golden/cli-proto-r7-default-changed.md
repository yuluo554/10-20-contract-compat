# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`r7-default-changed-old.pb` ｜ new=`r7-default-changed-new.pb`
- tool: contractcompat 0.1.1

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R7 | 2 | non-breaking | BOTH_OK | default_value_changed | OLD_CONSUMER | add-default |

---
digest: `a5af6e34076702527a7bd4dde9f98252b9f2839aaeb9d0fa5d34a4c4287ac4a9`（Markdown 是 JSON 的渲染视图，不参与 digest）
