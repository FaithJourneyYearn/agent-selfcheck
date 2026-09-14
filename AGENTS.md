# AGENTS.md —— 给 Codex 的入口

**先读 `CONVENTIONS.md`**（项目约定唯一事实源），再读 `TASK.md`，最后读 `HANDOFF.md` 最后一条。

## 你的定位：脏活工人 + 独立复审

- 你负责**批处理、脚本、数据清洗、重构、按既定模式批量改写**
- 你不负责设计实验方案（那归 `docs/research-design.md`，改动要单独提 TASK）
- 你**不该**在没读 `CONVENTIONS.md` 的情况下动 `src/selfcheck/` 的核心逻辑

## 强制验证协议

1. 改完必须跑 `python scripts/verify.py`，把**原始输出**贴进 HANDOFF.md
2. 不许说"已测试通过"而不给输出
3. 新增功能必须同步新增 `tests/` 用例
4. 任何涉及随机性/采样的代码，必须能固定种子复现

## 禁止事项

- 不要为了让测试通过而删改既有测试用例
- 不要引入 `requirements.txt` 里没有声明的依赖
- 不要动 `experiments/` 下已归档的实验记录（只追加）
- 不确定就写"我不确定"，不要编造 API 或结果
