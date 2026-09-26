"""Arena smoke baseline (Danio_Arena设计与实现说明.md section 18.11).

Regenerates the single-seed and multi-seed smoke tables with 12 ExpertPolicy-driven
fish over a full 600-step episode, so the documented baseline is reproducible
instead of being an ad-hoc observation.

Usage:  .venv/Scripts/python.exe scripts/smoke_arena.py
"""

from __future__ import annotations

import time

from evogenesis.arena.config import ArenaConfig
from evogenesis.arena.env import DanioArena
from evogenesis.arena.policies import ExpertPolicy

SEEDS = (1, 7, 42, 1234, 250927)
STEPS = 600
KEYS = ("arena.prey_captured", "arena.fish_captured", "arena.collision",
        "arena.escape", "arena.energy_depleted", "arena.spawn")


def run(seed: int) -> dict:
    arena = DanioArena(ArenaConfig(), master_seed=seed)
    arena.reset()
    expert = ExpertPolicy()
    t0 = time.perf_counter()
    for _ in range(STEPS):
        actions = {fid: expert(arena.observe(fid)) for fid, f in arena.fish.items() if f.alive}
        arena.step(actions)
    elapsed = time.perf_counter() - t0
    counts = {k: 0 for k in KEYS}
    for ev in arena.events:
        if ev.type in counts:
            counts[ev.type] += 1
    row = {"seed": seed, **{k.split(".")[1]: v for k, v in counts.items()}}
    row["alive"] = sum(1 for f in arena.fish.values() if f.alive)
    row["steps_per_s"] = STEPS / elapsed
    return row


def main() -> None:
    rows = [run(s) for s in SEEDS]
    print("| seed | `arena.prey_captured` | `arena.fish_captured` | `arena.collision`"
          " | `arena.escape` | `arena.energy_depleted` | 存活 |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['seed']} | {r['prey_captured']} | {r['fish_captured']} | {r['collision']}"
              f" | {r['escape']} | {r['energy_depleted']} | {r['alive']} |")
    ref = rows[-1]
    print()
    print(f"seed {ref['seed']}: spawn={ref['spawn']}, "
          f"throughput={ref['steps_per_s']:.0f} steps/s")


if __name__ == "__main__":
    main()
