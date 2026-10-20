# HANDOFF-M6 · 发布收尾交接单（收尾棒：项目已发布 v0.1.0）

> 用法（用户侧启动命令，绝对路径只在对话里给）：
> `/goal 读取 "<项目绝对路径>\plan\HANDOFF-M6.md" 继续完成任务`
> **第一动作 = 跑 `py tools/check-sprint-layout.py`**（门红了先修布局，再干活）。
> 上一棒：M5（四态归因 + 端到端 golden + `--verify` 重放定位），已完成并 commit。
> **本棒 = 收尾棒**：M6 已 ✅，v0.1.0 已发布，全里程碑关闭，无"下一棒"。

## 一、当前进度与证据

| 项 | 状态 | 证据（可复跑的命令） |
|---|---|---|
| 干净环境三场景 | ✅ | 仓库外 `git clone --no-local` + 新 venv：Avro r1 exit 1、Proto r5 exit 1、JSON Schema r3 forward exit 1；归因四联 `OLD_CONSUMER/NEW_CONSUMER/BOTH/REPLAY_ONLY` 逐条真跑（发布留档 §一） |
| tag + 源码包 | ✅ | `v0.1.0`（annotated → `0c7d28e`）；`git archive v0.1.0` + `gzip -9n` + `SHA256SUMS`；解包树与 tag 树 **258 文件 sha256 逐字节一致** |
| GitHub Release | ✅ | 公开仓库 `yuluo554/10-20-contract-compat`；Release `v0.1.0` 附 `contract-compat-0.1.0.tar.gz` + `SHA256SUMS` |
| CI 实跑全绿 | ✅ | 三矩阵各 **357 passed**（py3.12/ubuntu + py3.12/py3.8/windows）；终态 run 39455865945（main）/ 39455885096（v0.1.0）；push 数 9 = run 数 9 |
| 发布留档 | ✅ | `plan/RELEASE-M6.md` 两栏 + 阶段 7 覆盖对账表 |
| 发布终态自检门 | ✅ | `py tools/check-sprint-layout.py` 全绿（含已激活的发布留档判据）；两组变异（删覆盖对账节 / 去掉"tag 后追加"栏）均变红、恢复后绿 |
| 状态副本 | ✅ | 四处（plan/00 里程碑表 / plan/05 状态表 / README 状态行 / plan/06 缺口列）M6 全 ✅，缺口列无 M6 字样 |
| 版本一致性 | ✅ | `__version__` / `compat --version` / README / tag = `0.1.0` 四处一致（dev0 已翻转） |
| 测试全量 | ✅ | `py -3.12 -X utf8 -m pytest -q` 与 `py -3.8 -X utf8 -m pytest -q` 均 **357 passed** |
| golden / fixtures | ✅ | `gen_golden.py --check` → 118 份逐字节一致（双跑）；`gen_fixtures.py --check` → 76 文件 |
| 布局门 | ✅ | `py tools/check-sprint-layout.py` 全绿 |

## 二、当前事实 · 状态不变量（后续动手前必须知道）

| # | 事实 | 后果 / 禁区 |
|---|---|---|
| 1 | **tag 之后交付面零提交**：`v0.1.0..main` 为空 | tag 后只允许非交付面提交（文档/计划）；交付面改动 = 发 v0.1.1 重走发布 |
| 2 | M1–M5 的事实/禁区清单（K1–K29、分层约束、序列化单点）**全部继续生效** | 见各 HANDOFF §四与 AGENTS.md；本单不重复 |
| 3 | golden 行尾 = **LF 归一**（`gen_golden.py::_normalize_lf`） | 生成器在 Windows 上重生成也不再产出 CRLF；删掉归一步骤 → Linux 上 118 处漂移（首推实案） |
| 4 | dev extras 含 `pyyaml>=5.4` | 删掉会让 workflow 守门测试在 CI/干净环境 skip（"跳过"与"通过"在日志里长得一样） |
| 5 | git push 走 **SSH** remote（`git@github.com:…`）；HTTPS 对 `github.com` 网页域名间歇重置（`api.github.com` 稳定） | 换回 HTTPS remote 时先 `curl -sI https://github.com` 探活 |
| 6 | 竞品（contract-witness）M6 定稿复核：仍仅 JSON Schema、0★、无新 push | 差异化窗口判断不变；若续作，按 plan/00 缺口表口径每周复核 |
| 7 | 项目无"下一棒"：后续工作 = 维护态（issue 修复、可选扩展项） | 任何新功能 → 新版本号 + 新一轮发布流程（plan/05 §六的发布计划可复用） |

## 三、后续工作（无"下一棒"；维护态清单）

项目已发布收官，无里程碑待办。若需续作，按优先级：

1. **维护**：外部 issue / PR → 修复 → 双解释器全绿 + golden 复算 → 补丁版本（`v0.1.x`）重走
   plan/05 §六发布流程（tag/Release/留档同口径）。
2. **可选扩展**（题面红线④内、plan/00 决策记录允许的）：`--explain-mapping` 增强、更多 fixture 对、
   JSON Schema 新 draft 支持——均为交付面改动，**必须发新版本**，不得原地改 tag。
3. **不建议**：反例见证器（决策记录已弃）、Registry 服务（plan/00 弃选项表）。

## 四、既定口径清单（K 编号；动了会打挂测试的约定）

> M6 新增 K30–K31；K1–K29 未变（K1–K12 见 `plan/HANDOFF-M1.md` §四，K13–K15 见
> `plan/HANDOFF-M2.md` §四，K16–K18 见 `plan/HANDOFF-M3.md` §四，K19–K23 见 `plan/HANDOFF-M4.md` §四，
> K24–K27 与 K28–K29 见 `plan/HANDOFF-M5.md` §四——git 历史可查）。

| K | 口径 | 位置（唯一可编辑副本） | 打挂哪条 |
|---|---|---|---|
| K30 | golden 字节与平台无关：生成器把 CLI stdout 行尾**归一为 LF** 后写盘（canonical 冻结契约"换行一律 \n"的生成端对齐）；golden 全量 LF | `gen_golden.py::_normalize_lf` + `data/golden/`（118 份 LF） | Linux CI `tests/test_golden.py` 两断言（首推实案） |
| K31 | 版本号唯一源 `src/contractcompat/__init__.py:__version__`，发布时必须与 tag 同值（无 `dev` 后缀）；报告头含版本号 → 版本翻转必须同轮重生成 cli-* golden | `__init__.py` + `data/golden/cli-*` | `tests/test_golden.py`、发布前检查清单第 4 条 |

## 五、本机环境坑（全部实测，带日期）

| 坑 | 实测 | 处置 |
|---|---|---|
| `python` 是商店占位符 | 2026-10-20 | 一律 `py` / `py -3.12` / `py -3.8` |
| `py -3.12 -X utf8` 选项顺序 | 2026-10-20 | 版本号在 `-X` **之前** |
| 无 `protoc`；protobuf 两版本字节一致 | 2026-10-20 | 不变（M1 口径） |
| 子进程跑 `py -m contractcompat.cli` 需 `PYTHONPATH=src` | 2026-10-20 | `gen_golden.py` 已自己拼（`_env()`） |
| `py` 启动器下子进程崩溃表现为 `returncode 3221225477` | 2026-10-20 | 先直接复现再怀疑代码（M5 实案） |
| **HTTPS 到 `github.com` 间歇重置（`api.github.com` 稳定通）** | 2026-10-20（M6 实测，持续约 40 分钟） | git remote 用 **SSH**；重试循环 + `curl -sI https://github.com` 探活 |
| **Windows 文本流 CRLF 污染 golden** | 2026-10-20（M6 首推实案，CI 118 处漂移） | 生成端 `_normalize_lf` 已修；新增生成器照抄，不要在比对端"宽容 CRLF" |
| **dev extras 缺 pyyaml → workflow 守门测试 skip** | 2026-10-20（M6 实案，CI 三矩阵 350 passed + 1 skipped） | 已补 `pyyaml>=5.4`；新增"环境已装"类测试必须同步进 extras |
| 布局门变异靶子会被文档改字打崩 | 2026-10-20 | 改完文档先跑 `py tools/verify-layout-gate.py` |
| `plan/06` 缺口列措辞 | 2026-10-20 | 只写关闭条件与结论，不写文件路径、不含已 ✅ 里程碑的 token |

## 六、DoD 逐项 checklist（M6 → 收尾时点）

- [x] 干净环境（仓库外 + 新 venv）按 README 三条场景逐条跑通，退出码符合声明语义
- [x] 归因四联逐条真跑（四种 `--deploy-order` 四个 radius）
- [x] 源码包 `git archive v0.1.0` + `gzip -9n` + `SHA256SUMS`；真下载/解包与 tag 树逐字节比对（258 文件 sha256）
- [x] tag（annotated）+ GitHub Release（公开仓库）+ 附件（tar.gz + SHA256SUMS）
- [x] CI 全绿（三矩阵 357 passed）+ push 数 = run 数对账（9 = 9）
- [x] `plan/RELEASE-M6.md` 两栏 + 阶段 7 覆盖对账表（逐条：实现 / 不适用+理由 / 待首推）
- [x] 发布终态自检门无 FAIL；`LAYOUT.RELEASE` 判据激活 + 两组变异变红/恢复绿
- [x] 版本四处一致（dev0 翻转 + cli golden 同轮重生成）
- [x] tag 后零提交（`v0.1.0..main` 为空）；本单为收尾棒，写自身
- [x] 四处状态副本翻 M6 ✅；缺口列 G1/G2/G6/G7/G8 关闭、无 M6 字样
- [x] 双解释器 pytest 全绿（357 × 2）；布局门全绿

## 七、关键命令速查

```bash
# 方法论门（任何新对话第一件事）
py tools/check-sprint-layout.py
py tools/verify-layout-gate.py        # 门自身的 8 组变异（改过文档必跑）

# 全量测试（双解释器）
py -3.12 -X utf8 -m pytest -q
py -3.8  -X utf8 -m pytest -q

# 复算门
py data/tools/gen_fixtures.py --check      # 76 个 fixture 位级一致
py data/tools/gen_golden.py --check        # 118 份 golden 逐字节一致（LF 归一后跨平台）

# 发布态复核
git ls-remote origin refs/heads/main refs/tags/v0.1.0   # 远端 tag 指向 0c7d28e
gh release view v0.1.0 --repo yuluo554/10-20-contract-compat --json assets --jq '.assets[].name'
gh run list --repo yuluo554/10-20-contract-compat --limit 4   # 终态两 run success
```

## 附：本棒做了但题面没要求的（如实记录）

- **CI 首推两轮红并修复（都进了交付面，因此重打 tag）**：
  1. golden CRLF 跨平台漂移（生成端 `_normalize_lf` 修复 + 118 份重生成）；
  2. dev extras 缺 pyyaml（workflow 守门测试在 CI 全部 skip，补依赖后 357 全跑）。
  两者都是"本地绿 ≠ CI 绿"的实案，已回填发布留档 §二 与本单 §五。
- **版本翻转 `0.1.0.dev0` → `0.1.0`**：报告头含版本号，随翻同轮重生成 cli golden 62 份（K31）。
- **竞品窗口定稿复核**：当周用 `gh api` 逐文件目验 contract-witness 仍单格式（G7 关闭的实测证据）。
- **发布留档判据的变异验证**：判据激活（M6 翻 ✅）后补删覆盖对账节 / 去掉"tag 后追加"栏两组，
  均红、恢复均绿（G8 关闭的实测证据）。
- **远端 tag 三次重打**：0c314bf → 38ddfa5 → 0c7d28e（修复必须进发布）；每次都同步删远端旧 tag。
