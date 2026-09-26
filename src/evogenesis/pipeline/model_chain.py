"""模型链装配：`config → motif 目录 → 初始种群 → q(G) → 发育 → DanioNet → (ω,v)`。

owner：`pipeline/模型链装配.md`。上游：`core`（seed / ids）、`genome`、`development`、
`connectome`。本模块**只做编排**：不新造数值、不定义算法、不复制各模块契约。

本期范围：把 `configs/default_model.yaml` 一路跑到 DanioNet 动作 `(ω, v)`。
Arena 驱动、逐代演化、BC 与 run 落盘均**未接**（见 owner 文档「未接」）。
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass

from evogenesis.connectome.config import (
    DEFAULT_NETWORK_CONFIG,
    NetworkReadoutConfig,
    load_network_config,
)
from evogenesis.connectome.danionet import DanioNet
from evogenesis.core.ids import mint_id
from evogenesis.core.seed import SeedManager
from evogenesis.development.config import DEFAULT_CONFIG as DEFAULT_RGCD_CONFIG
from evogenesis.development.config import RGCDConfig, load_development_config
from evogenesis.development.rgcd import ConnectomePhenotype, develop
from evogenesis.genome.config import DEFAULT_LAYOUT, GenomeLayout, load_genome_config
from evogenesis.genome.genome import DiploidGenome, genome_affinity, random_genome
from evogenesis.genome.motifs import motif_catalog_for


@dataclass(frozen=True)
class ModelChainConfig:
    """模型链三段配置（`default_model.yaml` 的 `genome` / `grn`+`development` / `network` 节）。"""

    layout: GenomeLayout
    rgcd: RGCDConfig
    network: NetworkReadoutConfig


def load_model_chain_config(
    path: str | os.PathLike[str] | None = None,
) -> ModelChainConfig:
    """读 `configs/default_model.yaml`；`path=None` 时取各模块的冻结镜像默认值。"""
    return ModelChainConfig(
        layout=load_genome_config(path),
        rgcd=load_development_config(path),
        network=load_network_config(path),
    )


@dataclass(frozen=True)
class Individual:
    """generation 0 个体：稳定 `genome_id`（`core §3.1`）+ 二倍体 genome。"""

    genome_id: str
    genome: DiploidGenome


def initial_population(
    *,
    master_seed: int,
    experiment_id: str,
    n: int,
    layout: GenomeLayout = DEFAULT_LAYOUT,
) -> tuple[Individual, ...]:
    """generation 0 种群：均匀 i.i.d. 基因组（`genome §2`；`initial_population` 命名空间）。"""
    if n < 1:
        raise ValueError("n 必须 ≥ 1")
    manager = SeedManager(master_seed)
    individuals: list[Individual] = []
    for index in range(n):
        genome_id = mint_id(experiment_id, "genome", 0, index)
        genome = random_genome(
            layout, rng=manager.spawn_rng("initial_population", index), genome_id=genome_id
        )
        individuals.append(Individual(genome_id=genome_id, genome=genome))
    return tuple(individuals)


def motif_catalog(master_seed: int, layout: GenomeLayout = DEFAULT_LAYOUT) -> tuple[str, ...]:
    """实验级固定 motif 目录（`genome §6`；`motif_catalog` 命名空间）。"""
    return motif_catalog_for(master_seed, layout)


def phenotype_of(
    genome: DiploidGenome,
    motifs: Sequence[str],
    *,
    master_seed: int,
    index: int,
    config: RGCDConfig = DEFAULT_RGCD_CONFIG,
    device: str = "cpu",
) -> ConnectomePhenotype:
    """单个体：`q(G)=genome_affinity` → `develop`（`RGCD数学模型.md` §1–§11）。"""
    q = genome_affinity(genome, motifs)
    return develop(q, master_seed=master_seed, index=index, config=config, device=device)


def phenotypes_of(
    individuals: Sequence[Individual],
    motifs: Sequence[str],
    *,
    master_seed: int,
    config: RGCDConfig = DEFAULT_RGCD_CONFIG,
    device: str = "cpu",
) -> list[ConnectomePhenotype]:
    """批量发育：`index` 取个体在种群中的稳定序号（不得用调用顺序，`core §3`）。"""
    return [
        phenotype_of(
            individual.genome,
            motifs,
            master_seed=master_seed,
            index=index,
            config=config,
            device=device,
        )
        for index, individual in enumerate(individuals)
    ]


def danionet_of(
    phenotypes: Sequence[ConnectomePhenotype],
    *,
    master_seed: int,
    config: NetworkReadoutConfig = DEFAULT_NETWORK_CONFIG,
    device: str = "cpu",
) -> DanioNet:
    """由发育产物构造 `DanioNet`（batch = len(phenotypes)）。"""
    return DanioNet(list(phenotypes), master_seed=master_seed, config=config, device=device)
