"""选择算子（owner：``evolution/遗传繁殖与演化模型.md`` §5）：binary tournament（``k=2``）。

- 候选池 = 当代 ``viable=True`` 的个体（non-viable 排除；``viable`` 但 ``F=0`` 者仍可入选）；
- 每次锦标赛按 ``rng`` **有放回**抽 ``tournament_size`` 个候选、比较 ``F``、取最大者；
  ``F`` 并列时取抽中顺序中**先出现**的候选（``np.argmax`` 的语义）；
- 候选数 ``< tournament_size`` 时锦标赛无法组成，抛 ``ValueError``（配置非法）；
- 不使用比例 / softmax 选择。

随机源由调用方注入 ``numpy.random.Generator``（``core §3`` 的 ``selection`` 命名空间）。
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def is_population_bottleneck(candidates: Sequence[int] | np.ndarray) -> bool:
    """候选（viable）个体不足 2 个、无法配对时判瓶颈（``evolution §5``）。"""
    return np.asarray(candidates, dtype=np.intp).size < 2


def binary_tournament(
    fitness: Sequence[float] | np.ndarray,
    candidates: Sequence[int] | np.ndarray,
    *,
    tournament_size: int,
    rng: np.random.Generator,
    n_selections: int,
) -> np.ndarray:
    """从 ``candidates`` 中做 ``n_selections`` 次 binary tournament，返回亲本下标（有放回）。

    ``fitness`` 为全体个体的 ``F`` 向量（下标对齐）；``candidates`` 是允许进入候选池的下标
    （viable 个体）。返回形状 ``(n_selections,)``、dtype ``intp``。候选数小于 ``tournament_size``
    时抛 ``ValueError``（``evolution §5``：锦标赛不可组成，配置非法）。
    """
    fit = np.asarray(fitness, dtype=np.float32)
    cand = np.asarray(candidates, dtype=np.intp)
    if fit.ndim != 1:
        raise ValueError("fitness 必须是一维数组")
    if cand.ndim != 1:
        raise ValueError("candidates 必须是一维数组")
    if cand.size == 0:
        raise ValueError("候选池为空，无法进行锦标赛")
    if cand.min() < 0 or cand.max() >= fit.size:
        raise ValueError("候选下标越界")
    if tournament_size < 2:
        raise ValueError(f"binary tournament 的 k 必须 ≥ 2，实际 {tournament_size}")
    if cand.size < tournament_size:
        raise ValueError(f"候选池（{cand.size}）小于锦标赛规模 {tournament_size}")
    if n_selections < 0:
        raise ValueError("n_selections 必须非负")
    if n_selections == 0:
        return np.empty(0, dtype=np.intp)
    draws = rng.integers(0, cand.size, size=(n_selections, tournament_size))
    contenders = cand[draws]
    contender_fitness = fit[contenders]
    winners = np.argmax(contender_fitness, axis=1)
    return cand[draws[np.arange(n_selections), winners]].astype(np.intp)


def random_pairs(selected: Sequence[int] | np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """把已选亲本下标随机置换后相邻两两配对，**尽量禁自体配对**，返回 ``(n_pairs, 2)``。

    算法（``evolution §5`` 随机配对，定稿）：随机置换后逐对修复——对内两下标相同则与
    **其后最近一个不同下标**交换；若其后无不同下标，则与**其前一个能保持配对合法性的下标**交换；
    多轮修复直到无冲突。

    **可行性边界**：当某个亲本被抽中次数超过 n/2（n=2N，即有放回抽样下单个亲本占据
    超过一半槽位）时，自体配对在数学上**不可避免**；此时退回到「按值排序后对半配对」的构造，
    只保留**最少数量**（m-N 个，m 为该亲本出现次数且 m>N）的自体配对。
    """
    sel = np.asarray(selected, dtype=np.intp)
    if sel.ndim != 1:
        raise ValueError("selected 必须是一维数组")
    if sel.size % 2 != 0:
        raise ValueError("随机配对要求偶数个亲本")
    if sel.size == 0:
        return np.empty((0, 2), dtype=np.intp)
    arr = sel[rng.permutation(sel.size)].copy()
    if _repair_all(arr):
        return arr.reshape(-1, 2)
    return _minimal_self_pairing(arr, rng)


def _repair_pair(arr: np.ndarray, i: int) -> bool:
    """把已置换数组 ``arr`` 的第 ``i``/``i+1`` 个元素修成不同值；成功返回 ``True``。

    先在其后找最近的不同下标；找不到再到其前找，且要求交换后不会破坏先前已合法的配对。
    """
    n = arr.size
    for j in range(i + 2, n):
        if arr[j] != arr[i]:
            arr[i + 1], arr[j] = arr[j], arr[i + 1]
            return True
    for j in range(i - 1, -1, -1):
        partner = j - 1 if j % 2 == 1 else j + 1
        if arr[j] != arr[i] and arr[partner] != arr[i]:
            arr[i + 1], arr[j] = arr[j], arr[i + 1]
            return True
    return False


def _repair_all(arr: np.ndarray) -> bool:
    """多轮修复 ``arr`` 的相邻配对；完全无自体配对时返回 ``True``。"""
    n = arr.size
    for _ in range(n + 1):
        bad = [i for i in range(0, n, 2) if arr[i] == arr[i + 1]]
        if not bad:
            return True
        progress = False
        for i in bad:
            if _repair_pair(arr, i):
                progress = True
        if not progress:
            return False
    return not any(arr[i] == arr[i + 1] for i in range(0, n, 2))


def _minimal_self_pairing(arr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """按值稳定排序后对半配对，得到**最少自体配对**；rng 用于打乱组内顺序与对序。"""
    n = arr.size
    ordered = arr[np.argsort(arr, kind="stable")]
    half = n // 2
    pairs = np.stack([ordered[:half], ordered[half:]], axis=1).astype(np.intp, copy=True)
    rng.shuffle(pairs)
    flip = rng.random(half) < 0.5
    pairs[flip] = pairs[flip][:, ::-1]
    return pairs
