# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`r3-requiredness-old.pb` ｜ new=`r3-requiredness-new.pb`
- tool: contractcompat 0.1.0.dev0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R3 | 2 | non-breaking | BACKWARD_OK | label_change_or_new_required_without_default | OLD_CONSUMER | add-default |

---
digest: `844a6d291e283aaf126f96221b74a4d2fb2f6a441095a5e029b4a77f09fe8989`（Markdown 是 JSON 的渲染视图，不参与 digest）
