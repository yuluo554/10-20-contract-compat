# AGENTS.md

本仓库遵循 **`ai-tool-project-sprint`** 方法论（装订日期：2026-10-20）。

## 任何新对话的第一件事

```bash
py tools/check-sprint-layout.py     # 布局门；必须绿，红了先修布局再干活
```

- 续接对话：读 `plan/HANDOFF-M<k>.md`（第 k 棒收尾交接单），**先跑上面这条门**。
- 接手对话（无 HANDOFF）：先读 `plan/00`、`plan/05`、`plan/06` 与各 HANDOFF，
  重建"当前状态 + K 口径清单"再动手。
- **门不存在 = 本项目没装订** → 先补第零步三件（本文件 + 布局门 + `plan/00` 顶部一行），再做别的。
- CI 里同一条门用 `python tools/check-sprint-layout.py`（workflow 的 runner 上 `python` 可用）。

## 强制布局（布局门逐条断言，改动前先看这里）

| 项 | 位置 | 判据 |
| --- | --- | --- |
| 计划套件 | `plan/00`–`plan/06` + `data/README.md` | 存在且各含必需小节 |
| 数据口径 | `data/README.md` §四 | 七档/七类规则/三值/退出码/归因的**唯一定义处**（其它文档只引用，不复述） |
| 交接单 | `plan/HANDOFF-M<k>.md` | 每个 ✅ 里程碑一份（M<k> 收尾写 M<k+1>；收尾棒写自身），**七节**齐 |
| 里程碑状态副本 | `plan/00` 里程碑表 + `plan/05` 状态表 + `README.md` 状态行 | **逐处一致**（枚举式断言，真值不取自任何单一副本） |
| 发布留档 | `plan/RELEASE-M6.md`（两栏）或 `plan/WRAPUP-M6.md` | 最后一个里程碑 ✅ 后才要求；两栏 + 覆盖对账小节 |
| 文档点名的工具 | `tools/*.py` 等 | 文档里出现的路径**必须有实物**（`LAYOUT.DOC_TOOLS`） |

## 分层硬约束（测试守门，改目录结构前先看）

- `src/contractcompat/parsers/*` **不得** import `policy` / `rules` / `blast`（解析层不判定）。
- `policy.py` / `rules.py` **不得** import `report`（判定层不渲染）。
- 全仓 `json.dumps(` **只允许**出现在 `canonical.py`（序列化单点）。

## 环境事实与禁忌

- 本机（2026-10-20 实测）：`py -3.8` = 3.8.8、`py -3.12` = 3.12.10；`python` 是商店占位符，**用 `py`**。
  跑脚本一律 `py -X utf8`（中文控制台）。`node v24.15.0`、`gh 2.93.0`（已登录 yuluo554）。
  本机**无 `protoc`**（这条不变，`protoc` 只在验 exit 3 时需要）；**`protobuf` 已装**：
  `py -3.12` → 7.36.2、`py -3.8` → 5.29.6（M1 装，两档产出的描述符字节逐字节相同）。
  生成器/校验用：`py data/tools/gen_fixtures.py --check`、`py data/tools/gen_golden.py --check`。
- 禁用：把"未执行"写成已完成；tag 之后改交付面代码；在测试里写死"当前仓库有 tag"这类检出形态判据。
- 未接远端期间，CI 类 DoD 一律写"本地等价校验（未接远端，CI 待首推验证）"，**不得写"CI 绿"**。
