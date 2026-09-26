# 交接：给池伟豪的跨 lane 待办（2026-09-26）

> 来源：四项**只读**审计（`research/notes/参数一致性审计.md`、`引用登记缺口.md`、`前端对接需求清单.md`、
> `验收清单-落差审计.md`）+ 本轮 Arena 侧落地。**我未改动你 lane 的任何文件**（单写者约束）。
> 每条都带证据位置；编号沿用 `参数一致性审计.md` 的 A# 与 `验收清单-落差审计.md` 的 P0 序号。

## 一、P0：阻断正式实验 / 论文主线（按影响排序）

| # | 事项 | 证据 | 为什么阻断 |
|---|---|---|---|
| P0-2 | **DanioNet 整模块未实现** | `src/evogenesis/connectome/` 仅空 `__init__.py` | 动作映射与 activation 无实现 ⇒ 3 baselines / 3 ablations / Exp C、D 无对照对象；「DNA⇒架构⇒行为」主线未被证实 |
| P0-4 | **学习层未实现**（`learning/` 空）⇒ 专家轨迹未生成 | 同上 | BC 预算一致无对象；**遗传边界（ΔW 不遗传）**—— 论文核心卖点——无实证；Exp D 的 BC Dale 消融缺一半 |
| P0-5 | **evolution 无代循环；且 `evolution.py:5` 用 softmax 选择**（`beta=3.0` 硬编码），而定稿是 **binary tournament** | `configs/evolution.yaml:2`（`tournament_size: 2`）vs `evolution/evolution.py:5`；审计 **A9/A10** | 选择机制与定稿**直接冲突**；`configs/evolution.yaml` **全 13 键无任何读取方** ⇒ 改 config 不影响演化；Exp F 的 allele/phenotype frequency 无来源 |
| P0-8 | **Demo 服务层缺失**（用户已指示：**先不动，你在清理**）—— 但**文档仍在承诺** | `api/API与系统工程.md` §9 写 `make demo` 等价 `start_demo.sh` 并开 `http://127.0.0.1:8000`；而 `scripts/start_demo.sh`、`scripts/serve_api.py`、Makefile 的 `api`/`demo` 目标已被 `b4170aa` 删除 | 文档承诺 ↔ 仓库现状**冲突**；路演「Live Demo」时段当前**无载体**。**用户要求我把提醒做到位** ⇒ 记在本条。
| 审计 A11 | `configs/default_model.yaml` **无运行期读取方**（`load_genome_config()` 只被 `tests/` 调） | `genome/config.py:78-93`、`tests/test_genome_config.py:48` | 总表 **55/106** 条的「代码读取」列为 `—`；「所有数值应由 config 读取」在 development / connectome / network / learning / evolution 五组上**实际不成立** |

## 二、参数总表：需你定形态的条目（我未改动）

| # | 条目 | 冲突 | 建议（二选一，你定） |
|---|---|---|---|
| A3 | `generations` | 总表 `config` 指向 `configs/evolution.yaml` 中**不存在**的键（实际是 `generation_buttons`） | ① YAML 补 `generations: 20`；或 ② 总表改指 `generation_buttons` 并把该键的 `10–20` 说明落到 config 值 |
| A4 | `developmental_domains` | 总表 `value=6`（**计数**），而 `config` 指的文件值是**列表** | 拆成 `developmental_domain_count = 6`（`derived`）+ `developmental_domains`（列表，`config` 指 `development.domains`） |
| A6 | `fitness_weights` | 在 `configs/evolution.yaml` 与 `experiment/metrics.py` **各一份**，且**无 loader 读 evolution.yaml** | 我的 `metrics.py::COMPOSITE_WEIGHTS`（0.35/0.25/0.20/0.20）**可以改成 config 注入** —— 但取决于你的 `evolution.yaml` 是否进 loader；请先定形态 |
| A12 | `core §5.1` | 该节说 `capture_size_ratio` 的总表 status 是 `proposed_change`，实际是 `no_basis`，且该档已无任何条目使用 | core 文档改一行（我已把总表 legend 的该档移除并留 `legend_status_note`） |

## 三、需 **Tier-3 决定** 的一条（我 lane，但不能自行发明 id）

**审计 A14：`arena/env.py` 违反 seed 命名空间纪律 —— 但审计给的「一行改法」不安全。**

- 现状：`arena/env.py:56,68` 用 `np.random.default_rng(master_seed)` 直连，未走 `SeedManager(master_seed).rng(...)`
  （`AGENTS.md:174` / `core §3`；`core/seed.py` 的命名空间表里 arena 只有 `arena_spawn: 3`）。
- **安全隐患**：env 用**同一个 generator 驱动两件不同的事** —— ① 初始布局与 prey 再生（应属 `arena_spawn`）；
  ② **逐步猎物游走**（`env.py:383` → `PreyPolicy.act(self._rng)`，**没有对应命名空间**）。
  若直接把整条流换成 `.rng("arena_spawn")`，两条流会**耦合成一条**：游走消耗的抽签会推移 spawn 序列，
  **破坏「同一 seed 下 spawn 序列与跑了多少步无关」**（这正是 D4/S12 类确定性判据依赖的性质）。
- 因此需要 Tier-3 定夺：**新增一个命名空间**（如 `arena_dynamics`，需按 `motif_catalog=4`、`network_init=5` 的先例登记）
  **或**明确规定「逐步动态复用 `arena_spawn` 并以 index 区分」。`core/seed.py` 自己写着「未知名字显式报错，**不静默发明新 id**」，
  故我**不自行新造命名空间**，挂起待你/用户签。

## 四、我方本轮已完成（供你对齐，均已入库）

- 参数总表：**A1** `predator_size`（`config` 从 `null` 指回 YAML + 删过期表述）、**A2** `predator_turn_rate`、
  **A5** `episode_seconds` → `derived`（派生只读）、**A8** `prey_regrowth_steps` → `no_basis`（标定占位）、
  **A12-i** legend 移除未使用的 `proposed_change`。
- arena 文档：**A7** 死旋钮修复（`predator_max_chase_steps` 注入策略）+ 死旋钮守卫测试；
  **A12-ii** 去掉 `proposed_change` 引用；**A13** 统一「actors 12 项 / 14 项 / 含 biomass」三种说法。
- `capture_attempts` 落地（用户裁定「进过口」口径）⇒ **指标首次齐备**，首个 `composite_fitness` 已产出。

## 五、建议对接节奏

1. **`api/` 重写**（路演依赖；最小需求＝4 个 REST 端点，见 `前端对接需求清单.md`）——你已在清理，我等你的节奏；
2. **evolution 的选择机制冲突**（softmax vs binary tournament）优先裁决 —— 它压着「遗传边界」这一核心卖点；
3. DanioNet / 学习层实现（Exp C/D 与主线的前提）；
4. 参数总表 A3/A4/A6/A11 的形态决定后，我这边一次改完总表侧。

---

## 追加（2026-09-26）：你要接 core ↔ arena 时，这些是**已冻结**的接口

你消息说要把 core 和 arena 连起来。以下三件已在 `main` 上，可**直接依赖**，不必再等我：

1. **`prey_capture` 口径已改（§4，2026-09-26）**：
   `prey_capture = captures / max(encounters, 1)`，
   分母 = **尺寸门之前**的纯距离接触数（`arena` S6），**不是** `capture_attempts`。
   `capture_attempts` 降为**诊断列**（`capture_attempts − captures` = 「进过口但吃不下」）。
   实现：`experiment/metrics.py::prey_capture_rate`；每鱼记录字段不变（16 列，含两者）。
   依据：`src/evogenesis/experiment/实验与评价体系.md` §4。
2. **`encounters` 是事件计数、严重右偏 —— 已知，未裁决**：
   实测（3 seed × 12 鱼）中位数 2 / 最大 225 / **前 3 位个体占 65.7%**。
   故**引用 `prey_capture` 必须并列偏态**。是否改「去重」口径见 `实验与评价体系.md` 阅读问题 **#13**
   （涉及你 lane 的 S6 语义，故**我没动**，等你定）。
3. **可用的驱动/评价入口**（都在 `main`，已被测试守护）：
   - `scripts/run_arena.py --experiment-id <id>`：3 seed × 600 步，落 `results/runs/<id>-s<seed>/`
     （`metrics.csv` / `population.jsonl` / `episodes.jsonl` / `seed_summary.json`）
     并汇总到 `results/tables/<id>_summary.json`。
   - `scripts/make_figs.py` / `scripts/make_tables.py`：只读 run 目录，出图与出表
     （含 `diagnostics.md` 自动口径诊断）。
   - 基线（供你对照）：`survival 0.9472 ± 0.0459`、`prey_capture 0.5407 ± 0.1180`、
     `escape_success 0.2292 ± 0.0625`、`energy_efficiency −1.031e−3 ± 4.64e−5`、
     `composite_fitness 0.5123 ± 0.0428`（`exp_arena_expert_ref_v2`，**不入库、可重生成**）。

**仍然卡在你这边的**（会挡住 core↔arena 接线）：**A14**（arena 的 RNG 未走 `SeedManager`）。
`env.py` 现在一个 `np.random.default_rng()` 同时驱动出生与每步游走，**拆不开**成两个 namespace，
而 namespace id 属 **Tier-3 `schemas/` 契约**（现有 `mutation=0 … network_init=5`），
**我不 invent 新 id**。请你给一个 namespace（或在 `core` §10 登记新项），我立刻改。
在此之前，跨 lane 复现只能靠 master seed 整体复现，**无法按模块单独重放**。
