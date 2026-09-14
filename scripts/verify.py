#!/usr/bin/env python3
"""统一验证入口 —— 三个 agent 都跑这一个脚本。

设计原则：
  1. 零外部依赖（只用标准库；pytest 缺失时退回 unittest）
  2. 退出码即结论：0 = 全过，非 0 = 有问题，不许"口头通过"
  3. 输出既给人看，也给 agent 看

用法：
    python scripts/verify.py            # 全部检查
    python scripts/verify.py --quick    # 跳过测试与耗时项
"""

from __future__ import annotations

import compileall
import io
import os
import re
import subprocess
import sys
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
TESTS = os.path.join(ROOT, "tests")

# 仓库里必须存在的文件（缺一个就说明骨架被破坏了）
REQUIRED = [
    "README.md", "CONVENTIONS.md", "AGENTS.md", "CLAUDE.md",
    "TASK.md", "HANDOFF.md",
    "docs/research-design.md",
]
REQUIRED_DIRS = ["src", "tests", "scripts", "docs", "experiments"]

results: list[tuple[str, bool, str]] = []


def report(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    for line in str(detail).strip().splitlines() if detail else []:
        print(f"         {line}")


def note(name: str, detail: str) -> None:
    """非阻断的提示（不算进 PASS/FAIL 统计）。"""
    print(f"  [INFO] {name}")
    for line in str(detail).strip().splitlines() if detail else []:
        print(f"         {line}")


# ------------------------------------------------------------------ 1. 结构
def check_layout() -> bool:
    missing_dirs = [d for d in REQUIRED_DIRS if not os.path.isdir(os.path.join(ROOT, d))]
    missing_files = [f for f in REQUIRED if not os.path.isfile(os.path.join(ROOT, f))]
    detail = ""
    if missing_dirs:
        detail += "缺目录: " + ", ".join(missing_dirs) + "\n"
    if missing_files:
        detail += "缺文件: " + ", ".join(missing_files)
    ok = not missing_dirs and not missing_files
    report("仓库结构完整", ok, detail)
    return ok


# ------------------------------------------------------------------ 2. 语法
def check_syntax() -> bool:
    buf = io.StringIO()
    with redirect_stdout(buf):
        ok = compileall.compile_dir(ROOT, quiet=1, force=True)
    noise = ("site-packages", "node_modules", ".git", "__pycache__", ".venv")
    lines = [l for l in buf.getvalue().splitlines() if not any(n in l for n in noise)]
    report("Python 语法检查", ok, "\n".join(lines[:20]))
    return ok


# ------------------------------------------------------------------ 3. 测试
def check_tests() -> bool:
    if not os.path.isdir(TESTS):
        report("单元测试", False, "tests/ 目录不存在")
        return False
    test_files = [f for f in os.listdir(TESTS)
                  if f.startswith("test_") and f.endswith(".py")]
    if not test_files:
        report("单元测试", False,
               "tests/ 里没有 test_*.py —— 没有测试的改动不算完成")
        return False

    env = dict(os.environ)
    env["PYTHONPATH"] = SRC + os.pathsep + env.get("PYTHONPATH", "")
    try:
        import pytest  # noqa: F401
        cmd = [sys.executable, "-m", "pytest", TESTS, "-q", "--no-header"]
    except ImportError:
        cmd = [sys.executable, "-m", "unittest", "discover", "-s", TESTS, "-v"]

    p = subprocess.run(cmd, cwd=ROOT, env=env,
                       capture_output=True, text=True, errors="replace")
    tail = (p.stdout or "").strip().splitlines()[-10:]
    report(f"单元测试（{len(test_files)} 个文件）", p.returncode == 0,
           "\n".join(tail) or (p.stderr or "")[:400])
    return p.returncode == 0


# ------------------------------------------------------------------ 4. 环境自检
def check_environment() -> bool:
    """复用 selfcheck.env_check。缺 torch/GPU 只是 warn，不阻断。"""
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC + os.pathsep + env.get("PYTHONPATH", "")
    p = subprocess.run([sys.executable, "-m", "selfcheck.env_check"],
                       cwd=ROOT, env=env, capture_output=True, text=True, errors="replace")
    out = (p.stdout or "").strip()
    body = "\n".join(out.splitlines()[3:-2]) if len(out.splitlines()) > 4 else out
    report("环境自检通过", p.returncode == 0, body)
    return p.returncode == 0


# ------------------------------------------------------------------ 5. 卫生
# 注意：这些字符串是拼接出来的，不能写成字面量 ——
# 否则本文件自己就会命中下面的扫描，变成"自己举报自己"。
DEBUG_PATTERNS = (
    "break" + "point(",
    "pdb.set_" + "trace(",
    "DEBUG-" + "LEFTOVER",
)

SECRET_PATTERNS = [
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "OpenAI/DeepSeek 风格 key"),
    (re.compile(r"\bark-[A-Za-z0-9]{20,}"), "火山方舟 token"),
    (re.compile(r"\bAKLT[A-Za-z0-9]{16,}"), "火山 AK"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}"), "GitHub token"),
]


def _scan(pattern_predicate, roots=(SRC, TESTS, os.path.join(ROOT, "scripts"))):
    hits = []
    for root in roots:
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d != "__pycache__"]
            for f in fn:
                if not f.endswith((".py", ".md", ".yaml", ".yml", ".json")):
                    continue
                path = os.path.join(dp, f)
                try:
                    text = open(path, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                for i, line in enumerate(text.splitlines(), 1):
                    if pattern_predicate(line):
                        hits.append(f"{os.path.relpath(path, ROOT)}:{i}")
    return hits


def check_debug_leftovers() -> bool:
    hits = _scan(lambda l: any(p in l for p in DEBUG_PATTERNS))
    report("无遗留调试代码", not hits, "\n".join(hits[:10]))
    return not hits


def check_no_secrets() -> bool:
    """防止密钥被提交进仓库 —— 这个项目会配 API 做评测，必须防。"""
    hits = []
    for pat, label in SECRET_PATTERNS:
        for h in _scan(lambda l, _p=pat: bool(_p.search(l))):
            hits.append(f"{h}  ({label})")
    report("无硬编码密钥", not hits, "\n".join(hits[:10]))
    return not hits


# ------------------------------------------------------------------ main
def main() -> int:
    quick = "--quick" in sys.argv
    print("=" * 66)
    print("  验证开始" + ("（quick 模式）" if quick else ""))
    print("=" * 66)

    check_layout()
    check_syntax()
    if not quick:
        check_tests()
        check_environment()
    else:
        note("已跳过", "单元测试、环境自检")
    check_debug_leftovers()
    check_no_secrets()

    failed = [n for n, ok, _ in results if not ok]
    print("-" * 66)
    if failed:
        print(f"结果：FAIL —— {len(failed)} 项未通过")
        for n in failed:
            print(f"  · {n}")
        print("\n修好后重跑，把输出贴进 HANDOFF.md。")
        return 1
    print(f"结果：OK —— {len(results)} 项全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
