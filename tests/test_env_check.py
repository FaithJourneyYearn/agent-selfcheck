"""env_check 的测试。

重点测的是**约定**，不是实现细节：
  - 缺 GPU / 缺训练框架必须只 warn，绝不能 fail（否则骨架阶段验证永远是红的）
  - has_failure 只对 FAIL 敏感
  - 每个检查都必须返回结构化的东西，不能只是 print
  - 解释器来源必须如实分类：用项目 venv 跑才算 OK，其余一律 warn
  - **两条解释器路径都必须出现在人看得见的报告文本里**（不是只进 extra）
  - format_report 必须渲染 extra —— 否则写进 extra 的信息等于没写
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


# ------------------------------------------------------------------ 解释器来源
def test_找不到_venv_时必须_warn_而不是_fail():
    """骨架阶段 .venv 常不存在，这一条绝不能阻断验证。

    同时它必须是 WARN：如果这里给出 PASS，就等于在说
    "我检查的就是项目环境"——那是假的，检查的其实是当前解释器。
    """
    real = ec.find_project_venv
    try:
        ec.find_project_venv = lambda: None
        r = ec.check_env_identity()
        assert r.status == ec.WARN, "未找到项目环境应当是 warn（不阻断但必须提醒）"
        assert r.extra["venv_exists"] is False
        assert r.extra["current_python"], "必须报出当前解释器的绝对路径"
    finally:
        ec.find_project_venv = real


def test_用venv跑时报告结论代表项目环境():
    real_find, real_exe = ec.find_project_venv, ec.sys.executable
    try:
        ec.find_project_venv = lambda: real_exe  # 假装当前就是项目环境
        ec.sys.executable = real_exe
        r = ec.check_env_identity()
        assert r.status == ec.OK
        assert r.extra["is_venv_python"] is True
    finally:
        ec.find_project_venv, ec.sys.executable = real_find, real_exe


def test_用venv跑时也必须在报告里同时报出两条解释器路径():
    """两者相同时最容易被写成"只报一条"。

    但读者看到"项目环境: xxx"会问"那当前解释器呢"。
    约定是：**不管相不相同，两条都要出现在人看得见的文本里。**
    """
    real_find, real_exe = ec.find_project_venv, ec.sys.executable
    try:
        ec.find_project_venv = lambda: real_exe
        ec.sys.executable = real_exe
        r = ec.check_env_identity()
        rendered = ec.format_report([r])
        assert real_exe in rendered, "当前解释器路径必须在报告里出现"
        assert "当前解释器" in rendered, "两条路径要各自有标签，别混成一句"
        assert "项目环境解释器" in rendered, "项目环境路径也必须有标签"
    finally:
        ec.find_project_venv, ec.sys.executable = real_find, real_exe


def test_两条路径不同时报告里也要两条都在():
    real_find, real_exe = ec.find_project_venv, ec.sys.executable
    try:
        ec.find_project_venv = lambda: r"C:\fake\.venv\Scripts\python.exe"
        r = ec.check_env_identity()
        rendered = ec.format_report([r])
        assert real_exe in rendered
        assert r"C:\fake\.venv\Scripts\python.exe" in rendered
    finally:
        ec.find_project_venv = real_find


def test_venv存在但用的不是它时必须_warn并给出建议命令():
    """这是最容易被忽视的情形：环境建好了，但人拿系统 Python 跑了 verify。

    此时结论不代表项目环境，必须提醒，并且给出的命令要能在本平台直接粘贴。
    """
    real = ec.find_project_venv
    try:
        ec.find_project_venv = lambda: r"C:\fake\.venv\Scripts\python.exe"
        r = ec.check_env_identity()
        assert r.status == ec.WARN
        assert r.extra["is_venv_python"] is False
        expect = "Scripts" if os.name == "nt" else "bin/python"
        assert expect in r.detail, "建议命令要按平台给，别让 Windows 用户敲 POSIX 路径"
    finally:
        ec.find_project_venv = real


def test_解释器来源排在检查列表最前():
    """报告的第一段应当先讲清前提，再给依赖/GPU 结论。"""
    assert ec.ALL_CHECKS[0] is ec.check_env_identity


# ------------------------------------------------------------------ 汇总
def test_has_failure_只对FAIL敏感():
    assert ec.has_failure([ec.CheckResult("a", ec.OK), ec.CheckResult("b", ec.WARN)]) is False
    assert ec.has_failure([ec.CheckResult("a", ec.OK), ec.CheckResult("b", ec.FAIL)]) is True


def test_format_report_包含每个检查名():
    rs = [ec.CheckResult("甲", ec.OK, "细节1"), ec.CheckResult("乙", ec.FAIL, "细节2")]
    out = ec.format_report(rs)
    for token in ("甲", "乙", "细节1", "细节2", "PASS", "FAIL"):
        assert token in out


def test_format_report_必须渲染_extra_否则信息会凭空消失():
    """这是本项目踩过的真坑：`extra` 曾经完全不进报告。

    后果不是"少印一行"，而是**写进 extra 的信息在报告里彻底不存在** ——
    依赖缺失清单、磁盘余量、解释器路径全都被吞掉，而单元测试因为直接读
    `r.extra[...]` 属性照样全绿。于是"验证通过"和"人什么都看不见"同时成立。
    """
    r = ec.CheckResult("丙", ec.WARN, "细节", {"磁盘余量": "1.5 GB"})
    out = ec.format_report([r])
    assert "1.5 GB" in out, "extra 的值得出现在报告里"
    assert "磁盘余量" in out, "extra 的键也要出现，否则读者不知道这数字是什么"


def test_真实检查的_extra_在报告里看得见():
    """拿真实检查跑一遍，端到端确认不是只有构造出来的对象才行。"""
    rendered = ec.format_report(ec.run_all())
    assert "missing_core" in rendered, "依赖检查的 extra 必须可见"
    assert "free_gb" in rendered, "磁盘检查的 extra 必须可见"


def test_main_在没有失败时返回0():
    """main 的退出码必须与 has_failure 一致。"""
    assert ec.main() == (1 if ec.has_failure(ec.run_all()) else 0)
