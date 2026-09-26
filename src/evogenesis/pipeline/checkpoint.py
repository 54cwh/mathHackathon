"""Demo checkpoint 的**格式与加载**（`模型链装配.md` §6；`artifacts/demo/`）。

owner：`pipeline/模型链装配.md` §6。本模块只做「格式 / 序列化 / 重建」：不新造数值、不训练。
**生成**（含 BC 训练）在 `experiment/freeze_run.py`（消费 `collect` + `learning_run`），由
`scripts/freeze_checkpoint.py` 调用——保持 `pipeline` 不反向依赖 `experiment`/`learning`
（`模型链装配.md` §5）。

reload 契约：由 `phenotype` 经 `danionet_of` 重建网络，再以 `trained_theta` 覆盖 `Θ`
（`connectome §3`：`W⁰`/支撑/先验同构，唯 `Θ` 不同）。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import torch

from evogenesis.connectome.config import DEFAULT_NETWORK_CONFIG, NetworkReadoutConfig
from evogenesis.development.rgcd import ConnectomePhenotype
from evogenesis.pipeline.model_chain import danionet_of

CHECKPOINT_VERSION = 1
CHECKPOINT_FILENAME = "checkpoint_v1.pt"
POPULATION_FILENAME = "population.json"

_PHENO_TENSOR_KEYS = ("adjacency", "weights0", "tau", "cell_type", "positions", "active_mask", "z")


@dataclass(frozen=True)
class DemoIndividual:
    """Demo checkpoint 中一个 viable 个体。"""

    genome_id: str
    fish_id: str
    phenotype: ConnectomePhenotype
    trained_theta: torch.Tensor
    final_loss: float
    delta_w_norm: float


@dataclass(frozen=True)
class DemoCheckpoint:
    """加载后的 Demo checkpoint（`模型链装配.md` §6）。"""

    format_version: int
    master_seed: int
    experiment_id: str
    trained: bool
    individuals: tuple[DemoIndividual, ...]

    def build_net(
        self,
        *,
        config: NetworkReadoutConfig = DEFAULT_NETWORK_CONFIG,
        device: str = "cpu",
    ) -> torch.nn.Module:
        """按 checkpoint 重建 `DanioNet`（batch = 个体数），`Θ` 用 `trained_theta`。"""
        net = danionet_of(
            [ind.phenotype for ind in self.individuals],
            master_seed=self.master_seed,
            config=config,
            device=device,
        )
        with torch.no_grad():
            for slot, ind in enumerate(self.individuals):
                net.theta.data[slot].copy_(ind.trained_theta.to(device=device))
        return net


def _phenotype_to_dict(phenotype: ConnectomePhenotype) -> dict:
    payload = {key: getattr(phenotype, key).detach().cpu() for key in _PHENO_TENSOR_KEYS}
    payload["viable"] = bool(phenotype.viable)
    payload["viability_reason"] = str(phenotype.viability_reason)
    return payload


def _dict_to_phenotype(payload: dict) -> ConnectomePhenotype:
    return ConnectomePhenotype(
        adjacency=payload["adjacency"],
        weights0=payload["weights0"],
        tau=payload["tau"],
        cell_type=payload["cell_type"],
        positions=payload["positions"],
        active_mask=payload["active_mask"],
        viable=bool(payload["viable"]),
        viability_reason=str(payload["viability_reason"]),
        z=payload["z"],
    )


def save_demo_checkpoint(
    out_dir: str | os.PathLike[str],
    *,
    master_seed: int,
    experiment_id: str,
    individuals: list[DemoIndividual],
    population_manifest: dict,
    trained: bool,
    created_at: str,
    git_commit: str,
) -> Path:
    """写 `checkpoint_v1.pt` + `population.json`，返回 checkpoint 路径（`§6`）。"""
    if not individuals:
        raise ValueError("checkpoint 至少需要一个个体")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "format_version": CHECKPOINT_VERSION,
        "created_at": created_at,
        "git_commit": git_commit,
        "master_seed": int(master_seed),
        "experiment_id": str(experiment_id),
        "trained": bool(trained),
        "individuals": [
            {
                "genome_id": ind.genome_id,
                "fish_id": ind.fish_id,
                "phenotype": _phenotype_to_dict(ind.phenotype),
                "trained_theta": ind.trained_theta.detach().cpu(),
                "final_loss": float(ind.final_loss),
                "delta_w_norm": float(ind.delta_w_norm),
            }
            for ind in individuals
        ],
    }
    checkpoint_path = out / CHECKPOINT_FILENAME
    torch.save(payload, checkpoint_path)
    (out / POPULATION_FILENAME).write_text(
        json.dumps(population_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return checkpoint_path


def load_demo_checkpoint(path: str | os.PathLike[str]) -> DemoCheckpoint:
    """读 `checkpoint_v1.pt`（`weights_only=True`，仅 tensor/基本类型）。"""
    raw = torch.load(Path(path), map_location="cpu", weights_only=True)
    if int(raw.get("format_version", -1)) != CHECKPOINT_VERSION:
        raise ValueError(
            f"checkpoint format_version 非 {CHECKPOINT_VERSION}：{raw.get('format_version')!r}"
        )
    individuals = tuple(
        DemoIndividual(
            genome_id=item["genome_id"],
            fish_id=item["fish_id"],
            phenotype=_dict_to_phenotype(item["phenotype"]),
            trained_theta=item["trained_theta"],
            final_loss=float(item["final_loss"]),
            delta_w_norm=float(item["delta_w_norm"]),
        )
        for item in raw["individuals"]
    )
    return DemoCheckpoint(
        format_version=int(raw["format_version"]),
        master_seed=int(raw["master_seed"]),
        experiment_id=str(raw["experiment_id"]),
        trained=bool(raw["trained"]),
        individuals=individuals,
    )
