"""Demo checkpoint 生成（`pipeline/模型链装配.md` §6；`artifacts/demo/`）。

编排「种群 → 发育 → viable →（可选）Stage-1 采集 + Stage-2 BC 训练 → 冻结」。本模块只编排：
训练契约 `learning §3`、发育 `RGCD §1–§11`、格式/加载 owner = `pipeline/checkpoint.py`。
放在 `experiment/` 是因为它消费 `collect` / `learning_run`（`pipeline` 不反向依赖二者，
`模型链装配.md` §5）。薄 CLI = `scripts/freeze_checkpoint.py`。
"""

from __future__ import annotations

import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from evogenesis.arena.config import load_arena_config
from evogenesis.core.seed import SeedManager
from evogenesis.experiment import collect
from evogenesis.experiment.environments import BASELINE, load_environment
from evogenesis.experiment.learning_run import load_learning_config, run_lifetime_learning
from evogenesis.pipeline import (
    danionet_of,
    initial_population,
    load_model_chain_config,
    motif_catalog,
    phenotypes_of,
)
from evogenesis.pipeline.checkpoint import DemoIndividual, save_demo_checkpoint

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def freeze_demo_checkpoint(
    *,
    out_dir: str | Path,
    model_config_path: str | Path,
    arena_config_path: str | Path,
    experiment_id: str,
    master_seed: int,
    n: int = 12,
    train: bool = True,
    steps: int | None = None,
    environment: str = BASELINE,
    device: str = "cpu",
) -> Path:
    """生成 `artifacts/demo/{checkpoint_v1.pt,population.json}`，返回 checkpoint 路径。

    ``train=True`` 时跑 Stage-1 采集 + Stage-2 BC（`experiment §3.8`），冻结**训练后** `Θ`；
    ``train=False`` 只冻结未训练网络（快速路径/测试）。
    """
    env_overrides = None if environment == BASELINE else load_environment(environment)
    arena_config = load_arena_config(arena_config_path, overrides=env_overrides)
    chain = load_model_chain_config(model_config_path)

    population = initial_population(
        master_seed=master_seed, experiment_id=experiment_id, n=n, layout=chain.layout
    )
    motifs = motif_catalog(master_seed, chain.layout)
    phenotypes = phenotypes_of(
        population, motifs, master_seed=master_seed, config=chain.rgcd, device=device
    )
    viable = [(i, population[i], phenotypes[i]) for i in range(n) if phenotypes[i].viable]
    if not viable:
        raise ValueError(f"master_seed={master_seed} 下无 viable 个体，无法冻结 checkpoint")

    if train:
        with tempfile.TemporaryDirectory() as tmp:
            count = collect.default_trajectories(Path(model_config_path))
            collect.collect_trajectories(
                arena_config,
                experiment_id=experiment_id,
                environment_id=environment,
                generation=0,
                seed=SeedManager(master_seed).seed("arena_spawn", 0),
                trajectories=count,
                out_dir=tmp,
            )
            result = run_lifetime_learning(
                experiment_id=experiment_id,
                master_seed=master_seed,
                chain=chain,
                arena_config=arena_config,
                learning_config=load_learning_config(Path(model_config_path)),
                trajectories_dir=tmp,
                generation=0,
                n=n,
                steps=steps,
                device=device,
            )
        thetas = [theta[0].detach() for theta in result.trained_thetas]
        losses = [r.final_loss for r in result.train_results]
        deltas = list(result.delta_w_norm)
        if len(thetas) != len(viable):
            raise ValueError(f"训练个体数 {len(thetas)} 与 viable 数 {len(viable)} 不一致")
    else:
        thetas = [
            danionet_of([ph], master_seed=master_seed, config=chain.network, device=device)
            .theta.detach()[0]
            .clone()
            for _, _, ph in viable
        ]
        losses = [0.0] * len(viable)
        deltas = [0.0] * len(viable)

    individuals = [
        DemoIndividual(
            genome_id=individual.genome_id,
            fish_id=individual.fish_id,
            phenotype=phenotype,
            trained_theta=theta.detach().cpu(),
            final_loss=loss,
            delta_w_norm=delta,
        )
        for (_, individual, phenotype), theta, loss, delta in zip(
            viable, thetas, losses, deltas, strict=True
        )
    ]
    manifest = {
        "master_seed": int(master_seed),
        "experiment_id": experiment_id,
        "n_fish": int(n),
        "viable_indices": [index for index, _, _ in viable],
        "genome_ids": [individual.genome_id for _, individual, _ in viable],
    }
    return save_demo_checkpoint(
        out_dir,
        master_seed=master_seed,
        experiment_id=experiment_id,
        individuals=individuals,
        population_manifest=manifest,
        trained=train,
        created_at=datetime.now(UTC).isoformat(),
        git_commit=_git_commit(),
    )
