# agent-selfcheck

> 代码 Agent 的自检行为，能否被**可验证奖励**诱导出来？

一个用于本科毕设 / 考研复试的研究项目仓库。核心问题是：
给模型一个只看结果的奖励（单元测试通过），它会不会自己学会"先验一遍再交"？

完整研究设计（假设、变量、指标、消融、反悔条件）见 **[`docs/research-design.md`](docs/research-design.md)**。

**当前状态：骨架阶段**（环境自检 + 验证链路已跑通，实验代码尚未实现）

---

## 快速上手

```bash
# 建环境（Python 3.13）
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt

# 1. 环境自检（缺 GPU / 缺训练框架只会提示，不会报错）
python -m selfcheck.env_check

# 2. 跑完整验证（结构 / 语法 / 测试 / 环境 / 密钥卫生）
python scripts\verify.py
```

`verify.py` 的退出码就是结论：`0` = 全过。**不允许口头说"已经测过了"。**

---

## 三个 agent 怎么协作

这个仓库被设计成**同时**给 WorkBuddy / Codex / Claude Code 用。三条规则：

1. **规范只有一份**：`CONVENTIONS.md`。`AGENTS.md`、`CLAUDE.md`、`.workbuddy/memory/MEMORY.md`
   都只是指针，故意不复制内容 —— 三份副本必然各自演化成互相矛盾的三套规则。
2. **共享的是 diff，不是文件**：同一个 git 仓库，各开 `feat/<任务>-<agent>` 分支，
   靠 `HANDOFF.md` 交接（含 commit hash + 原始验证输出）。
3. **写完必须过 `verify.py`**，并把原始输出贴进 `HANDOFF.md`。

| 文件 | 谁读 | 作用 |
|---|---|---|
| `CONVENTIONS.md` | 全部 | 规则唯一来源，改规则只改这里 |
| `AGENTS.md` | Codex | 入口 + 脏活边界 |
| `CLAUDE.md` | Claude Code | 入口 + 强制验证协议 |
| `.workbuddy/memory/MEMORY.md` | WorkBuddy | 入口 + 本研究红线 |
| `TASK.md` | 全部 | 当前任务：目标 / 验收标准 / 边界 |
| `HANDOFF.md` | 全部 | 交接日志，只追加 |
| `experiments/*.yaml` | 全部 | 实验记录，**只追加不改** |

标准流程：

```
改 TASK.md 派活 → git checkout -b feat/xxx-<agent> → 干活 + 写测试
→ 跑 verify.py → 写 HANDOFF.md → 换另一个 agent 复审 → 合入 main
```

最后一步「换另一个 agent 复审」是最值钱的 —— 同一个模型审自己会倾向确认自己没错。

---

## 目录结构

```
agent-selfcheck/
├── CONVENTIONS.md          规则唯一事实源（先读这个）
├── AGENTS.md / CLAUDE.md   各 agent 的入口
├── TASK.md                 当前任务单
├── HANDOFF.md              交接日志
├── docs/
│   ├── research-design.md  ★ 研究设计（最重要的一份文档）
│   └── decisions/          重大取舍的决策记录
├── experiments/
│   ├── TEMPLATE.yaml       实验记录模板
│   └── *.yaml              ★ 实际实验记录（只追加）
├── scripts/verify.py       统一验证入口
├── src/selfcheck/
│   ├── env_check.py        环境自检（已实现）
│   └── ...                 tasks/datasets/reward/detect/train/eval（待实现）
└── tests/                  测试
```

---

## 三条不能破的红线

这三条是这类实验最常见的死法，写在这里是为了不用翻文档也能看见：

1. **数据泄漏** —— 训练集里出现评测题，pass@1 的提升就可能是记忆而非能力。
   必须做重叠检查并落盘留痕。
2. **"自检"的定义前置** —— `docs/research-design.md` 第 6 节的定义一经记录不得放宽。
   看到结果再改定义 = 事后拟合，等于没有结论。
3. **报结论带口径** —— 任何"提升了 X%"必须附：对比基线 + 重复次数 + 随机种子 + 标准差。
   单次结果不作为结论。

---

## 反悔条件（提前写好，防止自己骗自己）

- 控制生成长度后组间 SR 差异消失 → H1 不成立
- 去掉疑似泄漏样本后结论反转 → 结论无效，重做
- 判定器与人工一致率 kappa < 0.7 → 判定器重做，此前结论作废
- 组 D 的 pass@1 不涨但 SR 猛涨 → 奖励被 hack，重新设计奖励

详见 `docs/research-design.md` 第 7 节。
