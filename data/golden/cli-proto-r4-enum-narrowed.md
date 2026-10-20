# 跨格式契约兼容性判定

- policy: `backward` ｜ verdict: **compatible**
- 输入: old=`r4-enum-narrowed-old.pb` ｜ new=`r4-enum-narrowed-new.pb`
- tool: contractcompat 0.1.0

## 判定表（1 条）

| rule_id | stable_path | severity | direction | evidence | blast_radius | repair |
|---|---|---|---|---|---|---|
| R4 | 2 | non-breaking | BACKWARD_OK | enum_value_removed_or_renamed | OLD_CONSUMER | bump-and-version |

---
digest: `240535122680759a875a1bbaf477a12472bbab343c644acb8d323c875c237c3e`（Markdown 是 JSON 的渲染视图，不参与 digest）
