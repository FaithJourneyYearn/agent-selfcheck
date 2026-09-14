# MEMORY.md —— 本课题的长期事实

> 这个文件是给 WorkBuddy 读的项目记忆。**规则类内容不写这里，写 `CONVENTIONS.md`。**

## 研究主题
用可验证奖励（单元测试通过率）做强化学习，检验代码 Agent 的**自检行为**能否被"奖励出来"，
并与 SFT 监督基线对比。详见 `docs/research-design.md`。

## 必须记住的红线
- **数据泄漏是这类实验的头号死因**：训练集与评测集必须验证不重叠，且要留检查记录。
- **"自检"的定义必须提前写死**（见研究设计第 6 节），禁止事后放宽定义去凑结论。
- 报结论必须带**基线 + 样本量 + 标准差**，禁止用单次结果下断言。

## 常用命令
- 统一验证：`python scripts/verify.py`
- 环境自检：`python -m selfcheck.env_check`

## 本机环境坑（详细版见 CLAUDE.md）
- bash 基础命令残缺，用绝对路径调用可执行文件
- 无 GPU 环境下 `env_check` 会报 warning 而不是 error —— 这是设计如此，别当成 bug 修
