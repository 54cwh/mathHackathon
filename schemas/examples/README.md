# Schema Examples（契约示例）

> 状态：示例数据。`genome/fish/experiment` 实例已通过各自 schema 校验；
> `trajectory_example.jsonl` 仍为**旧草案**，与已定稿契约不一致（见下表），**不得被代码依赖**，待重生成；
> `event_log_example.jsonl` 已按事件词表 v1 重生成（见下）。
>
> 本目录是**契约示例**，不是仿真运行产物——真实 run 数据属于
> `results/runs/`（不入库）。

## 文件清单

| 文件 | 校验对象 | 状态 |
|---|---|---|
| `genome_example.json` | `schemas/genome.schema.json` | schema 已冻结，实例已通过校验 |
| `fish_example.json` | `schemas/fish.schema.json` | schema 已冻结，实例已通过校验 |
| `experiment_example.json` | `schemas/experiment.schema.json` | schema 已冻结，实例已通过校验 |
| `trajectory_example.jsonl` | 已定稿 `schemas/trajectory.schema.json` | ⚠️ 陈旧：8 行仅 4 键、无 header，未通过校验（`research/notes/评估指标与事件映射-草案.md` S-09）；待重生成 |
| `event_log_example.jsonl` | `schemas/event_log.schema.json`（首行 header + 事件词表 v1） | ✅ 已重生成：header + 8 类各 1 条、payload 与实现逐字段一致（§18.4.4 闭合） |

## 生成来源（provenance）

- 生成日期：2026-09-25
- 生成基线：commit `b0886f0`（docs: 数据全流程规范 v1.0 草案）
- 专用示例种子：`master_seed = 20260925`（子流 `+1`，按 Seed Manager 派生风格）。
  **注意**：该种子与 Demo（`250927`）和正式实验（`1103/2207/3301`）完全隔离，
  仅为可复现生成示例而设。
- 使用了仓库自身代码保证规则一致：
  - `src/evogenesis/genome/genome.py` — 二倍体基因组生成（2 对 × 128 bp，ACGT）
  - `src/evogenesis/arena/policies.py::ExpertPolicy` — 轨迹中的专家动作
    `(ω, v)` 由该策略对观测向量直接计算，非手工编造
- `experiment_example.json` 中的 `seed: 1103` 取自
  `configs/experiment_seeds.yaml` 的第一个正式种子。

### event_log_example.jsonl 重生成（2026-09-26）

- **来源一（6 类，真实 episode 摘录）**：默认 `ArenaConfig()`、示例种子 `20260925`、600 步、`ExpertPolicy` 驱动；取各类**首次出现**的一条：`arena.spawn` / `arena.prey_captured` / `arena.collision` / `arena.escape` / `arena.fish_captured` / `arena.episode_end`。
- **来源二（2 类，受控场景）**：`arena.capture_attempt` 与 `arena.energy_depleted` 在默认配置下**不可自然观测**（能量不会耗尽；前向锥内出现"过大猎物"罕见），故由受控场景触发（均为 arena 真实代码路径产出）：
  - `capture_attempt`：鱼正前方 2.0 处放置 `size=5.0` 的猎物（`size_ratio=0.2 < κ=1.25` → `too_small_to_eat`）。
  - `energy_depleted`：将某鱼能量置 0 后结算一步。
- 摘录行保留原始 `seq` / `step`；受控场景行的 `seq` 为示例内编号。文件首行为 **header**（run 级上下文示意，`n_events=8`），其后 8 条事件；形状由 `schemas/event_log.schema.json` 冻结。**本文件是契约示例，不是仿真运行产物。**

## trajectory 观测向量的 12 维语义（connectome/DanioNet设计规范.md §2）

| idx | 字段 | idx | 字段 |
|---|---|---|---|
| 0 | prey_left_signal | 6 | prey_relative_size |
| 1 | prey_right_signal | 7 | predator_relative_size |
| 2 | threat_left_signal | 8 | looming_rate |
| 3 | threat_right_signal | 9 | current_speed |
| 4 | obstacle_left_signal | 10 | energy |
| 5 | obstacle_right_signal | 11 | hunger |

示例剧情（step 300–307）：鱼追踪并捕获 `prey_07`（能量 0.62 → 0.74，
饥饿 0.41 → 0.28），随后 `predator_03` 出现在左侧（step 305 起 threat
信号上升，速度按 ExpertPolicy 规则提升）。

## 校验方式

```bash
python - <<'PY'
import json
from pathlib import Path
from jsonschema import validate
base = Path("schemas")
for name in ["genome", "fish", "experiment"]:
    inst = json.loads((base/"examples"/f"{name}_example.json").read_text(encoding="utf-8"))
    schema = json.loads((base/f"{name}.schema.json").read_text(encoding="utf-8"))
    validate(inst, schema)
    print(f"{name}: OK")
PY
```
