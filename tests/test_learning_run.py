"""`experiment/learning_run.py` 产物组装（`experiment §3.8/§5.1`；schema 见同目录 schemas/）。"""

from __future__ import annotations

from types import SimpleNamespace

from evogenesis.experiment.learning_run import learning_records, learning_summary


def _result():
    ind = SimpleNamespace(fish_id="exp:g0:fish0000", genome_id="exp:g0:genome0000")
    ind2 = SimpleNamespace(fish_id="exp:g0:fish0001", genome_id="exp:g0:genome0001")
    train = SimpleNamespace(final_loss=0.25, loss_weights=SimpleNamespace(omega=0.4, v=1.6))
    report = SimpleNamespace(
        flip_rate=0.1,
        spectral_radius=(0.9,),
        n_updates=20,
        epochs=6.4,
        coverage_steps=6.4,
        visible_steps=768000,
    )
    return SimpleNamespace(
        sign_constrained=True,
        n_individuals=12,
        n_viable=2,
        mean_final_loss=0.25,
        viable_individuals=(ind, ind2),
        reports=(report, report),
        train_results=(train, train),
        delta_w_norm=(0.01, 0.02),
        noninheritance=SimpleNamespace(fresh_delta_w_max_abs=0.0, weights0_max_abs_diff=0.0),
    )


def test_learning_records_are_per_individual():
    records = learning_records(_result())
    assert len(records) == 2
    assert records[0]["spectral_radius"] == 0.9  # 标量（逐个体），非全体列表
    assert isinstance(records[1]["flip_rate"], float)
    assert records[1]["fish_id"] == "exp:g0:fish0001"


def test_learning_summary_fields_and_noninheritance():
    summary = learning_summary(_result(), seed=1103)
    assert summary["seed"] == 1103
    assert summary["n_viable"] == 2
    assert summary["noninheritance"] == {
        "fresh_delta_w_max_abs": 0.0,
        "weights0_max_abs_diff": 0.0,
    }
