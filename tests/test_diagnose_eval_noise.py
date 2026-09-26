"""评估噪声诊断脚本的纯统计件（`scripts/diagnose_eval_noise.py`）。

`scripts/` 不是包，按路径用 importlib 载入（与 `test_dump_connectome_matrix.py` 同法）。
只测不跑 Arena 的纯函数：跨代面板本身由 CLI 跑，属证据而非单测范围。
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "diagnose_eval_noise", ROOT / "scripts" / "diagnose_eval_noise.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def diag():
    return _load()


def test_spearman_is_one_for_monotone_and_minus_one_for_reversed(diag):
    assert diag.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert diag.spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)


def test_spearman_is_invariant_to_monotone_transforms(diag):
    """秩相关只认排序：正单调变换不改变结果。"""
    base = [3, 1, 4, 1, 5, 9]
    assert diag.spearman(base, [2, 4, 6, 8, 10, 12]) == pytest.approx(
        diag.spearman(base, [1, 2, 3, 4, 5, 6])
    )


def test_spearman_brown_reduces_to_single_at_k1(diag):
    assert diag.spearman_brown(0.069, 1) == pytest.approx(0.069)


def test_spearman_brown_is_monotone_and_bounded(diag):
    values = [diag.spearman_brown(0.069, k) for k in range(1, 60)]
    assert values == sorted(values)
    assert all(0.0 <= v < 1.0 for v in values)


def test_required_k_matches_the_measured_panel(diag):
    """11 下标面板实测 rho_1 = 0.069：达到 0.5 需约 14 次实现，0.7 约 32 次。"""
    assert 10 <= diag.required_k(0.069, 0.5) <= 20
    assert 25 <= diag.required_k(0.069, 0.7) <= 40


def test_non_positive_reliability_has_no_solution(diag):
    """小面板可能给出 <= 0 的估计（抽样伪影）；此时不可达，须返回 None 而非乱填。"""
    assert diag.spearman_brown(0.0, 20) == 0.0
    assert diag.required_k(0.0, 0.5) is None
    assert diag.required_k(-0.29, 0.5) is None


def test_spearman_brown_rejects_non_positive_k(diag):
    with pytest.raises(ValueError):
        diag.spearman_brown(0.069, 0)


def test_spearman_handles_zero_variance(diag):
    """常量向量没有秩相关可言 —— 须返回 0 而不是除零。"""
    assert not math.isnan(diag.spearman([1, 1, 1], [1, 2, 3]))
