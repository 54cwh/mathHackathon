"""二倍体基因组：结构、motif affinity、位点表达与遗传算子。

契约 owner（唯一来源）：
- ``genome/生物学与进化遗传学基础.md`` §2（二倍体）、§3（``E_A/E_B`` 与 9:3:3:1、
  ``θ_N=θ_H=0.25``、四类 phenotype）、§4（重组四步）、§5（SNP mutation ``μ=0.001``）、
  §6（``a``、``TopKMean``、``q^{(h)}``、``q(G)``）。
- motif 长度/窗口/步长/``K`` 的**参数取值**单向引用
  ``development/RGCD数学模型.md`` §2（本模块不另立数值）。
- 交换/落盘形态对齐 ``schemas/genome.schema.json``（``genome_id`` + 2×(128+128) bp, ACGT）。
- ``bp_per_haplotype_chromosome=128`` / ``chromosome_pairs=2`` 取值见
  ``configs/default_model.yaml``。

随机数纪律：随机过程接收 ``numpy.random.Generator``（由 ``core/seed.py`` 的 ``SeedManager``
派生，命名空间 ``mutation=0`` / ``crossover=1``）；本模块不使用 Python ``random``。
数值 dtype：``q`` 向量与 ``E`` 标量统一 ``float32``（``core/核心机制与数据流.md`` §7）。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from evogenesis.genome.config import DEFAULT_LAYOUT, GenomeLayout

Haplotype = tuple[str, ...]
Gamete = Haplotype


def _validate_alphabet(seq: str, label: str, layout: GenomeLayout = DEFAULT_LAYOUT) -> None:
    if not isinstance(seq, str):
        raise ValueError(f"{label} 必须是字符串")
    invalid = set(seq) - set(layout.alphabet)
    if invalid:
        raise ValueError(f"{label} 含非 {'/'.join(layout.alphabet)} 符号：{sorted(invalid)}")


def _validate_sequence(seq: str, label: str, layout: GenomeLayout = DEFAULT_LAYOUT) -> None:
    _validate_alphabet(seq, label, layout)
    expected = layout.bp_per_haplotype_chromosome
    if len(seq) != expected:
        raise ValueError(f"{label} 长度必须为 {expected} bp，实际 {len(seq)}")


@dataclass(frozen=True)
class ChromosomePair:
    """两条 homologous chromosomes（各 128 bp ∈ {A,C,G,T}）。"""

    maternal: str
    paternal: str
    layout: GenomeLayout = field(default=DEFAULT_LAYOUT, compare=False, repr=False)

    def __post_init__(self) -> None:
        _validate_sequence(self.maternal, "maternal", self.layout)
        _validate_sequence(self.paternal, "paternal", self.layout)


@dataclass(frozen=True)
class DiploidGenome:
    """二倍体基因组：``pairs[0]`` 承载 A 位点，``pairs[1]`` 承载 B 位点（genome §3）。"""

    pairs: tuple[ChromosomePair, ...]
    genome_id: str = ""
    layout: GenomeLayout = field(default=DEFAULT_LAYOUT, compare=False, repr=False)

    def __post_init__(self) -> None:
        if len(self.pairs) != self.layout.chromosome_pairs:
            raise ValueError(f"DiploidGenome 必须恰有 {self.layout.chromosome_pairs} 对染色体")
        for pair in self.pairs:
            if not isinstance(pair, ChromosomePair):
                raise ValueError("pairs 的元素必须是 ChromosomePair")

    @property
    def maternal_haplotype(self) -> Haplotype:
        return tuple(pair.maternal for pair in self.pairs)

    @property
    def paternal_haplotype(self) -> Haplotype:
        return tuple(pair.paternal for pair in self.pairs)

    @property
    def haploid_bp(self) -> int:
        return self.layout.chromosome_pairs * self.layout.bp_per_haplotype_chromosome

    @property
    def diploid_bp(self) -> int:
        return sum(len(p.maternal) + len(p.paternal) for p in self.pairs)

    def to_dict(self) -> dict:
        """``schemas/genome.schema.json`` 的交换形态；要求非空 ``genome_id``（core §3.1）。"""
        if not self.genome_id:
            raise ValueError("序列化到 schema 边界要求非空 genome_id（core §3.1）")
        return {
            "genome_id": self.genome_id,
            "chromosome_pairs": [
                {"maternal": pair.maternal, "paternal": pair.paternal} for pair in self.pairs
            ],
        }

    @classmethod
    def from_dict(cls, data: dict, *, layout: GenomeLayout = DEFAULT_LAYOUT) -> DiploidGenome:
        items = data["chromosome_pairs"]
        if len(items) != layout.chromosome_pairs:
            raise ValueError(f"chromosome_pairs 必须恰有 {layout.chromosome_pairs} 项")
        pairs = tuple(
            ChromosomePair(item["maternal"], item["paternal"], layout=layout) for item in items
        )
        genome_id = data["genome_id"]
        if not isinstance(genome_id, str) or not genome_id:
            raise ValueError("genome_id 必须是非空字符串（core §3.1）")
        return cls(pairs, genome_id, layout=layout)


# ---------------------------------------------------------------------------
# motif affinity（genome §6；参数单向引用 RGCD §2）
# ---------------------------------------------------------------------------


def hamming_distance(a: str, b: str) -> int:
    if len(a) != len(b):
        raise ValueError("Hamming distance 要求两条序列等长")
    return sum(x != y for x, y in zip(a, b, strict=True))


def motif_affinity(motif: str, window: str) -> np.float32:
    r"""``a(M_k, s) = 1 - d_H(M_k, s) / |M_k|``（genome §6）。"""
    if len(motif) != len(window):
        raise ValueError("窗口须与 motif 等长（RGCD §2: |M_k|=|s|=6）")
    return np.float32(1.0 - hamming_distance(motif, window) / len(motif))


def top_k_mean(values: Sequence[np.float32] | np.ndarray, k: int) -> np.float32:
    """``TopKMean``：对窗口分数取最大的 ``K`` 个的均值（genome §6）。

    ``K`` 超过窗口数时退化为全部窗口的均值。
    """
    arr = np.asarray(values, dtype=np.float32)
    if arr.size == 0:
        raise ValueError("TopKMean 需要至少一个窗口分数")
    if k < 1:
        raise ValueError("TopK 的 K 必须 ≥ 1")
    kk = min(int(k), int(arr.size))
    if kk == arr.size:
        return np.float32(arr.mean(dtype=np.float32))
    top = np.partition(arr, arr.size - kk)[-kk:]
    return np.float32(top.mean(dtype=np.float32))


def window_affinities(sequence: str, motif: str, *, step: int = 1) -> np.ndarray:
    """单链上 motif 等长滑窗的 affinity 序列（窗口不跨染色体，未定义跨链）。"""
    n = len(motif)
    if len(sequence) < n:
        raise ValueError("序列短于 motif，无法扫描窗口")
    if step < 1:
        raise ValueError("滑窗步长必须 ≥ 1")
    starts = range(0, len(sequence) - n + 1, step)
    return np.fromiter(
        (motif_affinity(motif, sequence[i : i + n]) for i in starts),
        dtype=np.float32,
        count=len(starts),
    )


def chain_affinity(
    chain: str,
    motif: str,
    *,
    k: int | None = None,
    step: int = 1,
    layout: GenomeLayout = DEFAULT_LAYOUT,
) -> np.float32:
    r"""单链读出 ``q_k(S) = TopKMean_{s \subset S} a(M_k, s)``（genome §6）。

    ``k=None`` 时取 ``layout.motif_topk``。
    """
    kk = layout.motif_topk if k is None else k
    return top_k_mean(window_affinities(chain, motif, step=step), kk)


def haplotype_affinity(
    haplotype: Haplotype,
    motifs: Sequence[str],
    *,
    k: int | None = None,
    step: int = 1,
    layout: GenomeLayout = DEFAULT_LAYOUT,
) -> np.ndarray:
    r"""单倍型 ``q^{(h)}\in[0,1]^{8}``：窗口取本 haplotype 两条染色体窗口的并集（RGCD §2）。"""
    kk = layout.motif_topk if k is None else k
    out = np.empty(len(motifs), dtype=np.float32)
    for index, motif in enumerate(motifs):
        values = np.concatenate([window_affinities(chain, motif, step=step) for chain in haplotype])
        out[index] = top_k_mean(values, kk)
    return out


def combine_haplotypes(q_h1: np.ndarray, q_h2: np.ndarray, *, mode: str = "additive") -> np.ndarray:
    r"""两条 homolog 的聚合（genome §6）：``additive`` 为 ½(q^{(h1)}+q^{(h2)})。

    ``max`` 为逐分量消融基线（逐 motif 完全显性投影）。
    """
    q1 = np.asarray(q_h1, dtype=np.float32)
    q2 = np.asarray(q_h2, dtype=np.float32)
    if q1.shape != q2.shape:
        raise ValueError("两条 haplotype 的 q 形状必须一致")
    if mode == "additive":
        return ((q1 + q2) / np.float32(2.0)).astype(np.float32)
    if mode == "max":
        return np.maximum(q1, q2).astype(np.float32)
    raise ValueError(f"未知聚合算子 {mode!r}；支持 additive / max")


def genome_affinity(
    genome: DiploidGenome,
    motifs: Sequence[str],
    *,
    k: int | None = None,
    step: int = 1,
    mode: str = "additive",
) -> np.ndarray:
    r"""``q(G)\in[0,1]^{8}``（genome §6，即 RGCD §4 ``B q(G)`` 的输入）。"""
    q_h1 = haplotype_affinity(
        genome.maternal_haplotype, motifs, k=k, step=step, layout=genome.layout
    )
    q_h2 = haplotype_affinity(
        genome.paternal_haplotype, motifs, k=k, step=step, layout=genome.layout
    )
    return combine_haplotypes(q_h1, q_h2, mode=mode)


# ---------------------------------------------------------------------------
# 位点表达 E_A / E_B 与 2×2 架构档（genome §3）
# ---------------------------------------------------------------------------


def locus_expression(
    genome: DiploidGenome,
    motifs: Sequence[str],
    motif_indices: Sequence[int],
    chromosome_pair_index: int,
    *,
    k: int | None = None,
    step: int = 1,
) -> np.float32:
    r"""``E = (1/|K|) Σ_{k∈K} ½[q_k(C^{h1}) + q_k(C^{h2})]``（genome §3，位点限定）。"""
    if not motif_indices:
        raise ValueError("motif 子集 K 不能为空")
    pair_count = genome.layout.chromosome_pairs
    if not 0 <= chromosome_pair_index < pair_count:
        raise ValueError(f"染色体对下标须在 [0, {pair_count})")
    pair = genome.pairs[chromosome_pair_index]
    total = np.float32(0.0)
    for index in motif_indices:
        motif = motifs[index]
        q_maternal = chain_affinity(pair.maternal, motif, k=k, step=step, layout=genome.layout)
        q_paternal = chain_affinity(pair.paternal, motif, k=k, step=step, layout=genome.layout)
        total = np.float32(total + (q_maternal + q_paternal) / np.float32(2.0))
    return np.float32(total / np.float32(len(motif_indices)))


def expression_A(
    genome: DiploidGenome,
    motifs: Sequence[str],
    motif_indices: Sequence[int] | None = None,
    *,
    k: int | None = None,
    step: int = 1,
) -> np.float32:
    """A 位点表达量：只扫 ``pairs[0]``；``motif_indices`` 缺省取 ``layout.motif_subset("A")``。"""
    indices = genome.layout.motif_subset("A") if motif_indices is None else motif_indices
    return locus_expression(genome, motifs, indices, 0, k=k, step=step)


def expression_B(
    genome: DiploidGenome,
    motifs: Sequence[str],
    motif_indices: Sequence[int] | None = None,
    *,
    k: int | None = None,
    step: int = 1,
) -> np.float32:
    """B 位点表达量：只扫 ``pairs[1]``；``motif_indices`` 缺省取 ``layout.motif_subset("B")``。"""
    indices = genome.layout.motif_subset("B") if motif_indices is None else motif_indices
    return locus_expression(genome, motifs, indices, 1, k=k, step=step)


@dataclass(frozen=True)
class Architecture:
    """四类 neural phenotype 的架构档：``high_N × high_H``（genome §3）。"""

    high_N: bool
    high_H: bool

    @property
    def class_label(self) -> str:
        if self.high_N and self.high_H:
            return "A_B_"
        if self.high_N:
            return "A_bb"
        if self.high_H:
            return "aaB_"
        return "aabb"


def architecture(e_a: np.float32, e_b: np.float32, theta_N: float, theta_H: float) -> Architecture:
    """``high_N ⟺ E_A>θ_N``、``high_H ⟺ E_B>θ_H``（genome §3，严格大于）。"""
    for name, theta in (("theta_N", theta_N), ("theta_H", theta_H)):
        if not 0.0 < theta < 0.5:
            raise ValueError(f"{name} 须落在 (0, 0.5)（genome §3 完全显性必要条件），实际 {theta}")
    return Architecture(high_N=bool(e_a > theta_N), high_H=bool(e_b > theta_H))


# ---------------------------------------------------------------------------
# 遗传算子（genome §4/§5）
# ---------------------------------------------------------------------------


def mutate_sequence(
    seq: str, mu: float, rng: np.random.Generator, *, layout: GenomeLayout = DEFAULT_LAYOUT
) -> str:
    r"""SNP mutation：每碱基以 ``μ`` 概率替换（genome §5；替换碱基在其余三种上均匀抽取）。"""
    if not 0.0 <= mu <= 1.0:
        raise ValueError("μ 必须落在 [0, 1]")
    if len(layout.alphabet) < 2:
        raise ValueError("SNP 替换要求 alphabet 至少 2 个符号")
    _validate_alphabet(seq, "序列", layout)
    alphabet = "".join(layout.alphabet)
    out: list[str] = []
    for base in seq:
        if rng.random() < mu:
            alternatives = alphabet.replace(base, "")
            out.append(alternatives[int(rng.integers(0, len(alternatives)))])
        else:
            out.append(base)
    return "".join(out)


def crossover(a: str, b: str, probability: float, rng: np.random.Generator) -> tuple[str, str]:
    """按给定概率发生一次单点 crossover；切点均匀取自内部断点 1..L-1（genome §4 步骤 1–2）。"""
    if len(a) != len(b):
        raise ValueError("同源链必须等长")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("crossover 概率必须落在 [0, 1]")
    if rng.random() >= probability:
        return a, b
    point = 1 + int(rng.random() * (len(a) - 1))
    return a[:point] + b[point:], b[:point] + a[point:]


def meiosis(
    genome: DiploidGenome, crossover_probability: float, rng: np.random.Generator
) -> Gamete:
    """gamete 形成：每对染色体先 crossover，再随机选一条进入 gamete（genome §4 步骤 1–3）。"""
    gamete: list[str] = []
    for pair in genome.pairs:
        recombinant_m, recombinant_p = crossover(
            pair.maternal, pair.paternal, crossover_probability, rng
        )
        gamete.append(recombinant_m if rng.random() < 0.5 else recombinant_p)
    return tuple(gamete)


def make_gamete(
    genome: DiploidGenome,
    mu: float,
    crossover_probability: float,
    crossover_rng: np.random.Generator,
    mutation_rng: np.random.Generator,
    *,
    layout: GenomeLayout | None = None,
) -> Gamete:
    """gamete：crossover/选择，再 SNP mutation（分别用 crossover / mutation 命名空间）。

    ``layout`` 缺省取 ``genome.layout``。
    """
    active_layout = genome.layout if layout is None else layout
    base_gamete = meiosis(genome, crossover_probability, crossover_rng)
    return tuple(
        mutate_sequence(chromosome, mu, mutation_rng, layout=active_layout)
        for chromosome in base_gamete
    )


def fertilize(
    gamete_a: Gamete, gamete_b: Gamete, *, layout: GenomeLayout = DEFAULT_LAYOUT
) -> DiploidGenome:
    """``gamete_A + gamete_B → offspring``（genome §4 / evolution §3）。"""
    if len(gamete_a) != layout.chromosome_pairs or len(gamete_b) != layout.chromosome_pairs:
        raise ValueError(f"gamete 必须含 {layout.chromosome_pairs} 条染色体")
    pairs = tuple(
        ChromosomePair(a, b, layout=layout) for a, b in zip(gamete_a, gamete_b, strict=True)
    )
    return DiploidGenome(pairs, layout=layout)
