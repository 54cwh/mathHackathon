"""Arena 实验驱动器（**ExpertPolicy 驱动**：环境 pre-check / 基线）：跑 seeds × 600 步，落盘产物。

驱动方分工（`experiment §3.3`、`learning §5`）：本脚本用 `ExpertPolicy`；
**模型评估**（BC/DanioNet）用 `scripts/run_chain.py`（DanioNet 驱动），
本脚本不用于模型评估。规模：默认 `n_fish=12`（Live/ExpertPolicy）。

每个 seed 一个 run 目录（`<experiment_id>-s<seed>`），目录布局由
`experiment/runlayout.py::create_run_dir` 创建（它是 run 目录布局的唯一实现；本脚本只负责
补 Arena 侧产物）：

```text
results/runs/<experiment_id>-s<seed>/
  metadata.json               (由 runlayout 写)
  behavior_trace/             (仅在 --emit-behavior-trace 时写：整群逐 step 行为回放，
                               episode_<id>.jsonl，契约见 schemas/behavior_trace.schema.json；
                               **不是** BC 数据——单鱼 BC 轨迹由 scripts/collect_trajectories.py 写)
  arena_config_resolved.json  (由 runlayout 写：实际生效的 ArenaConfig 快照)
  config_snapshot/  seed.txt  git_commit.txt
  metrics.csv                 逐个体一行：指标 + 原始计数
  population.jsonl            逐个体一行：轨迹幅度等，供作图
  episodes.jsonl              逐 episode 一行：事件计数 + 吞吐
  events.jsonl                arena 事件日志：首行 header + 逐条事件
                              (由 scripts/run_arena.py 写；落盘业务逻辑 owner =
                               experiment/events.py；格式 owner = core §5.1 / arena §18.4)
  seed_summary.json           逐 seed 的个体等权均值
```

跨 seed 的 mean ± std 写到 `results/tables/<experiment_id>_summary.json`（口径见
`experiment/metrics.py` 模块 docstring）。

用法：

    .venv/Scripts/python.exe scripts/run_arena.py --experiment-id exp1
    .venv/Scripts/python.exe scripts/run_arena.py --experiment-id exp1 --seeds 1103,2207
    .venv/Scripts/python.exe scripts/run_arena.py --experiment-id exp1 --emit-behavior-trace

注意：`experiment_id` 必须唯一（沿用 `run_experiment.py` 的契约）；已存在时报错退出。
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from evogenesis.arena.config import load_arena_config
from evogenesis.arena.env import DanioArena
from evogenesis.arena.policies import ExpertPolicy
from evogenesis.core.ids import mint_id
from evogenesis.core.seed import SeedManager
from evogenesis.evolution.config import load_evolution_config
from evogenesis.experiment import runlayout
from evogenesis.experiment.arena_rollout import expert_rollout
from evogenesis.experiment.behavior_trace import (
    TraceCollector,
    trace_header,
    write_trace,
)
from evogenesis.experiment.environments import load_environment
from evogenesis.experiment.events import episode_event_header, write_event_log
from evogenesis.experiment.metrics import (
    aggregate_by_seed,
    episode_metrics,
    summarise_over_seeds,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEEDS = "1103,2207,3301"  # configs/experiment_seeds.yaml
EVENT_KEYS = (
    "arena.spawn",
    "arena.capture_attempt",
    "arena.prey_captured",
    "arena.collision",
    "arena.escape",
    "arena.energy_depleted",
    "arena.fish_captured",
    "arena.episode_end",
)
METRIC_COLUMNS = (
    "survival_steps",
    "captures",
    "capture_attempts",  # 诊断列（§2.1 分母为 encounters）
    "encounters",
    "predator_encounters",
    "escape_successes",
    "collisions",
    "energy_final",
    "survival",
    "capture_rate",
    "prey_capture",
    "escape_success",
    "energy_efficiency",
    "composite_fitness",
)


def create_run_dir(
    experiment_id: str, config: str, seed: int, overrides: dict | None = None
) -> Path:
    """经布局 owner `experiment/runlayout.py` 建目录，返回 `<experiment_id>-s<seed>/`。"""
    return runlayout.create_run_dir(
        experiment_id=experiment_id,
        seed=seed,
        config_path=config,
        overrides=overrides,
    )


@dataclass(frozen=True)
class ArenaRunResult:
    """一局 ExpertPolicy run 的产物（供 run_arena 落盘）。"""

    per_fish: dict[str, dict]
    events: list
    elapsed: float
    trace: list[dict]
    done: bool
    steps_run: int
    fish_ids: list[str]
    spawn_seed: int
    dynamics_seed: int


def run_episode(
    cfg_path: Path,
    seed: int,
    steps: int,
    overrides: dict | None = None,
    emit_behavior_trace: bool = False,
    experiment_id: str = "run",
    generation: int = 0,
) -> ArenaRunResult:
    """跑一局，返回逐鱼记录/事件/墙钟/整群 trace。

    驱动循环走 `experiment/arena_rollout.py::expert_rollout`（与 BC 采集共用）。
    整群 trace 只在 `emit_behavior_trace=True` 时收集；死鱼止步（无观测即无记录）。
    """
    cfg = load_arena_config(cfg_path, overrides=overrides)
    fish_ids = [mint_id(experiment_id, "fish", generation, i) for i in range(cfg.population.n_fish)]
    genome_ids = [
        mint_id(experiment_id, "genome", generation, i) for i in range(cfg.population.n_fish)
    ]
    manager = SeedManager(seed)
    spawn_seed = manager.seed("arena_spawn", 0)
    dynamics_seed = manager.seed("arena_dynamics", 0)
    arena = DanioArena(
        cfg,
        spawn_seed=spawn_seed,
        dynamics_seed=dynamics_seed,
        fish_ids=fish_ids,
        genome_ids=genome_ids,
        generation=generation,
    )
    arena.reset()
    expert = ExpertPolicy()
    collector = TraceCollector(arena) if emit_behavior_trace else None
    done = False
    steps_run = 0
    t0 = time.perf_counter()
    for rollout in expert_rollout(arena, steps=steps, expert=expert):
        if collector is not None:
            collector.add(rollout)
        done = rollout.done
        steps_run = rollout.step + 1
    trace = collector.records() if collector is not None else []
    elapsed = time.perf_counter() - t0
    return ArenaRunResult(
        per_fish=arena.per_fish_log(),
        events=list(arena.events),
        elapsed=elapsed,
        trace=trace,
        done=done,
        steps_run=steps_run,
        fish_ids=fish_ids,
        spawn_seed=spawn_seed,
        dynamics_seed=dynamics_seed,
    )


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
    parser.add_argument(
        "--emit-behavior-trace",
        action="store_true",
        help="落整群行为回放到 <run>/behavior_trace/（回放/诊断，非 BC 数据）",
    )
    parser.add_argument(
        "--environment",
        default=None,
        help="configs/experiment_environments.yaml 的 environment_id；缺省=基线",
    )
    parser.add_argument("--seeds", default=DEFAULT_SEEDS, help="逗号分隔；见 experiment_seeds.yaml")
    parser.add_argument("--steps", type=int, default=None, help="默认取 world.episode_steps")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        cfg_path = ROOT / cfg_path
    try:
        overrides = load_environment(args.environment) if args.environment else None
    except KeyError as exc:
        raise SystemExit(str(exc)) from exc
    cfg = load_arena_config(cfg_path, overrides=overrides)
    steps = args.steps if args.steps is not None else cfg.world.episode_steps
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    e_max = cfg.energy.e_max
    weights = load_evolution_config().fitness_weights.model_dump()

    all_rows: list[dict] = []
    seed_rows: list[dict] = []
    for seed in seeds:
        run_id = f"{args.experiment_id}-s{seed}"
        run_dir = create_run_dir(args.experiment_id, args.config, seed, overrides)
        episode = run_episode(
            cfg_path,
            seed,
            steps,
            overrides,
            args.emit_behavior_trace,
            experiment_id=args.experiment_id,
        )
        per_fish, events, elapsed = episode.per_fish, episode.events, episode.elapsed
        gen = next(iter(per_fish.values()), {}).get("generation") or 0
        write_event_log(
            run_dir / "events.jsonl",
            episode_event_header(
                experiment_id=args.experiment_id,
                episode_id="ep0001",
                environment_id=args.environment or "default",
                generation=int(gen),
                episode_seed=episode.spawn_seed,
                n_events=len(events),
            ),
            events,
        )
        if args.emit_behavior_trace:
            write_trace(
                run_dir / "behavior_trace" / "episode_ep0001.jsonl",
                trace_header(
                    experiment_id=args.experiment_id,
                    episode_id="ep0001",
                    environment_id=args.environment or "default",
                    generation=int(gen),
                    episode_seed=episode.spawn_seed,
                    dynamics_seed=episode.dynamics_seed,
                    total_steps=episode.steps_run,
                    terminated=False,
                    truncated=episode.done,
                    fish_ids=episode.fish_ids,
                    environment_config=asdict(cfg.population),
                ),
                episode.trace,
            )
        rows = [
            {
                "seed": seed,
                "fish_id": fid,
                **episode_metrics(
                    rec,
                    episode_steps=steps,
                    e_max=e_max,
                    capture_success_prob=cfg.growth.capture_success_prob,
                    weights=weights,
                ),
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
            "environment": args.environment or "default",
            "emit_behavior_trace": bool(args.emit_behavior_trace),
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
