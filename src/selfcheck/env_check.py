"""环境与依赖自检 —— 供 `scripts/verify.py` 和人工排查使用。

设计原则：
  1. **零硬依赖**：没装 torch / trl 也要能跑，只是报 warn 而不是崩。
  2. **warning 不等于 error**：骨架阶段没有 GPU、没有训练框架是正常的，
     不该让验证失败。只有"根本跑不下去"的问题才算 fail。
  3. 输出既可读（给人看），也可结构化（给脚本判断）。

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
        total, _, free = shutil.disk_usage(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
        free_gb = free / 1024 ** 3
        detail = f"可用 {free_gb:.1f} GB"
        # 10GB 以下提示，但不阻断
        return CheckResult("磁盘空间", OK if free_gb >= 10 else WARN, detail,
                           {"free_gb": round(free_gb, 1)})
    except Exception as e:  # pragma: no cover
        return CheckResult("磁盘空间", WARN, f"无法读取: {e}", {})


ALL_CHECKS = [check_python, check_deps, check_gpu, check_disk]


def run_all() -> list[CheckResult]:
    return [c() for c in ALL_CHECKS]


def has_failure(results: list[CheckResult]) -> bool:
    return any(not r.ok for r in results)


def format_report(results: list[CheckResult]) -> str:
    icon = {OK: "PASS", WARN: "WARN", FAIL: "FAIL"}
    lines = []
    for r in results:
        lines.append(f"  [{icon[r.status]}] {r.name}")
        for part in r.detail.split(" | "):
            if part:
                lines.append(f"         {part}")
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
