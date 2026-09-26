# 交接：跨 lane 待办（2026-09-26 晚 更新）

> 来源：只读审计（`参数一致性审计.md`、`引用登记缺口.md`、`前端对接需求清单.md`、`验收清单-落差审计.md`）
> + arena↔上下游对齐审计 + 本轮落地（P0-9/A1–A5/event log 落盘/R1/R6/R8）。每条带证据位置。
> **已闭合（不再列出）**：P0-2 DanioNet、P0-4 learning BC、P0-5 选择机制与 loader、P0-9 `Fish.genome_id`、
> A3/A4/A6/A11/A12 参数总表形态、event log 无 producer、事件样例陈旧、Mihalitsis 登记、arena H3 探针状态。

## 一、阻断主线（代码未接）

| # | 事项 | 证据 | 影响 |
|---|---|---|---|
| B1 | **代循环未接** | `evolution/population.py::advance_generation` 无生产 caller；缺「评估回填 fitness → 下一代」 | Exp F 的 allele/phenotype frequency 无来源；多代演化跑不起来 |
| B2 | **BC 端到端未接** | `learning/` 已入库，但无「Stage-1 轨迹 → 训练 → ΔW 不遗传实证」编排 | 论文核心卖点（遗传边界）缺 Exp D 实证 |
| B3 | **P0-8 Demo 服务层缺** | `api/API与系统工程.md §9` 承诺 `make demo`；`scripts/start_demo.sh`/`serve_api.py`/Makefile `demo` 目标已随 `b4170aa` 删除 | 路演「Live Demo」无载体；文档承诺↔现状冲突 |
| B4 | **轨迹双产出链路** | `experiment/collect.py`（1 受控鱼、truncated）vs `run_arena --emit-trajectories`（全部存活鱼、truncated=False）；`core §4.5` 状态 `草案待确认`（用户裁决「挂账不合并」） | 产出方不唯一，`core §4.5` 无法恢复已定稿 |

## 二、需裁决（设计选择，不可 AI 填空）

| # | 事项 | 证据 | 待定 |
|---|---|---|---|
| D1 | **A14 arena 随机源** | `env.py` 单条 `default_rng(master)` 同时驱动 spawn 与逐步游走 | 拆 `arena_spawn`/`arena_dynamics`（id 9 已可用）会改 RNG 流、**作废 §18.11 基线** → 暂缓 |
| D2 | **H3 探针实现** | `arena §14` 任务定义已定稿、实现未做；`§19 P1 #8` | 用 `integrator_memory` 激活替代（零代码）or 实现探针（会加字段/可能加事件） |
| D3 | **`encounters` 去重口径** | `prey_capture=captures/max(encounters,1)`；实测中位 2/最大 225/前 3 占 65.7% | 是否改去重口径（`experiment §7 #1` 已由 arena S6 明确粒度，剩口径抉择） |
| D4 | **捕获成功率随机化** | `arena §19 P0.3` 余项；当前 `P_capture_success=1.0` | 是否引入随机失败（影响指标方差与基线） |
| D5 | **环境三组 M4** | `arena §12`/`M4`：`environment` 字段不改变任何参数，「环境选择」尚无实际因果 | 是否做高价值 prey 靠近 predator 等**场景布置** |

## 三、下游文档待纠正（零行为，需对方 lane）

| # | 事项 | 证据 | 建议 |
|---|---|---|---|
| C1 | **`predator_encounters` 口径** | arena S7=目标获取计数（owner）；`experiment §2.2` 写「与天敌接触计数」，且为 `escape_success` 分母 | 改 `experiment` 措辞 |
| C2 | **评估驱动方（部分闭合）** | 新增 `scripts/run_chain.py`（DanioNet 驱动 Arena，落 metrics/events/seed_summary）已提供模型评估入口；`experiment §3.3`「即 `run_arena.py` 现状」措辞待改（`run_arena`=ExpertPolicy pre-check/基线） | `experiment` 改措辞并指向 `run_chain.py` |
| C3 | **规模口径** | `experiment §4` 泛述「n_fish=12 不变」与 Exp F 48-genome 协议张力（arena §3 已澄清两种规模） | `experiment` 同步限定「12=ExpertPolicy pre-check；48=演化评估」 |
| C4 | **`configs/experiment_environments.yaml` 注释** | 称「填 `missing_required` 第 1 项」，但该项已变 penetrance | 修注释 |

## 四、契约 / 文献 / 声明债务

| # | 事项 | 证据 |
|---|---|---|
| E1 | **`penetrance` 无 owner 定义** | `参数总表.missing_required` 第 1 项；`experiment` 0 处 |
| E2 | **`trajectory_example.jsonl` 仍陈旧** | 8 行仅 4 键、无 header；`schemas/examples/README.md:17` 标待重生成（对照 `event_log` 已闭环） |
| E3 | **文献待登记** | `bibliography.md` `待登记-2`（Arena 生物学 5 组，一条未登记）、`-3`（`reference_magnitudes` 6 条）、`-4`（#217 License 复核）、`-5`（前端资源） |
| E4 | **`docs/declaration/THIRD_PARTY.md` 空表** | 开来源码机制对照 `[bib#215]–[bib#220]` 未声明；`待登记-4` |
| E5 | **参数总表 arena 组** | 1 `missing`（`body_length_mm`，属长度契约）、33 `no_basis`；`env_*` 三组状态「草案待确认」 |

## 五、arena 实现完善（P2，勿混入基线改动）

- `selected neural activity snapshots` 未实现（`arena §13` / `M3`）。
- `PreyPolicy.avoid_gain` 死参数（S12/F2/M6）。
- `arena.collision` 默认场景仍多为 0（`§18.9`/A7）→ 需专门「密集障碍」对照场景；活鱼 escape、空种群终止、`_free_spot` 回退分支缺专项测试。
- `api` 端点残留引用（`/v1/sessions/...snapshot`、`API接口.md §7.2`、`arena_config_path`）随 `api/` 重写一体处理（= B3）。

## 五·补、arena ↔ 上游接线（2026-09-26 查验并补齐）

| 上游 | 接线点 | 状态 |
|---|---|---|
| `core` seed | `pipeline/arena_episode.py::arena_seed_for` → `SeedManager.seed("arena_spawn",0)` 传入 `DanioArena(master_seed=...)` | ✅ 本轮修复（此前直传根部 seed） |
| `core` 稳定 ID | `fish_ids`/`genome_ids` 注入（collect / run_arena / run_chain / pipeline） | ✅ |
| `core §3.1` generation | `DanioArena(generation=)` 透传 | ✅ |
| `core` config | `load_arena_config`（run_arena / collect / run_experiment / run_chain） | ✅ |
| `connectome §2` obs→DanioNet | `pipeline/run_arena_episode` 组 `float32` 批量投喂；`DanioNet.step` 经 `to_float32_tensor` | ✅ |
| **驱动方（Expert/DanioNet）** | ExpertPolicy：`run_arena`/`collect`；**DanioNet：`scripts/run_chain.py`（新，生产入口）** | ✅ |

> `run_chain.py`：`uv run python scripts/run_chain.py --experiment-id <id> --seed <s> [--n N --steps S --generation G]`；实跑 `exp-chain-smoke`（n=12, 30 步）viable 1/12、events 28、events.jsonl 过 schema。

## 六、已冻结、可直接依赖（供对齐）

- **评价入口**：`scripts/run_arena.py`（落 `metrics.csv`/`population.jsonl`/`episodes.jsonl`/**`events.jsonl`**/`seed_summary.json`）；`--emit-trajectories` 落 Stage-1 轨迹（`genome_id` 已为稳定 ID）。
- **event log**：`schemas/event_log.schema.json`；`experiment/events.py`（header + 8 类事件）。
- **基线（可重生成、不入库）** `exp_arena_expert_ref_v2`：`survival 0.9472`、`prey_capture 0.5407`、`escape_success 0.2292`、`energy_efficiency −1.031e−3`、`composite_fitness 0.5123`。
- **稳定 ID / 世代**：`DanioArena(..., fish_ids, genome_ids, generation)`；`pipeline/arena_episode.py` 与 `experiment/collect.py` 均注入。
