# RELEASE-M6 · v0.1.0 发布留档

> 两栏纪律：§一 冻结 **tag 时点**的事实；§二 只记 **tag 之后追加**的事实。
> 覆盖对账小节（§三）逐条交代阶段 7 检查清单：实现 / 不适用+理由 / 待首推。

## 一、tag 前事实

| 项 | 事实 |
|---|---|
| tag | `v0.1.0`（annotated）→ commit `0c7d28e`（main HEAD，tag 后零提交） |
| 交付面 | `src/contractcompat/{ir,policy,rules,blast,report,canonical,errors,cli}.py` + 三解析器 + `rules/rule-table.json`；M0–M6 全部里程碑 |
| 版本四处一致 | `__version__ = "0.1.0"` / `compat --version` → `compat 0.1.0` / README `0.1.0` / tag `v0.1.0` |
| 测试 | 本地双解释器各 **357 passed**（py3.8.8 / py3.12.10）；golden `--check` 118 份逐字节一致（双跑）；fixtures `--check` 76 文件；布局门全绿 |
| golden | 28 IR + 28 policy + 62 端到端 `cli-*`（含四态四联另 3 档），LF 行尾归一（跨平台逐字节一致） |
| 源码包 | `git archive v0.1.0` + `gzip -9n` → `contract-compat-0.1.0.tar.gz`（sha256 `af48996f…363066d`）+ `SHA256SUMS`；解包树与 `git archive` 树 **258 文件逐字节一致**（sha256 逐文件对账） |
| 干净环境 | 仓库外 `git clone --no-local` + 新 venv：README 三场景退出码 0/1/1 符合声明；归因四联 `OLD_CONSUMER / NEW_CONSUMER / BOTH / REPLAY_ONLY` 各真跑一次 |
| 干净解包树 | tarball 解包 + editable 安装：357 passed + golden 118 份全绿 + `compat --version` 正确 |
| 提交身份 | `yuluo554 <282769740+yuluo554@users.noreply.github.com>`（noreply） |
| 远端 | `git@github.com:yuluo554/10-20-contract-compat.git`（HTTPS 对 github.com 间歇不通，SSH 通，见 §二） |

## 二、tag 后追加

| 时间（2026-10-20） | 事实 |
|---|---|
| 首推 | `main` + `v0.1.0` 推上 GitHub 公开仓库；CI 首跑 **failure**：Linux 上 golden 118 处漂移（Windows 文本流 CRLF 入库，Linux 重生成 LF） |
| 修复 1 | `gen_golden.py` 生成端归一 LF（`_normalize_lf`，canonical 冻结契约"换行一律 \n"的对齐）→ golden 118 份重生成；commit `0c314bf` |
| 修复 2 | dev extras 补 `pyyaml>=5.4`：`tests/test_workflow.py` 在 CI/干净环境真跑（此前 1 skipped，YAML 守门落空）→ **357 passed × 3 矩阵**；commit `38ddfa5` |
| 版本翻转 | `0.1.0.dev0` → `0.1.0`（tag 一致性）+ golden 62 份随版本号重生成；commits `284a71c`、`0c7d28e` |
| 重打 tag | 修复提交必须进发布：远端旧 tag 删除重打，`v0.1.0` 最终指向 `0c7d28e` |
| CI 终态 | `main` run `39455865945` ✅、`v0.1.0` run `39455885096` ✅（py3.12/ubuntu + py3.12+py3.8/windows 全绿）；push 数与 run 数对账：9 push = 9 runs |
| Release | `gh release create v0.1.0` → https://github.com/yuluo554/10-20-contract-compat/releases/tag/v0.1.0 ，附件 `contract-compat-0.1.0.tar.gz` + `SHA256SUMS`（最终 tag 重建后 `--clobber` 上传） |
| 网络备注 | 本机 HTTPS 到 `github.com` 网页域名间歇重置（`api.github.com` 稳定）；git push 改走 SSH（22 端口直连 GitHub 验证通过）后稳定 |

## 三、阶段 7 覆盖对账表

| 检查项 | 结论 | 证据 |
|---|---|---|
| README 三场景在仓库外干净环境逐条跑通、退出码符合声明语义 | 实现 | §一"干净环境"行；Avro r1 exit 1、Proto r5 exit 1、JSON Schema r3 forward exit 1、四联四 radius |
| README 命令可被 parser 反射解析 | 实现 | `tests/test_readme_gate.py` = 4 条固定断言 + README 中 `compat` 命令数（现 8 条）= **12 项（动态值**，随 README 命令数漂移，不要写死） |
| README 提到的产物名真在 Release 里 | 实现 | Release assets：tar.gz + SHA256SUMS；golden 复算命令在包内可跑 |
| 版本四处一致 | 实现 | §一"版本四处一致"行（dev0 翻转后重验） |
| 报告无绝对路径/时间戳/主机名 | 实现 | `tests/test_golden.py` 无绝对路径断言扩到 `cli-*`；golden 复算跨机逐字节一致本身即证明 |
| 脱敏（无本机用户名、noreply 身份） | 实现 | 提交身份 noreply；golden/报告扫描无本机路径 |
| tag 后只含非交付面提交；交付面零差异 | 实现 | `git log v0.1.0..main` 为空；tag 即 HEAD |
| 发布留档两栏 + 阶段 7 覆盖对账表 | 实现 | 本文件 |
| 布局门在收尾棒跑绿（含 LAYOUT.RELEASE 变异验证） | 实现 | `py tools/check-sprint-layout.py` 全绿；`LAYOUT.RELEASE` 两组变异见下 |
| CI 实跑 | 实现（曾「待首推」） | 首推后实跑：修复两轮，终态 run `39455865945`（`main`）/ `39455885096`（`v0.1.0`）3 矩阵全绿（§二） |
| 干净 clone 按 README 跑通 | 实现（曾缺口） | §一"干净环境"行 |

### LAYOUT.RELEASE 变异验证（判据证伪）

| 变异 | 预期 | 实测 |
|---|---|---|
| 删除覆盖对账小节标题 | FAIL（覆盖对账小节:False） | 实测 FAIL，恢复后绿 |
| 删除"二、tag 后追加"栏标题 | FAIL（两栏:False） | 实测 FAIL，恢复后绿 |

---

# v0.1.1 发布留档（2026-10-23）

> 沿同一两栏纪律：§四 冻结 **tag 时点**事实；§五 只记 **tag 之后**追加的事实。
> v0.1.0 的三条发布面缺陷（Release draft / tarball 首屏 M5 版 / RELEASE-M6 不在 tag 树里）
> 按 DEC-2 甲案处理：**远端 `v0.1.0` 删除后重打**，让"已发布的 tag"与 main 自洽。

## 四、v0.1.1 tag 前事实

| 项 | 事实 |
|---|---|
| 版本 | `0.1.1`（单一来源 `src/contractcompat/__init__.py:7`）；`pyproject.toml` 走 `dynamic` |
| 交付面变更 | D1 缺件态退出码判据（`parsers/__init__.py`）+ 全量参数化测试；文档诚实化 4 处；CI actions v7；布局门新增 `LAYOUT.CI_CLAIM` |
| 测试 | 干净 py3.12 = **421 passed**、干净 py3.8.8 = **421 passed**（基线 357，净增 64）；CI 三腿各 421 passed（run `39900355574`） |
| golden | 118 份；版本翻转后重生成 **62 份 `cli-*`**（含 `tool: contractcompat 0.1.1`）；`ir-*.json` / `policy-*.json` **零变动**；`--check` 全绿 |
| fixture | 76 文件位级冻结，**零改动**；`--check` 全绿 |
| 布局门 | `check-sprint-layout.py` 全绿；`verify-layout-gate.py` **9 组变异全红、还原后全绿**（新增 M9 = 删 run 号 → `LAYOUT.CI_CLAIM` 必红） |
| CI | run `39900355574` @ `ab6807b` 三腿全 success；Node20 弃用注解 **0 条**（原 6 条） |
| Release 形态 | **非 draft**（DEC-2 修正项，v0.1.0 曾误发为 draft） |

## 五、v0.1.1 tag 后追加

| 时间（2026-10-23） | 事实 |
|---|---|
| v0.1.0 处置 | 远端 `v0.1.0` 删除并重打到 `ab6807b`（DEC-2 甲案，用户点头）；旧附件 `af48996f…` 已不对应新 tag 树，按 `--clobber` 重建重传 |
| 源码包 | 构建方式不变：`git archive v0.1.1 --prefix=contract-compat-0.1.1/` + `gzip -9n`，sha256 见 Release 说明与 `SHA256SUMS` |
| 可复现性 | 沿用 v0.1.0 已验证的手法（`git archive` + `gzip -9n`，不用 `tar`/`zip`）；重建 sha256 必须与附件一致 |
