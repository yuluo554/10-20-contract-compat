# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`r3-requiredness-old.pb` ｜ new=`r3-requiredness-new.pb`
- tool: contractcompat 0.1.0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R3 | 2 | non-breaking | BACKWARD_OK | label_change_or_new_required_without_default | OLD_CONSUMER | add-default |

---
digest: `1828bf1bf252e0c9ae3b5c731251237643c7566fbcd9405b76d28b8cc114f7ae`（Markdown 是 JSON 的渲染视图，不参与 digest）
