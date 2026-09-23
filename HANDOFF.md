# HANDOFF.md —— 交接日志

> **只追加，不修改历史条目。** 复审的人从最后一条往前读。

---

## 模板（复制这一段用）

```
### YYYY-MM-DD HH:MM · <agent 名> · <任务名>

- **commit**：`<git rev-parse HEAD 的输出>`
- **分支**：feat/xxx-<agent>
- **改了什么**（文件 + 一句话）：
  - `src/selfcheck/xxx.py` —— 修了 xxx
- **验证结果**：贴原始命令输出，不是"已通过"
  ```
  $ python scripts/verify.py
  ...
  OK
  ```
- **没做完 / 不确定的**：
- **给下一个人的提醒**：
```

---

## 日志

<!-- 从这里往下追加，最新的在最下面 -->

### 2026-09-14 21:55 · workbuddy · T-001 搭建仓库骨架

- **commit**：`e8b8ff7`
- **分支**：`main`（仓库刚初始化，首个提交）
- **改了什么**：
  - 建立目录骨架 `src/selfcheck/`、`tests/`、`scripts/`、`docs/`、`experiments/`
  - `CONVENTIONS.md` —— 填好第 1、2 节（项目定义、技术栈），并加了第 6 节「研究专属红线」
  - `docs/research-design.md` —— 研究设计：H1/H2/H3 假设、变量与指标、消融五组、
    自检的操作化定义、**反悔条件表**、最小可行版本
  - `scripts/verify.py` —— 统一验证入口：结构 / 语法 / 测试 / 环境自检 / 调试残留 / 硬编码密钥
  - `src/selfcheck/env_check.py` —— 环境自检，零硬依赖，缺 GPU 与训练框架只 warn 不 fail
  - `tests/test_env_check.py` —— 12 个用例
  - `TASK.md` —— 排出 T-002…T-010 队列
- **验证结果**：
  ```
  $ python scripts/verify.py
  ==================================================================
    验证开始
  ==================================================================
    [PASS] 仓库结构完整
    [PASS] Python 语法检查
    [PASS] 单元测试（1 个文件）
           12 passed in 0.04s
    [PASS] 环境自检通过
    [PASS] 无遗留调试代码
    [PASS] 无硬编码密钥
  ------------------------------------------------------------------
  结果：OK —— 6 项全部通过
  EXIT=0
  ```
- **踩过的坑（给后面的人省时间）**：
  `verify.py` 的调试代码扫描一开始**自己举报自己** —— 因为 `DEBUG_PATTERNS` 里写的是
  字面量 `"breakpoint()"`，而这一行本身就在被扫描的文件里，于是永远命中。
  改成运行时拼接（`"break" + "point("`）才修好。
  **教训：写静态检查工具时，要拿它检查它自己。**
- **没做完 / 不确定的**：
  - `src/selfcheck/` 下 `tasks/datasets/reward/detect/train/eval` 六个模块**尚未实现**
    （`__init__.py` 里已列出规划，见 TASK.md 队列）
  - 磁盘可用仅 15.7 GB，真开始训练前需要清理或换盘
- **给下一个人的提醒**：
  下一步是 **T-002（tasks + datasets + 泄漏检查）**，见 `TASK.md`。
  这是全项目风险最高的一块：泄漏检查做错，后面所有实验数字都是废的，宁可比需要的更严。

---

### 2026-09-23 23:20 · workbuddy · PR #2 复审整改（T-002 前置修补）

- **commit**：`8bdbebe`（本分支最后一次提交；见下方提醒第 1 条）
- **分支**：`feat/verify-env-probe-workbuddy`（接 `e43f35a`，同一个 PR #2）
- **改了什么**：
  - `src/selfcheck/env_check.py` —— `check_env_identity()` 三条分支全部改成
    同时打印「当前解释器」和「项目环境解释器」两条路径（带各自标签）；
    两者相同时也不再只报一条
  - `src/selfcheck/env_check.py` —— **`format_report()` 现在会渲染 `extra`**（原为完全忽略）
  - `tests/test_env_check.py` —— 新增 4 个测试（21 passed，原 17）

**为什么会有这一轮**：PR #2 的 Copilot 代码审查给了 🟡 Changes recommended，
其中一条（Medium）指出「两条解释器路径没有都输出」——**这条成立**，
而且根因比它说的更深，见下。

- **验证结果**（原始输出，用带 pytest 的解释器跑的）：

  ```
  $ python scripts/verify.py
  ==================================================================
    验证开始
  ==================================================================
    [PASS] 仓库结构完整
    [PASS] Python 语法检查
    [PASS] 单元测试（1 个文件）
           .....................                                                    [100%]
           21 passed in 0.07s
    [PASS] 环境自检通过
           [WARN] 解释器来源
                    当前解释器: C:\Users\LENOVO\......
                    项目环境: 未找到 .venv —— 上面的依赖 / GPU 检查反映的是「当前解释器」，而非项目环境；建好 .venv 后请用它重跑
                    · current_python: C:\Users\LENOVO\......
                    · venv_python: None
                    · venv_exists: False
                    · is_venv_python: False
             [PASS] Python 版本
                    Python 3.13.14 @ C:\Users\LENOVO\......
                    · venv: True
                    · version: [3, 13, 14]
             [PASS] 依赖清单
                    核心依赖: 齐全
                    训练依赖: 缺 torch, transformers, trl, datasets（实验期才需要）
                    评测依赖: 缺 scipy, vllm（实验期才需要）
                    · missing_core: []
                    · missing_train: ['torch', 'transformers', 'trl', 'datasets']
                    · missing_eval: ['scipy', 'vllm']
             [WARN] GPU
                    未安装 torch，跳过（实验期再查）
                    · cuda: None
             [PASS] 磁盘空间
                    可用 125.2 GB
                    · free_gb: 125.2
    [PASS] 无遗留调试代码
    [PASS] 无硬编码密钥
  ------------------------------------------------------------------
  结果：OK —— 6 项全部通过
  EXIT=0
  ```

  三态分支的人工复核（打桩 `find_project_venv`，确认报告文本本身，不只是断言）：

  ```
  --- 情形 A：两者相同（原 bug 所在分支）---
    [PASS] 解释器来源
           当前解释器: C:\...\default\Scripts\python.exe
           项目环境解释器: C:\...\default\Scripts\python.exe
           两者是同一个解释器，结论代表项目环境

  --- 情形 B：venv 存在但用的不是它 ---
    [WARN] 解释器来源
           当前解释器: C:\...\default\Scripts\python.exe
           项目环境解释器: C:/fake/.venv/Scripts/python.exe
           两者不同：本次结论不代表项目环境，请改用: .venv\Scripts\python.exe scripts\verify.py

  --- 情形 C：未找到 .venv ---
    [WARN] 解释器来源
           当前解释器: C:\...\default\Scripts\python.exe
           项目环境: 未找到 .venv —— ……
  ```

- **踩过的坑（重要，给后面的人省时间）**：
  **`format_report()` 从来不渲染 `extra`，这是从 T-001 就埋下的假绿。**

  它原来只有 `for part in r.detail.split(" | ")` —— 一个字都没读 `extra`。
  后果不是"少印一行"，而是**凡是写进 `extra` 的信息在报告里彻底不存在**：
  依赖缺失清单、磁盘余量、`is_venv_python` 全部被吞掉。

  最阴的地方在于：单元测试是直接读 `r.extra["missing_core"]` 这种**属性**的，
  所以照样全绿；`verify.py` 也照样通过。于是
  **「验证通过」和「人什么都看不见」可以同时成立。**

  ⇒ 两条纪律，写进习惯里：
  1. 断言数据结构的测试**证明不了报告可读**。凡是有 `format_report` 这类渲染层，
     就必须有一条测试是**断言渲染出来的文本**里含关键内容（本次新增的两条就是干这个的）。
  2. 加新检查项时，要么写进 `detail`、要么写进 `extra` 并确认渲染层会显示它 ——
     别塞进一个没人读的地方还以为是"结构化输出"。

  附带一个环境坑：本机跑 `verify.py` 的解释器必须装 `pytest`，否则
  `check_tests` 会以 `ModuleNotFoundError` 报错。
  稳妥做法是**先按 CONVENTIONS.md 第 2 节建好项目 `.venv`**，
  再用 `.venv` 里的解释器跑 —— 顺带也让本报告各项检查的结论真正代表项目环境。
  （临时办法：任选一个装了 pytest 的解释器，本次整改是在一个 WorkBuddy 托管的
  隔离 venv 里跑的，不在仓库内。）

- **关于 Copilot 那条 High（记录一下，避免下次重复排查）**：
  它标为 critical/high 的第一条是
  `scripts/verify.py::check_tests()` 的 `subprocess.run()` 异常在 `report()` 前逃逸、
  `main()` 仍可能返回 0。**这条在 PR #2 的范围内不成立** ——
  本次 diff 只有 `src/selfcheck/env_check.py` 和 `tests/test_env_check.py` 两个文件，
  根本没有 `scripts/verify.py`。它是在照抄 Issue #1 的描述，
  而那条恰好是 PR 描述里明确写了的「本次不做」（T-002 边界禁止改 `verify.py` 检查项）。
  它自己写的 overview 三条改动里也没有一条提到 verify.py。
  ⇒ **看 AI 审查意见的第一件事：核它引用的文件和行号在不在这个 diff 里。**
  （该问题本身是真实的，仍挂在 Issue #1 里，属于后续任务。）

- **没做完 / 不确定的**：
  - Issue #1 的第三条（`check_tests` 异常路径绕过 `report()`、退出码不可靠）
    **仍然没修**，因为改它会碰到 `scripts/verify.py`，那是 T-002 明令禁止的边界。
    需要单独开一个任务（建议 T-011）并放宽该边界。
  - 仓库仍**没有项目 `.venv`**，所以本机 `verify.py` 给出的依赖/GPU 结论
    始终只代表"当前解释器"。这正是 `check_env_identity` 存在的意义，
    但真实项目环境仍未建立。
  - 本机磁盘可用 125.2 GB（比 T-001 时的 15.7 GB 宽裕很多，训练前不再是瓶颈）。

- **给下一个人的提醒**：
  1. **commit hash 有自指问题**：往 `HANDOFF.md` 里填自己的 hash 会改变内容、
     进而改变 hash，追不上。上面那个 hash 是**本分支最后一次提交**，
     复审时用 `git log --oneline -1` 核对即可，不必强求它等于本条记录所在的提交。
     （这条本身也是踩坑记录：下次别在同一个提交里写自己。）
  2. **下一步仍是 T-002**，见 `TASK.md`。
  3. 别忘了先给 `scripts/verify.py` 的异常路径（Issue #1 第三条）单开一个任务，
     不要顺手改它 —— 那是 T-002 的边界。
  4. 建项目 `.venv` 这件事一直没做，建议在开 T-002 之前先做掉：
     它会同时解决"报告不代表项目环境"和"本机没 pytest"两个问题。

