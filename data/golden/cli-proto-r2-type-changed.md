# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **breaking**
- 输入: old=`r2-type-changed-old.pb` ｜ new=`r2-type-changed-new.pb`
- tool: contractcompat 0.1.0.dev0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R2 | 2 | breaking | NONE_OK | wire_incompatible_type_change | OLD_CONSUMER | bump-and-version |

---
digest: `ff42215d7aead082cf0abbb8296f5070b9739018f1a7412583d2a323e6b1e54e`（Markdown 是 JSON 的渲染视图，不参与 digest）
