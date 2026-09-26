# Schema Examples（契约示例）

> 状态：示例数据。`genome/fish/experiment` 实例已通过各自 schema 校验；
> `trajectory_example.jsonl` 与 `event_log_example.jsonl` 为**旧草案**，与已定稿契约不一致（见下表），
> **不得被代码依赖**，待重生成。
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
| `event_log_example.jsonl` | 事件词表 v1（`arena/Danio_Arena设计与实现说明.md` §18.4.2） | ⚠️ 陈旧：4 行、payload/result 与实现不符、缺 4 类（§18.4.4）；待重生成 |

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
