"""基因组布局参数：取值 owner 为 ``configs/default_model.yaml`` 的 ``genome`` 节。

本模块**不新造数值**：``GenomeLayout`` 的默认值是冻结配置的镜像，由
``tests/test_genome_config.py`` 的漂移守护测试断言与配置文件逐字段一致；
运行期用 ``load_genome_config()`` 经 ``core`` 的 ``load_config`` 读取真实配置注入。
参数依据与状态见 ``docs/参数总表.json``（``group=genome``）。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evogenesis.core.config import GenomeConfig, ModelConfig, load_config

# 仓库根 = 本文件 ``src/evogenesis/genome/config.py`` 的上溯第 3 级。
DEFAULT_MODEL_CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "default_model.yaml"


@dataclass(frozen=True)
class GenomeLayout:
    """二倍体布局与 motif 读出参数（镜像 ``configs/default_model.yaml`` 的 ``genome`` 节）。"""

    chromosome_pairs: int = 2
    bp_per_haplotype_chromosome: int = 128
    alphabet: tuple[str, ...] = ("A", "C", "G", "T")
    motif_count: int = 8
    motif_length: int = 6
    motif_topk: int = 3
    motif_subset_A: int = 0
    motif_subset_B: int = 1

    def __post_init__(self) -> None:
        for locus, index in (("A", self.motif_subset_A), ("B", self.motif_subset_B)):
            if not 0 <= index < self.motif_count:
                raise ValueError(
                    f"motif_subset_{locus} 须落在 [0, {self.motif_count})，实际 {index}"
                )
        if self.motif_subset_A == self.motif_subset_B:
            raise ValueError("K_A 与 K_B 必须互斥（genome §3）")

    @property
    def haploid_bp(self) -> int:
        return self.chromosome_pairs * self.bp_per_haplotype_chromosome

    @property
    def diploid_bp(self) -> int:
        return 2 * self.haploid_bp

    def motif_subset(self, locus: str) -> tuple[int, ...]:
        """位点 K_A / K_B 的 motif 索引元组（genome §3；MVP 单元素）。"""
        if locus == "A":
            return (self.motif_subset_A,)
        if locus == "B":
            return (self.motif_subset_B,)
        raise ValueError(f"未知位点 {locus!r}；支持 'A' / 'B'")

    @classmethod
    def from_config(cls, cfg: GenomeConfig) -> GenomeLayout:
        return cls(
            chromosome_pairs=cfg.chromosome_pairs,
            bp_per_haplotype_chromosome=cfg.bp_per_haplotype_chromosome,
            alphabet=tuple(cfg.alphabet),
            motif_count=cfg.motif_count,
            motif_length=cfg.motif_length,
            motif_topk=cfg.motif_topk,
            motif_subset_A=cfg.motif_subset_A,
            motif_subset_B=cfg.motif_subset_B,
        )


DEFAULT_LAYOUT = GenomeLayout()


def load_genome_config(
    path: str | os.PathLike[str] | None = DEFAULT_MODEL_CONFIG_PATH,
    *,
    overrides: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> GenomeLayout:
    """按 ``CLI > env > file > default`` 读取 ``genome`` 节并转为 ``GenomeLayout``。

    默认读 ``configs/default_model.yaml``；``path=None`` 时只用 ``GenomeLayout`` 的
    默认值（冻结配置的镜像），便于离线与单测。``overrides`` 形状同 YAML（按节嵌套，
    如 ``{"genome": {"motif_topk": 5}}``）。
    """
    if path is None:
        return GenomeLayout()
    cfg: ModelConfig = load_config(path, overrides=overrides, environ=environ)
    return GenomeLayout.from_config(cfg.genome)
