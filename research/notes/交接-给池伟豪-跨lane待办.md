# 交接：给池伟豪的跨 lane 待办（2026-09-26）

> 来源：四项**只读**审计（`research/notes/参数一致性审计.md`、`引用登记缺口.md`、`前端对接需求清单.md`、
> `验收清单-落差审计.md`）+ Arena / experiment 侧落地。**我未改动你 lane 的任何文件**（单写者约束）。
> 每条都带证据位置。**已解决项已删除**（2026-09-26 更新）：P0-2 DanioNet、P0-4 学习层（BC，`173f911`）、
> P0-5 选择机制与 loader、A3/A4/A6/A12 参数总表形态、A11 `default_model.yaml` 读取方、P0-9 `Fish.genome_id` 占位 —— 均已在 `main` 上闭合。

## 一、仍阻断正式实验 / 论文主线

| # | 事项 | 证据 | 为什么阻断 |
|---|---|---|---|
| P0-8 | **Demo 服务层缺失，但文档仍在承诺** | `api/API与系统工程.md` §9 写 `make demo` 等价 `start_demo.sh` 并开 `http://127.0.0.1:8000`；而 `scripts/start_demo.sh`、`scripts/serve_api.py`、Makefile 的 `api`/`demo` 目标已被 `b4170aa` 删除 | 文档承诺 ↔ 仓库现状**冲突**；路演「Live Demo」时段当前**无载体** |
| 代循环（原 P0-5 残余） | **`advance_generation` 无调用方** | `evolution/population.py::advance_generation`（选择/繁殖已就绪）无生产 caller；缺"评估回填 fitness → 下一代"的循环 | Exp F 的 allele/phenotype frequency 无来源；多代演化跑不起来；**BC 端到端实验**（Stage-1 轨迹 → 训练 → ΔW 不遗传实证）亦待接 |

## 二、需你 / 用户拍板（我不能自行发明）

| # | 事项 | 证据 | 待定 |
|---|---|---|---|
| A14 | **`arena/env.py` 随机源未走 `SeedManager`** | `env.py` 一个 `np.random.default_rng(master)` 同时驱动出生与每步游走，拆不开成两个 namespace | 需新增命名空间（**已定 id=9 为 `arena_dynamics`**，但 **8 已被在飞的 `bc` 占用**）→ 待 `bc` 落地后改 `core/seed.py`+`core §3`+`env.py`。此前跨 lane 复现只能靠 master seed 整体复现 |
| 追加-2 | **`encounters` 口径** | `prey_capture = captures / max(encounters, 1)`，分母为尺寸门之前的纯距离接触数；实测（3 seed × 12 鱼）中位数 2 / 最大 225 / **前 3 位占 65.7%** | 是否改「去重」口径（见 `experiment/实验与评价体系.md` 阅读问题 #13，涉我 lane 的 arena S6 语义）→ 我未动 |

## 三、我方（池伟豪 lane）待补

| # | 事项 | 证据 | 建议 |
|---|---|---|---|
| 接线 | **逐代演化闭环** | `advance_generation` 就绪但无 caller | 编排：`pipeline` 评估 → fitness 回填 `Individual` → `advance_generation` 产下一代（见上「代循环」） |

---

## 追加（2026-09-26）：core ↔ arena 的**已冻结**接口，可直接依赖

1. **`prey_capture` 口径（§4）**：`prey_capture = captures / max(encounters, 1)`，分母 = **尺寸门之前**的纯距离接触数（`arena` S6），**不是** `capture_attempts`。`capture_attempts` 降为诊断列（`capture_attempts − captures` = 「进过口但吃不下」）。实现 `experiment/metrics.py::prey_capture_rate`；每鱼记录 16 列。依据 `experiment/实验与评价体系.md` §4。
2. **可用的驱动/评价入口**（均在 `main`，已被测试守护）：
   - `scripts/run_arena.py --experiment-id <id>`（`--emit-trajectories` 可落 Stage-1 轨迹）：3 seed × 600 步，落 `results/runs/<id>-s<seed>/`（`metrics.csv`/`population.jsonl`/`episodes.jsonl`/`seed_summary.json`）。
   - `scripts/make_figs.py` / `scripts/make_tables.py`：只读 run 目录，出图/出表（含 `diagnostics.md` 口径诊断）。
   - 基线（对照用，**不入库、可重生成**，`exp_arena_expert_ref_v2`）：`survival 0.9472 ± 0.0459`、`prey_capture 0.5407 ± 0.1180`、`escape_success 0.2292 ± 0.0625`、`energy_efficiency −1.031e−3 ± 4.64e−5`、`composite_fitness 0.5123 ± 0.0428`。

## 追加（2026-09-26）：Stage-1 轨迹采集器已就绪

`scripts/run_arena.py --emit-trajectories` → 每 run 落 `trajectories/episode_ep0001.jsonl`（首行 header + 逐 step），字段/格式严格照 `schemas/trajectory.schema.json`（jsonschema 逐条校验）。实跑 `exp_traj_smoke`（1 seed）6601 step，obs ⊂ [0,1]、step ⊂ [0,599]、`is_first`/`is_last` 各 12 条，全通过。**唯一缺口 = 上表 P0-9**（`genome_id` 全为 `"unknown"`）。
