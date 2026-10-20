# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`r7-default-changed-old.pb` ｜ new=`r7-default-changed-new.pb`
- tool: contractcompat 0.1.0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R7 | 2 | non-breaking | BOTH_OK | default_value_changed | OLD_CONSUMER | add-default |

---
digest: `d3cb51c44a6e6d44fcd608199b4b64ff4bccdbf800994a23aea43f1f2c6c5ec9`（Markdown 是 JSON 的渲染视图，不参与 digest）
