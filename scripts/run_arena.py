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
from dataclasses import asdict
from pathlib import Path

from evogenesis.arena.config import load_arena_config
from evogenesis.evolution.config import load_evolution_config
from evogenesis.experiment import runlayout
from evogenesis.experiment.behavior_trace import (
    trace_header,
    write_trace,
)
from evogenesis.experiment.config import load_formal_seeds
from evogenesis.experiment.environments import load_environment
from evogenesis.experiment.events import write_episode_log
from evogenesis.experiment.expert_run import run_episode
from evogenesis.experiment.metrics import (
    aggregate_by_seed,
    summarise_over_seeds,
)
from evogenesis.experiment.run_artifacts import (
    dump_json,
    individual_metric_rows,
    run_summary_payload,
    write_seed_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]


def _default_seeds() -> str:
    """正式 seed 轴（`configs/experiment_seeds.yaml`，`core §3`；唯一来源）。"""
    return ",".join(str(seed) for seed in load_formal_seeds().seeds)


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
    parser.add_argument(
        "--seeds", default=_default_seeds(), help="逗号分隔；见 experiment_seeds.yaml"
    )
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
        write_episode_log(
            run_dir / "events.jsonl",
            experiment_id=args.experiment_id,
            environment_id=args.environment or "default",
            generation=int(gen),
            episode_seed=episode.spawn_seed,
            events=events,
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
        rows = individual_metric_rows(
            per_fish,
            seed=seed,
            episode_steps=steps,
            e_max=e_max,
            capture_success_prob=cfg.growth.capture_success_prob,
            weights=weights,
        )
        write_seed_artifacts(
            run_dir,
            rows=rows,
            seed=seed,
            per_fish=per_fish,
            events=events,
            steps=steps,
            elapsed=elapsed,
        )
        by_seed = aggregate_by_seed(rows)
        dump_json(run_dir / "seed_summary.json", by_seed, indent=2)
        all_rows.extend(rows)
        seed_rows.extend(by_seed)
        runlayout.update_run_status(run_dir, "completed")
        print(f"[{run_id}] {steps} 步 / {len(rows)} 个体 / {elapsed:.1f}s")

    summary = summarise_over_seeds(seed_rows)
    tables = ROOT / "results" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    out = tables / f"{args.experiment_id}_summary.json"
    dump_json(
        out,
        run_summary_payload(
            experiment_id=args.experiment_id,
            environment=args.environment or "default",
            emit_behavior_trace=bool(args.emit_behavior_trace),
            seeds=seeds,
            steps=steps,
            n_individuals=len(all_rows),
            per_metric=summary,
        ),
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
