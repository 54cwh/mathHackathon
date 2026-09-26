"""Demo checkpoint 冻结/加载 round-trip（`pipeline/模型链装配.md` §6）。"""

from __future__ import annotations

from pathlib import Path

import torch

from evogenesis.experiment.freeze_run import freeze_demo_checkpoint
from evogenesis.pipeline import load_demo_checkpoint

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "configs" / "default_model.yaml"
ARENA = ROOT / "configs" / "default_arena.yaml"


def _freeze(out: Path) -> Path:
    return freeze_demo_checkpoint(
        out_dir=out,
        model_config_path=MODEL,
        arena_config_path=ARENA,
        experiment_id="demo-test",
        master_seed=250927,
        n=12,
        train=False,
    )


def test_checkpoint_roundtrip(tmp_path: Path) -> None:
    path = _freeze(tmp_path)
    ck = load_demo_checkpoint(path)
    assert ck.master_seed == 250927
    assert ck.trained is False
    assert ck.individuals, "至少一个 viable 个体"
    assert (tmp_path / "population.json").exists()
    net = ck.build_net()
    assert len(net.n_neurons) == len(ck.individuals)
    for slot, ind in enumerate(ck.individuals):
        assert torch.equal(net.theta.data[slot].cpu(), ind.trained_theta.cpu())


def test_checkpoint_deterministic(tmp_path: Path) -> None:
    first = load_demo_checkpoint(_freeze(tmp_path / "a"))
    second = load_demo_checkpoint(_freeze(tmp_path / "b"))
    assert [i.genome_id for i in first.individuals] == [i.genome_id for i in second.individuals]
    for left, right in zip(first.individuals, second.individuals, strict=True):
        assert torch.equal(left.phenotype.weights0, right.phenotype.weights0)
        assert torch.equal(left.trained_theta, right.trained_theta)
