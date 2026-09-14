"""env_check 的测试。

重点测的是**约定**，不是实现细节：
  - 缺 GPU / 缺训练框架必须只 warn，绝不能 fail（否则骨架阶段验证永远是红的）
  - has_failure 只对 FAIL 敏感
  - 每个检查都必须返回结构化的东西，不能只是 print
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import pytest  # noqa: E402

from selfcheck import env_check as ec  # noqa: E402


# ------------------------------------------------------------------ 数据结构
def test_CheckResult_只有_FAIL_才算不ok():
    assert ec.CheckResult("x", ec.OK).ok is True
    assert ec.CheckResult("x", ec.WARN).ok is True, "warn 不该被当成失败"
    assert ec.CheckResult("x", ec.FAIL).ok is False


@pytest.mark.parametrize("fn", ec.ALL_CHECKS)
def test_每个检查都返回_CheckResult(fn):
    r = fn()
    assert isinstance(r, ec.CheckResult)
    assert r.name, "检查必须有名字，否则报告里看不出是哪一项"
    assert r.status in (ec.OK, ec.WARN, ec.FAIL)


def test_run_all_覆盖所有检查():
    results = ec.run_all()
    assert len(results) == len(ec.ALL_CHECKS)
    assert [r.name for r in results] == [fn().name for fn in ec.ALL_CHECKS]


# ------------------------------------------------------------------ 关键约定
def test_没有GPU不能导致验证失败():
    """这是本机（无 CUDA）和大多数新机器的真实情况，绝不能阻断。"""
    r = ec.check_gpu()
    assert r.status in (ec.OK, ec.WARN), "缺 GPU 必须是 warn 或 ok，不能是 fail"


def test_缺训练依赖不阻断验证():
    """骨架阶段没装 torch/trl 是正常的。"""
    r = ec.check_deps()
    missing_train = r.extra.get("missing_train", [])
    if missing_train:
        assert r.status in (ec.OK, ec.WARN), "缺训练依赖不该 fail"


def test_缺核心依赖才算失败():
    """用打桩的方式验证：核心依赖缺失时必须 FAIL。"""
    real = ec._has_module
    try:
        ec._has_module = lambda name: name not in ec.CORE_DEPS
        r = ec.check_deps()
        assert r.status == ec.FAIL
        assert set(r.extra["missing_core"]) == set(ec.CORE_DEPS)
    finally:
        ec._has_module = real


# ------------------------------------------------------------------ 汇总
def test_has_failure_只对FAIL敏感():
    assert ec.has_failure([ec.CheckResult("a", ec.OK), ec.CheckResult("b", ec.WARN)]) is False
    assert ec.has_failure([ec.CheckResult("a", ec.OK), ec.CheckResult("b", ec.FAIL)]) is True


def test_format_report_包含每个检查名():
    rs = [ec.CheckResult("甲", ec.OK, "细节1"), ec.CheckResult("乙", ec.FAIL, "细节2")]
    out = ec.format_report(rs)
    for token in ("甲", "乙", "细节1", "细节2", "PASS", "FAIL"):
        assert token in out


def test_main_在没有失败时返回0():
    """main 的退出码必须与 has_failure 一致。"""
    assert ec.main() == (1 if ec.has_failure(ec.run_all()) else 0)
