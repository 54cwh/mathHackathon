"""Arena 实验驱动器：跑 seeds × 600 步，落盘 `实验与评价体系.md` §11 要求的产物。

每个 seed 一个 run 目录（`<experiment_id>-s<seed>`），目录布局由 `scripts/run_experiment.py`
创建（它是 run 目录布局的唯一 owner；本脚本只负责补 Arena 侧产物）：

```text
results/runs/<experiment_id>-s<seed>/
  metadata.json               (由 run_experiment.py 写)
  arena_config_resolved.json  (由 run_experiment.py 写：实际生效的 ArenaConfig 快照)
  config_snapshot/  seed.txt  git_commit.txt
  metrics.csv                 逐个体一行：指标 + 原始计数
  population.jsonl            逐个体一行：轨迹幅度等，供作图
  episodes.jsonl              逐 episode 一行：事件计数 + 吞吐
  seed_summary.json           逐 seed 的个体等权均值
```

跨 seed 的 mean ± std 写到 `results/tables/<experiment_id>_summary.json`（口径见
`experiment/metrics.py` 模块 docstring）。

用法：

    .venv/Scripts/python.exe scripts/run_arena.py --experiment-id exp1
    .venv/Scripts/python.exe scripts/run_arena.py --experiment-id exp1 --seeds 1103,2207

注意：`experiment_id` 必须唯一（沿用 `run_experiment.py` 的契约）；已存在时报错退出。
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

from evogenesis.arena.config import load_arena_config
from evogenesis.arena.env import DanioArena
from evogenesis.arena.policies import ExpertPolicy
from evogenesis.experiment.metrics import (
    aggregate_by_seed,
    episode_metrics,
    summarise_over_seeds,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEEDS = "1103,2207,3301"  # configs/experiment_seeds.yaml
EVENT_KEYS = (
    "arena.prey_captured",
    "arena.fish_captured",
    "arena.collision",
    "arena.escape",
    "arena.energy_depleted",
    "arena.spawn",
)
METRIC_COLUMNS = (
    "survival_steps",
    "captures",
    "capture_attempts",
    "encounters",
    "predator_encounters",
    "escape_successes",
    "collisions",
    "energy_final",
    "survival",
    "prey_capture",
    "escape_success",
    "energy_efficiency",
    "composite_fitness",
)


def create_run_dir(experiment_id: str, config: str, seed: int) -> Path:
    """委托 `run_experiment.py` 建目录（布局唯一 owner），返回运行目录。"""
    script = ROOT / "scripts" / "run_experiment.py"
    cmd = [
        sys.executable,
        str(script),
        "--config",
        config,
        "--seed",
        str(seed),
        "--experiment-id",
        experiment_id,
    ]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise SystemExit(
            "run_experiment.py 建目录失败（experiment_id 需唯一）："
            + (proc.stderr.strip() or proc.stdout.strip())
        )
    return ROOT / "results" / "runs" / experiment_id


def run_episode(cfg_path: Path, seed: int, steps: int) -> tuple[dict[str, dict], list, float]:
    """跑一局，返回 (每鱼记录, 事件列表, 墙钟秒)。"""
    cfg = load_arena_config(cfg_path)
    arena = DanioArena(cfg, master_seed=seed)
    arena.reset()
    expert = ExpertPolicy()
    t0 = time.perf_counter()
    for _ in range(steps):
        alive = [(fid, f) for fid, f in arena.fish.items() if f.alive]
        actions = {fid: expert(arena.observe(fid)) for fid, _ in alive}
        arena.step(actions)
    elapsed = time.perf_counter() - t0
    return arena.per_fish_log(), list(arena.events), elapsed


def write_metrics_csv(run_dir: Path, rows: list[dict]) -> None:
    fields = ["seed", "fish_id", *METRIC_COLUMNS]
    with (run_dir / "metrics.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k) for k in fields})


def _population_record(seed: int, fid: str, rec: dict) -> dict:
    energy = rec.get("energy_trajectory") or []
    size = rec.get("size_trajectory") or []
    return {
        "seed": seed,
        "fish_id": fid,
        "generation": rec.get("generation"),
        "survival_steps": rec.get("survival_steps"),
        "captures": rec.get("captures"),
        "encounters": rec.get("encounters"),
        "predator_encounters": rec.get("predator_encounters"),
        "escape_successes": rec.get("escape_successes"),
        "collisions": rec.get("collisions"),
        "energy_first": energy[0] if energy else None,
        "energy_last": energy[-1] if energy else None,
        "energy_min": min(energy) if energy else None,
        "size_first": size[0] if size else None,
        "size_last": size[-1] if size else None,
        "n_motor_commands": len(rec.get("motor_commands") or []),
    }


def write_population(run_dir: Path, seed: int, per_fish: dict[str, dict]) -> None:
    with (run_dir / "population.jsonl").open("w", encoding="utf-8", newline="") as fh:
        for fid, rec in sorted(per_fish.items()):
            row = _population_record(seed, fid, rec)
            fh.write(json.dumps(row, ensure_ascii=False) + chr(10))


def episode_row(
    seed: int, events: list, per_fish: dict[str, dict], steps: int, elapsed: float
) -> dict:
    counts = {k: 0 for k in EVENT_KEYS}
    for ev in events:
        if ev.type in counts:
            counts[ev.type] += 1
    row = {"seed": seed, "steps": steps, "steps_per_s": round(steps / elapsed, 1)}
    for k in EVENT_KEYS:
        row[k.replace("arena.", "")] = counts[k]
    row["fish_alive_end"] = sum(1 for r in per_fish.values() if r["survival_steps"] >= steps)
    row["n_events_total"] = len(events)
    return row


def _dump(path: Path, payload: dict, *, indent: int | None = None) -> None:
    path.write_text(
        json.dumps(payload, indent=indent, ensure_ascii=False) + chr(10),
        encoding="utf-8",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Arena episodes for an experiment.")
    parser.add_argument(
        "--experiment-id",
        required=True,
        help="稳定实验 ID；run 目录为 results/runs/<id>-s<seed>/",
    )
    parser.add_argument("--config", default="configs/default_arena.yaml")
    parser.add_argument("--seeds", default=DEFAULT_SEEDS, help="逗号分隔；见 experiment_seeds.yaml")
    parser.add_argument("--steps", type=int, default=None, help="默认取 world.episode_steps")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        cfg_path = ROOT / cfg_path
    cfg = load_arena_config(cfg_path)
    steps = args.steps if args.steps is not None else cfg.world.episode_steps
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    e_max = cfg.energy.e_max

    all_rows: list[dict] = []
    seed_rows: list[dict] = []
    for seed in seeds:
        run_id = f"{args.experiment_id}-s{seed}"
        run_dir = create_run_dir(run_id, args.config, seed)
        per_fish, events, elapsed = run_episode(cfg_path, seed, steps)
        rows = [
            {
                "seed": seed,
                "fish_id": fid,
                **episode_metrics(rec, episode_steps=steps, e_max=e_max),
            }
            for fid, rec in sorted(per_fish.items())
        ]
        write_metrics_csv(run_dir, rows)
        write_population(run_dir, seed, per_fish)
        _dump(run_dir / "episodes.jsonl", episode_row(seed, events, per_fish, steps, elapsed))
        by_seed = aggregate_by_seed(rows)
        _dump(run_dir / "seed_summary.json", by_seed, indent=2)
        all_rows.extend(rows)
        seed_rows.extend(by_seed)
        print(f"[{run_id}] {steps} 步 / {len(rows)} 个体 / {elapsed:.1f}s")

    summary = summarise_over_seeds(seed_rows)
    tables = ROOT / "results" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    out = tables / f"{args.experiment_id}_summary.json"
    _dump(
        out,
        {
            "experiment_id": args.experiment_id,
            "seeds": seeds,
            "steps": steps,
            "n_individuals": len(all_rows),
            "per_metric": summary,
        },
        indent=2,
    )
    print()
    print(f"跨 seed 汇总（n={len(seeds)}）→ {out.relative_to(ROOT)}")
    for m, st in summary.items():
        mean = st["mean"]
        mean_s = "None" if mean is None else format(mean, ".6g")
        std_s = "None" if st["std"] is None else format(st["std"], ".6g")
        print(f"  {m:20s} mean={mean_s}  std={std_s}  n={st['n']}")


if __name__ == "__main__":
    main()
