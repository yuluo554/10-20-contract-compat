# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r2-type-changed-old.pb` ｜ new=`r2-type-changed-new.pb`
- tool: contractcompat 0.1.1

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R2 | 2 | breaking | NONE_OK | wire_incompatible_type_change | OLD_CONSUMER | bump-and-version |

---
digest: `d15e9f923bbe66700da44499de2aace8bd6504bc94574ae94779fce9b260ad2c`（Markdown 是 JSON 的渲染视图，不参与 digest）
