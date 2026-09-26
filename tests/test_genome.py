"""genome 模块测试：结构 / motif affinity / E_A,E_B / 阈值 / 遗传算子 / 可复现。

契约来源：``genome/生物学与进化遗传学基础.md``（v1.7 已定稿）、
``development/RGCD数学模型.md`` §2（参数）、``schemas/genome.schema.json``。
固定种子取 ``configs/demo_seed.yaml`` 的 ``master_seed=250927``。
"""

from __future__ import annotations

from collections import Counter

import numpy as np
import pytest

from evogenesis.core.seed import SeedManager
from evogenesis.genome import genome as G
from evogenesis.genome.config import DEFAULT_LAYOUT

MASTER_SEED = 250927
MOTIF_A = "AAACCC"
MOTIF_B = "CCCAAA"
# 8 条目录；本测试只依赖 index 0/1（K_A={0}, K_B={1}），其余仅填充 q(G) 维度。
MOTIF_CATALOG = [MOTIF_A, MOTIF_B, "ACGTAC", "AACGTT", "TGCAAC", "GGGTAA", "CATGCA", "TTCGAA"]
BACKBONE = "G"
MARKER_POSITIONS = (10, 40, 70)


def _chromosome_with(motif: str, positions: tuple[int, ...] = MARKER_POSITIONS) -> str:
    seq = list(BACKBONE * DEFAULT_LAYOUT.bp_per_haplotype_chromosome)
    for start in positions:
        for offset, symbol in enumerate(motif):
            seq[start + offset] = symbol
    return "".join(seq)


FUNC_A = _chromosome_with(MOTIF_A)
FUNC_B = _chromosome_with(MOTIF_B)
LOSS = BACKBONE * DEFAULT_LAYOUT.bp_per_haplotype_chromosome


def _genome(pair0: G.ChromosomePair, pair1: G.ChromosomePair) -> G.DiploidGenome:
    return G.DiploidGenome((pair0, pair1))


def _mendel_parent() -> G.DiploidGenome:
    return _genome(
        G.ChromosomePair(FUNC_A, LOSS),
        G.ChromosomePair(FUNC_B, LOSS),
    )


class _StubRng:
    """按给定序列返回 ``random()``，用于确定性测试遗传算子。"""

    def __init__(self, values: list[float]) -> None:
        self._values = list(values)
        self._index = 0

    def random(self) -> float:
        value = self._values[self._index % len(self._values)]
        self._index += 1
        return value


# ---------------------------------------------------------------------------
# 结构 / DNA 契约
# ---------------------------------------------------------------------------


def test_chromosome_validation_length_and_alphabet():
    with pytest.raises(ValueError):
        G.ChromosomePair("A" * 127, "A" * 128)
    with pytest.raises(ValueError):
        G.ChromosomePair("A" * 128, "N" * 128)
    with pytest.raises(ValueError):
        G.DiploidGenome((G.ChromosomePair("A" * 128, "A" * 128),))  # type: ignore[arg-type]


def test_diploid_and_haploid_bp():
    genome = _genome(
        G.ChromosomePair("A" * 128, "C" * 128),
        G.ChromosomePair("G" * 128, "T" * 128),
    )
    assert genome.diploid_bp == 512
    assert genome.haploid_bp == 256


def test_schema_exchange_shape_roundtrip():
    genome = G.DiploidGenome(
        (G.ChromosomePair(FUNC_A, LOSS), G.ChromosomePair(FUNC_B, LOSS)),
        genome_id="g-0001",
    )
    payload = genome.to_dict()
    assert set(payload) == {"genome_id", "chromosome_pairs"}
    assert len(payload["chromosome_pairs"]) == 2
    for item in payload["chromosome_pairs"]:
        assert len(item["maternal"]) == 128 and len(item["paternal"]) == 128
        assert set(item["maternal"]) <= set("".join(DEFAULT_LAYOUT.alphabet))
        assert set(item["paternal"]) <= set("".join(DEFAULT_LAYOUT.alphabet))
    assert G.DiploidGenome.from_dict(payload) == genome


def test_to_dict_requires_nonempty_genome_id():
    genome = G.DiploidGenome((G.ChromosomePair(FUNC_A, LOSS), G.ChromosomePair(FUNC_B, LOSS)))
    with pytest.raises(ValueError):
        genome.to_dict()


def test_from_dict_requires_genome_id():
    payload = {
        "chromosome_pairs": [
            {"maternal": FUNC_A, "paternal": LOSS},
            {"maternal": FUNC_B, "paternal": LOSS},
        ]
    }
    with pytest.raises(KeyError):
        G.DiploidGenome.from_dict(payload)


def test_from_dict_rejects_wrong_pair_count():
    payload = {
        "genome_id": "g-0001",
        "chromosome_pairs": [{"maternal": FUNC_A, "paternal": LOSS}],
    }
    with pytest.raises(ValueError):
        G.DiploidGenome.from_dict(payload)


# ---------------------------------------------------------------------------
# motif affinity / TopKMean（genome §6；参数引用 RGCD §2）
# ---------------------------------------------------------------------------


def test_motif_affinity_is_one_minus_hamming_ratio():
    assert G.motif_affinity("ACGTAC", "ACGTAC") == pytest.approx(1.0)
    assert G.motif_affinity("ACGTAC", "ACGTAG") == pytest.approx(5.0 / 6.0)
    assert G.motif_affinity("ACGTAC", "TGCATG") == pytest.approx(0.0)
    with pytest.raises(ValueError):
        G.motif_affinity("ACGTAC", "ACG")


def test_top_k_mean_uses_largest_k():
    values = np.array([0.0, 1.0, 1.0, 1.0, 0.5], dtype=np.float32)
    assert G.top_k_mean(values, 3) == pytest.approx(1.0)
    assert G.top_k_mean(values, 5) == pytest.approx((0.0 + 1.0 + 1.0 + 1.0 + 0.5) / 5)
    # K 超过窗口数时退化为全部窗口均值
    assert G.top_k_mean(values, 99) == pytest.approx(float(values.mean()))
    with pytest.raises(ValueError):
        G.top_k_mean(np.array([], dtype=np.float32), 3)
    with pytest.raises(ValueError):
        G.top_k_mean(values, 0)


def test_window_affinities_rejects_out_of_range_motif_and_step():
    with pytest.raises(ValueError):
        G.window_affinities("ACGT", "ACGTAC")
    with pytest.raises(ValueError):
        G.window_affinities("ACGTACGT", "ACGT", step=0)


def test_chain_affinity_hits_one_and_knockout_zero():
    assert G.chain_affinity(FUNC_A, MOTIF_A) == pytest.approx(1.0)
    assert G.chain_affinity(LOSS, MOTIF_A) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# E_A / E_B ∈ {0, 0.5, 1} 与阈值判定（genome §3）
# ---------------------------------------------------------------------------


def test_expression_values_AA_Aa_aa():
    aa = _genome(G.ChromosomePair(LOSS, LOSS), G.ChromosomePair(LOSS, LOSS))
    parent = _genome(G.ChromosomePair(FUNC_A, FUNC_A), G.ChromosomePair(FUNC_B, FUNC_B))
    hetero = _genome(G.ChromosomePair(FUNC_A, LOSS), G.ChromosomePair(FUNC_B, LOSS))
    assert float(G.expression_A(parent, MOTIF_CATALOG, (0,))) == pytest.approx(1.0)
    assert float(G.expression_A(hetero, MOTIF_CATALOG, (0,))) == pytest.approx(0.5)
    assert float(G.expression_A(aa, MOTIF_CATALOG, (0,))) == pytest.approx(0.0)
    assert float(G.expression_B(parent, MOTIF_CATALOG, (1,))) == pytest.approx(1.0)
    assert float(G.expression_B(hetero, MOTIF_CATALOG, (1,))) == pytest.approx(0.5)
    assert float(G.expression_B(aa, MOTIF_CATALOG, (1,))) == pytest.approx(0.0)


def test_theta_025_gives_complete_dominance_of_Aa():
    hetero = _genome(G.ChromosomePair(FUNC_A, LOSS), G.ChromosomePair(FUNC_B, LOSS))
    e_a = G.expression_A(hetero, MOTIF_CATALOG, (0,))
    e_b = G.expression_B(hetero, MOTIF_CATALOG, (1,))
    assert G.architecture(e_a, e_b, 0.25, 0.25) == G.Architecture(True, True)
    assert G.architecture(e_a, e_b, 0.25, 0.25).class_label == "A_B_"
    aa = _genome(G.ChromosomePair(LOSS, LOSS), G.ChromosomePair(LOSS, LOSS))
    arch = G.architecture(
        G.expression_A(aa, MOTIF_CATALOG, (0,)),
        G.expression_B(aa, MOTIF_CATALOG, (1,)),
        0.25,
        0.25,
    )
    assert arch == G.Architecture(False, False)
    assert arch.class_label == "aabb"


@pytest.mark.parametrize(
    ("high_n", "high_h", "label"),
    [
        (True, True, "A_B_"),
        (True, False, "A_bb"),
        (False, True, "aaB_"),
        (False, False, "aabb"),
    ],
)
def test_architecture_class_labels(high_n, high_h, label):
    assert G.Architecture(high_n, high_h).class_label == label


# ---------------------------------------------------------------------------
# q(G)：加性主模型 vs max 消融（genome §6）
# ---------------------------------------------------------------------------


def test_combine_haplotypes_additive_and_max():
    q1 = np.array([1.0, 0.0, 0.5], dtype=np.float32)
    q2 = np.array([0.0, 1.0, 0.25], dtype=np.float32)
    assert G.combine_haplotypes(q1, q2, mode="additive") == pytest.approx(
        np.array([0.5, 0.5, 0.375], dtype=np.float32)
    )
    assert G.combine_haplotypes(q1, q2, mode="max") == pytest.approx(
        np.array([1.0, 1.0, 0.5], dtype=np.float32)
    )
    with pytest.raises(ValueError):
        G.combine_haplotypes(q1, q2, mode="sum")


def test_genome_affinity_shape_dtype_and_max_ablation():
    parent = _genome(G.ChromosomePair(FUNC_A, FUNC_A), G.ChromosomePair(FUNC_B, FUNC_B))
    q_add = G.genome_affinity(parent, MOTIF_CATALOG, mode="additive")
    q_max = G.genome_affinity(parent, MOTIF_CATALOG, mode="max")
    assert q_add.shape == (8,) and q_add.dtype == np.float32
    assert q_max.shape == (8,) and q_max.dtype == np.float32
    assert np.all(q_add <= 1.0) and np.all(q_add >= 0.0)
    assert np.all(q_max >= q_add - 1e-6)


# ---------------------------------------------------------------------------
# 遗传算子（genome §4/§5）
# ---------------------------------------------------------------------------


def test_crossover_no_event_returns_originals():
    a = "A" * 128
    b = "C" * 128
    assert G.crossover(a, b, 0.0, _StubRng([0.0])) == (a, b)


def test_crossover_swaps_at_uniform_point():
    a = "A" * 128
    b = "C" * 128
    recombinant_m, recombinant_p = G.crossover(a, b, 1.0, _StubRng([0.0, 0.0]))
    assert recombinant_m == "A" + "C" * 127
    assert recombinant_p == "C" + "A" * 127


def test_crossover_rejects_unequal_lengths():
    with pytest.raises(ValueError):
        G.crossover("A" * 128, "C" * 64, 0.5, _StubRng([0.0]))


def test_fertilize_rejects_wrong_gamete_shape():
    with pytest.raises(ValueError):
        G.fertilize(("A" * 128,), ("C" * 128, "T" * 128))


def test_mutation_rejects_non_acgt_and_mu_out_of_range():
    rng = SeedManager(MASTER_SEED).rng("mutation")
    with pytest.raises(ValueError):
        G.mutate_sequence("N" * 8, 0.5, rng)
    with pytest.raises(ValueError):
        G.mutate_sequence("ACGT" * 4, 1.5, rng)


def test_mutation_zero_rate_is_identity():
    rng = SeedManager(MASTER_SEED).rng("mutation")
    seq = "ACGT" * 32
    assert G.mutate_sequence(seq, 0.0, rng) == seq


def test_meiosis_selects_one_chromosome_per_pair():
    genome = _genome(
        G.ChromosomePair("A" * 128, "C" * 128),
        G.ChromosomePair("G" * 128, "T" * 128),
    )
    # pair0: no crossover + select maternal; pair1: no crossover + select paternal.
    gamete = G.meiosis(genome, 0.0, _StubRng([0.0, 0.0, 0.0, 0.9]))
    assert gamete == ("A" * 128, "T" * 128)


def test_fertilize_builds_diploid_genome():
    gamete_a = ("A" * 128, "G" * 128)
    gamete_b = ("C" * 128, "T" * 128)
    child = G.fertilize(gamete_a, gamete_b)
    assert child.pairs[0] == G.ChromosomePair("A" * 128, "C" * 128)
    assert child.pairs[1] == G.ChromosomePair("G" * 128, "T" * 128)
    assert child.diploid_bp == 512


def test_mutation_only_substitutes_bases():
    rng = SeedManager(MASTER_SEED).rng("mutation")
    mutated = G.mutate_sequence("ACGT" * 32, 1.0, rng)
    assert len(mutated) == 128
    assert set(mutated) <= set("".join(DEFAULT_LAYOUT.alphabet))
    assert all(original != changed for original, changed in zip("ACGT" * 32, mutated, strict=True))


def test_snp_rate_mu_0001_over_256bp():
    rng = SeedManager(MASTER_SEED).rng("mutation")
    sequence = "ACGT" * 64  # 256 bp haploid
    trials = 4000
    snps = sum(
        G.hamming_distance(sequence, G.mutate_sequence(sequence, 0.001, rng)) for _ in range(trials)
    )
    mean_snp = snps / trials
    # 期望 0.256；n=4000 下均值标准误 ≈ 0.008，容差 0.03 ≈ 3.7σ。
    assert mean_snp == pytest.approx(0.256, abs=0.03)


# ---------------------------------------------------------------------------
# Mendel Mode：AaBb × AaBb → 四类计数 9:3:3:1（genome §3）
# ---------------------------------------------------------------------------


def test_mendel_9331_fixed_seed():
    """genome §3：9:3:3:1 是 pc=0（不交叉）的理想分离结果。

    pc>0 时串联 motif 标记会被交叉拆散、部分功能染色体重组后仍越阈，
    四类比例向 A_B_ 偏斜——见 test_crossover_breaks_9331_as_documented。
    """
    seed_manager = SeedManager(MASTER_SEED)
    crossover_rng = seed_manager.rng("crossover")
    mutation_rng = seed_manager.rng("mutation")
    parent_a = _mendel_parent()
    parent_b = _mendel_parent()
    counts: Counter[str] = Counter()
    offspring_n = 2000
    for _ in range(offspring_n):
        gamete_a = G.make_gamete(parent_a, 0.0, 0.0, crossover_rng, mutation_rng)
        gamete_b = G.make_gamete(parent_b, 0.0, 0.0, crossover_rng, mutation_rng)
        child = G.fertilize(gamete_a, gamete_b)
        e_a = G.expression_A(child, MOTIF_CATALOG, (0,))
        e_b = G.expression_B(child, MOTIF_CATALOG, (1,))
        counts[G.architecture(e_a, e_b, 0.25, 0.25).class_label] += 1

    order = ["A_B_", "A_bb", "aaB_", "aabb"]
    expected = [9 / 16, 3 / 16, 3 / 16, 1 / 16]
    total = sum(counts.values())
    assert total == offspring_n
    chi_square = sum(
        (counts[label] - total * prob) ** 2 / (total * prob)
        for label, prob in zip(order, expected, strict=True)
    )
    # χ²(df=3, α=0.05) 临界 7.8147；固定种子下确定性通过。
    assert chi_square < 7.8147
    for label, prob in zip(order, expected, strict=True):
        assert counts[label] / total == pytest.approx(prob, abs=0.03)


def test_crossover_breaks_9331_as_documented():
    """genome §3：pc>0 时四类比例向 A_B_ 偏斜，属演示装置的预期行为。

    文档口径 n=4000，本测试 n=2000 仅验定性方向（χ² 远大于临界值）。
    """
    seed_manager = SeedManager(MASTER_SEED)
    crossover_rng = seed_manager.rng("crossover")
    mutation_rng = seed_manager.rng("mutation")
    counts: Counter[str] = Counter()
    offspring_n = 2000
    for _ in range(offspring_n):
        gamete_a = G.make_gamete(_mendel_parent(), 0.0, 0.5, crossover_rng, mutation_rng)
        gamete_b = G.make_gamete(_mendel_parent(), 0.0, 0.5, crossover_rng, mutation_rng)
        child = G.fertilize(gamete_a, gamete_b)
        e_a = G.expression_A(child, MOTIF_CATALOG, (0,))
        e_b = G.expression_B(child, MOTIF_CATALOG, (1,))
        counts[G.architecture(e_a, e_b, 0.25, 0.25).class_label] += 1

    order = ["A_B_", "A_bb", "aaB_", "aabb"]
    expected = [9 / 16, 3 / 16, 3 / 16, 1 / 16]
    total = sum(counts.values())
    chi_square = sum(
        (counts[label] - total * prob) ** 2 / (total * prob)
        for label, prob in zip(order, expected, strict=True)
    )
    assert chi_square > 7.8147
    assert counts["A_B_"] / total > 9 / 16
    assert counts["aabb"] / total < 1 / 16


# ---------------------------------------------------------------------------
# 可复现（同一 seed）
# ---------------------------------------------------------------------------


def test_same_seed_reproducible_and_different_seed_differs():
    def draw(seed: int):
        manager = SeedManager(seed)
        genome = _mendel_parent()
        return G.make_gamete(
            genome,
            0.001,
            0.5,
            manager.rng("crossover"),
            manager.rng("mutation"),
        )

    assert draw(MASTER_SEED) == draw(MASTER_SEED)
    assert draw(MASTER_SEED) != draw(MASTER_SEED + 1)


def test_haplotype_affinity_is_union_of_chromosome_windows():
    """genome §6：单倍型 q 取本 haplotype **两条染色体窗口并集**的 TopKMean（不跨染色体）。"""
    genome = G.random_genome(
        DEFAULT_LAYOUT, rng=np.random.default_rng(3), genome_id="exp:g0:genome0000"
    )
    motifs = tuple("AAAAAA" if i else "CCCCCC" for i in range(8))
    for haplotype in (genome.maternal_haplotype, genome.paternal_haplotype):
        q = G.haplotype_affinity(haplotype, motifs)
        expected = np.array(
            [
                G.top_k_mean(
                    np.concatenate([G.window_affinities(chain, motif) for chain in haplotype]),
                    DEFAULT_LAYOUT.motif_topk,
                )
                for motif in motifs
            ],
            dtype=np.float32,
        )
        assert np.allclose(q, expected)
        # 并集 ⊇ 单链窗口 → 每个 motif 的 q 不低于任一单链
        for motif_index, motif in enumerate(motifs):
            per_chain = [G.chain_affinity(chain, motif) for chain in haplotype]
            assert q[motif_index] >= max(per_chain) - 1e-6
