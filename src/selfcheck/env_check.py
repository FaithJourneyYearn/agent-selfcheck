"""环境与依赖自检 —— 供 `scripts/verify.py` 和人工排查使用。

设计原则：
  1. **零硬依赖**：没装 torch / trl 也要能跑，只是报 warn 而不是崩。
  2. **warning 不等于 error**：骨架阶段没有 GPU、没有训练框架是正常的，
     不该让验证失败。只有"根本跑不下去"的问题才算 fail。
  3. 输出既可读（给人看），也可结构化（给脚本判断）。
  4. **说清楚在检查哪个环境**：所有检查用的都是当前解释器（`sys.executable`）。
     若 `verify.py` 不是用项目 `.venv` 跑的，结论就不代表项目环境 ——
     见 `check_env_identity`，它负责把这个前提摊开讲，而不是假装没这回事。

直接运行：
    python -m selfcheck.env_check
"""

from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import sys
from dataclasses import dataclass, field

OK = "ok"
WARN = "warn"
FAIL = "fail"

# 项目目标 Python 版本（低于此版本视为问题）
MIN_PY = (3, 10)

# 依赖分三层：core 必须有，train/eval 推迟到实验期
CORE_DEPS = ["pytest"]
TRAIN_DEPS = ["torch", "transformers", "trl", "datasets"]
EVAL_DEPS = ["numpy", "scipy", "vllm"]


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status != FAIL


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


# 项目根目录：本文件位于 <root>/src/selfcheck/env_check.py
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# 项目虚拟环境里解释器的相对路径（建环境的方式见 CONVENTIONS.md 第 2 节）
VENV_PY_RELPATH = ("Scripts", "python.exe") if os.name == "nt" else ("bin", "python")


def find_project_venv() -> str | None:
    """返回项目 `.venv` 里解释器的绝对路径；不存在则返回 None。

    抽成独立函数是为了让测试能打桩 —— 环境探测不该依赖本机碰巧有没有 .venv。
    """
    p = os.path.join(PROJECT_ROOT, ".venv", *VENV_PY_RELPATH)
    return p if os.path.isfile(p) else None


def check_env_identity() -> CheckResult:
    """说清楚"到底在检查哪个环境"。

    存在的意义：`verify.py` 的其余检查用的都是 `sys.executable`，
    也就是**当前正在跑 verify 的那个解释器**。如果项目 `.venv` 还没建、
    人拿系统 Python 跑了 verify，那么"Python 版本 PASS"这一条检查的其实是它自己，
    而不是项目环境 —— 这是一个看起来很绿的假结论。

    本检查不阻断（骨架阶段没有 .venv 是正常的），但**必须把人引到正确命令上**，
    否则 CI 绿了不代表本机绿。
    """
    cur = sys.executable
    venv = find_project_venv()
    extra = {"current_python": cur, "venv_python": venv,
             "venv_exists": venv is not None, "is_venv_python": venv is not None and
             os.path.normcase(os.path.abspath(cur)) == os.path.normcase(venv)}

    # 两条路径都写进 `展示项`，而不是塞进 extra ——
    # extra 是给程序读的，进不了报告；人类读者能看见的只有展示项。
    shown_cur = f"当前解释器: {cur}"

    if venv is None:
        return CheckResult(
            "解释器来源", WARN,
            f"{shown_cur} | 项目环境: 未找到 .venv —— "
            "上面的依赖 / GPU 检查反映的是「当前解释器」，"
            "而非项目环境；建好 .venv 后请用它重跑", extra)

    shown_venv = f"项目环境解释器: {venv}"

    if extra["is_venv_python"]:
        # 两者是同一条路径：仍然把两条都报出来，并明说它们是同一个。
        # 只写一行"项目环境: xxx"会让读者不知道当前解释器跑哪去了。
        return CheckResult(
            "解释器来源", OK,
            f"{shown_cur} | {shown_venv} | 两者是同一个解释器，结论代表项目环境", extra)

    # 建议命令按平台给，别让 Windows 用户去敲 POSIX 路径
    if os.name == "nt":
        suggested = r".venv\Scripts\python.exe scripts\verify.py"
    else:
        suggested = ".venv/bin/python scripts/verify.py"
    return CheckResult(
        "解释器来源", WARN,
        f"{shown_cur} | {shown_venv} | 两者不同："
        f"本次结论不代表项目环境，请改用: {suggested}", extra)


def check_python() -> CheckResult:
    ver = sys.version_info
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    detail = f"Python {platform.python_version()} @ {sys.executable}"
    extra = {"venv": in_venv, "version": list(ver[:3])}

    if ver[:2] < MIN_PY:
        return CheckResult("Python 版本", FAIL,
                           f"{detail} —— 低于最低要求 {MIN_PY[0]}.{MIN_PY[1]}", extra)
    if not in_venv:
        return CheckResult("Python 版本", WARN,
                           f"{detail} —— 不在虚拟环境里，建议用项目 venv", extra)
    return CheckResult("Python 版本", OK, detail, extra)


def check_deps() -> CheckResult:
    """分三层报告依赖。骨架阶段缺 train/eval 层是预期行为，只 warn。"""
    missing_core = [d for d in CORE_DEPS if not _has_module(d)]
    missing_train = [d for d in TRAIN_DEPS if not _has_module(d)]
    missing_eval = [d for d in EVAL_DEPS if not _has_module(d)]
    extra = {"missing_core": missing_core, "missing_train": missing_train,
             "missing_eval": missing_eval}

    lines = []
    lines.append(f"核心依赖: {'齐全' if not missing_core else '缺 ' + ', '.join(missing_core)}")
    lines.append(f"训练依赖: {'齐全' if not missing_train else '缺 ' + ', '.join(missing_train)}"
                 "（实验期才需要）")
    lines.append(f"评测依赖: {'齐全' if not missing_eval else '缺 ' + ', '.join(missing_eval)}"
                 "（实验期才需要）")

    if missing_core:
        return CheckResult("依赖清单", FAIL, " | ".join(lines), extra)
    return CheckResult("依赖清单", OK, " | ".join(lines), extra)


def check_gpu() -> CheckResult:
    """没有 GPU 只 warn —— 骨架阶段完全正常。"""
    if not _has_module("torch"):
        return CheckResult("GPU", WARN, "未安装 torch，跳过（实验期再查）", {"cuda": None})
    try:
        import torch  # noqa: PLC0415
        if not torch.cuda.is_available():
            return CheckResult("GPU", WARN, "torch 已装但 CUDA 不可用 —— 训练阶段需要 GPU",
                               {"cuda": False})
        n = torch.cuda.device_count()
        names = [torch.cuda.get_device_name(i) for i in range(n)]
        return CheckResult("GPU", OK, f"{n} 张卡: {', '.join(names)}", {"cuda": True, "count": n})
    except Exception as e:  # pragma: no cover - 依赖环境
        return CheckResult("GPU", WARN, f"检测失败: {type(e).__name__}: {e}", {"cuda": None})


def check_disk() -> CheckResult:
    """训练会吃掉大量磁盘，先看一眼。"""
    try:
        total, _, free = shutil.disk_usage(PROJECT_ROOT)
        free_gb = free / 1024 ** 3
        detail = f"可用 {free_gb:.1f} GB"
        # 10GB 以下提示，但不阻断
        return CheckResult("磁盘空间", OK if free_gb >= 10 else WARN, detail,
                           {"free_gb": round(free_gb, 1)})
    except Exception as e:  # pragma: no cover
        return CheckResult("磁盘空间", WARN, f"无法读取: {e}", {})


# 顺序即报告顺序：先讲清楚"这台机器在哪个环境里"，再报该环境的具体情况。
ALL_CHECKS = [check_env_identity, check_python, check_deps, check_gpu, check_disk]


def run_all() -> list[CheckResult]:
    return [c() for c in ALL_CHECKS]


def has_failure(results: list[CheckResult]) -> bool:
    return any(not r.ok for r in results)


def format_report(results: list[CheckResult]) -> str:
    """把检查结果渲染成人类可读的报告。

    同时渲染 `detail` 与 `extra`。**这一点很重要**：
    过去这里只读 `detail`，于是凡是"写进 extra"的信息（依赖缺失清单、
    磁盘余量、解释器路径……）在报告里全都凭空消失 ——
    测试却因为直接读属性而全部通过，形成一种"绿着但看不见"的假绿。
    """
    icon = {OK: "PASS", WARN: "WARN", FAIL: "FAIL"}
    lines = []
    for r in results:
        lines.append(f"  [{icon[r.status]}] {r.name}")
        for part in r.detail.split(" | "):
            if part:
                lines.append(f"         {part}")
        for key, value in r.extra.items():
            lines.append(f"         · {key}: {value}")
    return "\n".join(lines)


def main() -> int:
    results = run_all()
    print("=" * 66)
    print("  环境自检")
    print("=" * 66)
    print(format_report(results))
    print("-" * 66)
    if has_failure(results):
        bad = [r.name for r in results if not r.ok]
        print(f"结果：FAIL —— {len(bad)} 项需要处理: {', '.join(bad)}")
        return 1
    warn_n = sum(1 for r in results if r.status == WARN)
    print(f"结果：OK —— 无阻断问题" + (f"（{warn_n} 项提示，骨架阶段属正常）" if warn_n else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
