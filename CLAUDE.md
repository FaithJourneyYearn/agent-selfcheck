# CLAUDE.md —— 给 Claude Code 的入口

**先读 `CONVENTIONS.md`**（项目约定唯一事实源），再读 `TASK.md`，最后读 `HANDOFF.md` 最后一条。

## 你的定位：长期驻地 + 深度工作

- 你负责这个仓库里**需要跨文件推理、需要长期记忆、需要架构判断**的部分
- 你的优势是能跑 Bash、能读能写、能接 MCP —— **必须用起来做实际验证**

## 强制验证协议（不许跳过）

1. 跑 `python scripts/verify.py`，贴出原始输出
2. **可视产物**（图表/页面）：无头浏览器渲染截图，贴 PNG 绝对路径。
   本机命令：

   "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless=new --disable-gpu --no-sandbox --hide-scrollbars --force-device-scale-factor=1 --window-size=1280,900 --virtual-time-budget=2500 --screenshot="<绝对路径>.png" "file:///<绝对路径>"

   然后用 Read 工具读那张 PNG，**真的看一眼**再下结论。
3. **实验数据**：任何"提升了 X%"的说法，必须说明
   - 对比的是什么基线
   - 跑了几次、随机种子是什么
   - 是单次结果还是多次均值
   只给单次结果就下结论的，视为未完成。
4. 自查 ≥ 2 轮：首轮问题改完后必须重新验证一次。

## 交接

完成后在 `HANDOFF.md` 追加一条（含 `git rev-parse HEAD`）。
不要在同一分支上和另一个 agent 并行改同一文件。

## 不确定的事

写"我不确定"。编造 API、编造实验数字、假称已测过，是这里最严重的错误。
