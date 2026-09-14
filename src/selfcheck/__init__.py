"""selfcheck —— 代码 Agent 自检行为研究的实验代码。

模块划分（随开发逐步填充，不要一次写满）：

    env_check   环境与依赖自检，供 verify.py 调用
    tasks       代码任务的数据结构（题目 / 单测 / 元信息）
    datasets    训练集与评测集的加载、去重、泄漏检查
    reward      奖励函数（可验证奖励 / 格式奖励 / 消融变体）
    detect      从轨迹中判定"是否发生自检"（定义见 docs/research-design.md 第 6 节）
    train       SFT / GRPO 训练入口
    eval        评测：pass@1、自检率 SR、平均尝试次数
"""

__version__ = "0.0.1"
