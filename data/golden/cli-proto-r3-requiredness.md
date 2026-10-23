# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`r3-requiredness-old.pb` ｜ new=`r3-requiredness-new.pb`
- tool: contractcompat 0.1.1

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R3 | 2 | non-breaking | BACKWARD_OK | label_change_or_new_required_without_default | OLD_CONSUMER | add-default |

---
digest: `cefdfa052564095c575129c688601fdc994fd7b3f230836aa9fcc16ec72ad6cb`（Markdown 是 JSON 的渲染视图，不参与 digest）
