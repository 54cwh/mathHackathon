# 交接：跨 lane 待办（2026-09-26 晚 更新）

> 来源：只读审计（`参数一致性审计.md`、`引用登记缺口.md`、`前端对接需求清单.md`、`验收清单-落差审计.md`）
> + arena↔上下游对齐审计 + 本轮落地（P0-9/A1–A5/event log 落盘/R1/R6/R8）。每条带证据位置。
> **已闭合（不再列出）**：P0-2 DanioNet、P0-4 learning BC、P0-5 选择机制与 loader、P0-9 `Fish.genome_id`、
> A3/A4/A6/A11/A12 参数总表形态、event log 无 producer、事件样例陈旧、Mihalitsis 登记、arena H3 探针状态。

## 一、阻断主线（代码未接）

| # | 事项 | 证据 | 影响 |
|---|---|---|---|
| B1 ✅ | **代循环未接** | 已闭合（2026-09-26）：`experiment/evolution_run.py::run_evolution` + `scripts/run_evolution.py`（评估→F→回填→`advance_generation`→下一代）；契约 `experiment/代循环编排.md` | ✅（allele/phenotype frequency 仍待 experiment 侧从种群快照派生） |
| B2 | **BC 端到端未接** | `learning/` 已入库，但无「Stage-1 轨迹 → 训练 → ΔW 不遗传实证」编排 | 论文核心卖点（遗传边界）缺 Exp D 实证 |
| B3 | **P0-8 Demo 服务层缺** | `api/API与系统工程.md §9` 承诺 `make demo`；`scripts/start_demo.sh`/`serve_api.py`/Makefile `demo` 目标已随 `b4170aa` 删除 | 路演「Live Demo」无载体；文档承诺↔现状冲突 |
| B4 ✅ | **轨迹双产出链路** | 已闭合（2026-09-26）：BC `trajectories/` 唯一产出方=`experiment/collect.py`；整群 dump 正名为独立资产 `behavior_trace/`（`--emit-behavior-trace`，schema `schemas/behavior_trace.schema.json`）；共用 `experiment/arena_rollout.py`。`core §4.5` 恢复已定稿 | ✅ |

## 二、需裁决（设计选择，不可 AI 填空）

| # | 事项 | 证据 | 待定 |
|---|---|---|---|
| ~~D1~~ | ~~**A14 arena 随机源**~~ ✅ **已闭合 2026-09-26（池伟豪 `ec2eaf3`）** | 原：`env.py` 单条 `default_rng(master)` 同时驱动 spawn 与逐步游走 | 已拆 `arena_spawn`(id 3) / `arena_dynamics`(id 9)，`DanioArena(*, spawn_seed, dynamics_seed)`，编排经 `arena_seeds_for` 透传；**全基线已重跑（v3）**。残留 D5（改障碍数量/半径/clearance 会平移 spawn 流）仍在 |
| D2 | **H3 探针实现** | `arena §14` 任务定义已定稿、实现未做；`§19 P1 #8` | 用 `integrator_memory` 激活替代（零代码）or 实现探针（会加字段/可能加事件） |
| D3 | **`encounters` 去重口径** | `prey_capture=captures/max(encounters,1)`；实测中位 2/最大 225/前 3 占 65.7% | 是否改去重口径（`experiment §7 #1` 已由 arena S6 明确粒度，剩口径抉择） |
| D4 | ~~捕获成功率随机化~~ ✅ **已闭合（2026-09-26）**：新增 `growth.capture_success_prob`（默认 1.0=确定性，零行为）；<1 时失败记 `capture_attempt('missed')`。**待正式实验前定值**（play-test） | — |
| ~~D6~~ | ~~`composite_fitness` 捕食分量口径~~ ✅ **已闭合（2026-09-26）**：`experiment §2.3` 改为**条件式**（默认 `capture_rate`，随机化后用 `prey_capture`），`metrics.py` 已对齐并重跑 | — |
| D5′ | **死参/死分支** | ✅ 已清（2026-09-26）：删 `PreyPolicy.avoid_gain` 与 `Predator.alive` 死分支 | — |
| D5 | **环境三组 M4** | `arena §12`/`M4`：`environment` 字段不改变任何参数，「环境选择」尚无实际因果 | 是否做高价值 prey 靠近 predator 等**场景布置** |

## 三、下游文档待纠正（零行为，需对方 lane）

| # | 事项 | 证据 | 建议 |
|---|---|---|---|
| ~~C1~~ | ~~`predator_encounters` 口径~~ ✅ **已闭合（2026-09-26）**：`experiment §2.1/§2.2/§7` 与 `metrics.py` 已回写为 arena S7（被锁定次数）；`encounters` 粒度亦回写 S6（每鱼每步至多 1 次） | — | — |
| ~~C2~~ | ~~评估驱动方~~ ✅ **已闭合（2026-09-26）**：`experiment §3.3` 改为「模型评估=`run_chain.py`(DanioNet)；`run_arena`=ExpertPolicy pre-check/基线」；两脚本 docstring/help 同步标注驱动方 | — |
| ~~C3~~ | ~~规模口径~~ ✅ **已闭合（2026-09-26）**：`experiment §4` 限定「12=`ExpertPolicy` pre-check；48=Exp F 演化评估（按 viable 覆盖 n_fish）」 | — |
| ~~C4~~ | ~~config 注释~~ ✅ **已闭合（2026-09-26）**：注释改为「三组已登记；`missing_required` 仅剩 penetrance」 | — |

## 四、契约 / 文献 / 声明债务

| # | 事项 | 证据 |
|---|---|---|
| E1 | **`penetrance` 无 owner 定义** | `参数总表.missing_required` 第 1 项；`experiment` 0 处 |
| E2 ✅ | ~~`trajectory_example.jsonl` 陈旧~~ | 已闭合：schema 1.1.0（含 `dynamics_seed`），由 `collect.py` 重生成 |
| E3 | **文献待登记** | `bibliography.md` `待登记-2`（Arena 生物学 5 组，一条未登记）、`-3`（`reference_magnitudes` 6 条）、`-4`（#217 License 复核）、`-5`（前端资源） |
| E4 | **`docs/declaration/THIRD_PARTY.md` 空表** | 开来源码机制对照 `[bib#215]–[bib#220]` 未声明；`待登记-4` |
| E5 | **参数总表 arena 组** | 1 `missing`（`body_length_mm`，属长度契约）、33 `no_basis`；`env_*` 三组状态「草案待确认」 |
| E6 | ~~`episodes.jsonl` 只计 6/8 类事件~~ ✅ **已闭合（2026-09-26）**：`run_arena EVENT_KEYS` 补齐 8 类；`make_figs` 事件图同步 8 列 | — |
| E7 ✅ | **run 产物 JSON schema 未建** | 已闭合：`run_metadata`/`population`/`episodes`/`seed_summary`/`run_table_summary`/`fitness`/`evolution` 7 个 schema + `tests/test_run_artifacts_schema.py` |
| E8 | **arena 实体快照无生产者** | `API接口.md:151` 需 `fish[].x/y/heading/speed/energy/size/alive`；api 移除后无代码产出（= B3） |
| E9 ◐ | **`run_chain.py` 缺 `--environment`/overrides 与多代/BC 接口** | 多代+环境已由 `scripts/run_evolution.py --environment` 提供（Exp F 可用）；`run_chain.py` 单代入口仍未加 `--environment` |
| E10 ✅ | **`viable_pairs` 丢弃 non-viable** | 已闭合：`pipeline.evaluate_population` 返回对齐全长的 `phenotypes`/`viable_indices`，`evolution_run.assemble_individuals` 构全量掩码 |
| E11 | Tier6 副本 `delta-B-and-penetrance.*` 仍用旧分母 `capture_attempts` | 非契约（Tier6），暂不清 |

## 五、arena 实现完善（P2，勿混入基线改动）

1. **`prey_capture` 口径（§4）**：`prey_capture = captures / max(encounters, 1)`，分母 = **尺寸门之前**的纯距离接触数（`arena` S6），**不是** `capture_attempts`。`capture_attempts` 降为诊断列（`capture_attempts − captures` = 「进过口但吃不下」）。实现 `experiment/metrics.py::prey_capture_rate`；每鱼记录 16 列。依据 `experiment/实验与评价体系.md` §2.1（指标契约）。
2. **可用的驱动/评价入口**（均在 `main`，已被测试守护）：
   - `scripts/run_arena.py --experiment-id <id>`（`--emit-behavior-trace` 可落整群行为回放 `behavior_trace/`）：3 seed × 600 步，落 `results/runs/<id>-s<seed>/`（`metrics.csv`/`population.jsonl`/`episodes.jsonl`/`seed_summary.json`）。
   - `scripts/make_figs.py` / `scripts/make_tables.py`：只读 run 目录，出图/出表（含 `diagnostics.md` 口径诊断）。
   - 基线（对照用，**不入库、可重生成**，`exp_arena_expert_ref_v3`，A14 后重跑）：`survival 0.9188 ± 0.1362`、`capture_rate 0.0030 ± 0.0014`、`prey_capture 0.5148 ± 0.2972`、`escape_success 0.3032 ± 0.1354`、`energy_efficiency −9.25e−4 ± 1.62e−4`、`composite_fitness 0.3828 ± 0.0725`。

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

## 六、【Demo 闸门】服务层重写 —— 归属待确认，需求清单已备好

**2026-09-26 更正**：本节初稿把归属写成「用户已指定由你（池伟豪）实现」。**该断言不严谨，撤回**：
`AGENTS.md` **不按人归属 `api/`**（只规定「API 端点 → `api/API接口.md`」，L129）；
**唯一的人名归属在 `api/API接口.md §6`** —— Arena 10 条 functional 记 **李辰钊**、
模型/实验 10 条 501 stub 记 **池伟豪**；而用户 2026-09-26 的口头安排是「池伟豪写 api」。
**三者不一致 ⇒ 请二人先确认归属**：按 §6 的记法，下面 §1/§2 那 6 条（**正是 Demo 必需的**）
原本是李辰钊的。

### 需求清单已备好（不必重新侦察）

`research/notes/前端驱动-API实现清单.md` —— 前端驱动的**最小必要清单 + 审计**：

- **§1 Demo 必需 4 条**、**§2 契约必需 2 条**（合起来**恰好等于 `arena.ts` 导出的 6 个 REST 函数**，不多不少）；
- **§3 本轮不做但需预留 2 条**（Fish Card / leaderboard —— 面板未做，现在实现无人调用）；
- **§4 明确不要实现**（`/pause` 前端不调、`/health` 只给启动脚本、**10 个 501 stub 与 Demo 无关**）；
- **§5 契约未定、禁止现在实现**（`/v1/ws`：`交互与可视化.md` 阅读问题 8 未定采样率与 payload，
  现在实现等于赌一个会被推翻的契约）；
- **§7 实现期不变量**（`204` 无体 / `release` 用 query 参数 / 坐标系 / RFC 7807 /
  `environment` 改了也没用 / 别重复实现前端已做的降级语义 / `make demo` 承诺须兑现）。

**证据底本**：`research/notes/前端对接需求清单.md`（逐行测全调用面，含文件行号）。

### 唯一硬约束

**兼容 `frontend/src/api/arena.ts` 既有调用面 ⇒ `frontend/**` 0 改动。** 前端即契约；
不一致时改服务层（改前端会同时作废上述两份清单）。

### 交付后

告诉我一声，我接着做前端接线与 Demo 流程。**归属确认前我不动 `src/evogenesis/api/`。**

## 追加（2026-09-26 晚）：本轮跨 lane 发现（leader 侧，第二轮）

> 来源：报告正文四章写作 + 架构/viability 取证 + 文档指针审计。**我未改动你 lane 的
> 实质内容**（唯一例外见第 4 条，是加法式追加且已在此声明）。每条带证据位置。

### 1. `paper/latex/refs.bib` 是**派生产物**，请勿手改
唯一来源 = `research/notes/bibliography.md`。本轮有人手工给 `.bib` 加了 Mihalitsis 2017，
但 note 里的 `#` 未转义 ⇒ 编译报「macro parameter character #」，门禁三红。已按单一来源
重新生成（221 条 / 0 丢弃），并加了守护测试（`tests/test_paper_bib.py` 同步检查 +
`tests/test_paper_latex_safety.py` 字符检查）。**要加文献请登记 `bibliography.md` 后重跑
`scripts/make_bib.py`**；生成器现已转义 `# & % $ _ ^ ~` 与反斜杠，url 字段保持裸 URL
（plainnat 自己会包 `url` 宏；再包一层会与它叠加成嵌套调用 ⇒ hyperref 递归 ⇒ 编译崩）。

### 2. 环境对照三组的状态：**以参数总表为准 = `no_basis` +「草案待确认」**
`docs/参数总表.json` 的三条 `env_*` 现为 `status: "no_basis"`，且 `missing_required.note` 写
「状态『草案待确认』…并从本清单移出」（`items` 现仅剩 `penetrance`）。
`configs/experiment_environments.yaml` 头注已与之一致（本轮有 agent 误改成「已定稿」并被
leader 推翻）。若你希望统一措辞（词表值 `no_basis` vs 散文「草案待确认」），属你的表。

### 3. 你 lane 仍有指向旧 `§4` 的**失效指针**（`实验与评价体系.md` 已重构为 §1–§7）
映射：旧 §4「指标定义」→ 新 **§2.1**；旧 §9「Efficiency」→ **§2.4**；旧 §7「环境三组」→ **§4**；
旧 §10「正式结果原则」→ **§1.4**；旧 §11「目录布局」→ **§5.1**。

| 文件 | 位置 | 现写 | 应为 |
|---|---|---|---|
| `core/核心机制与数据流.md` | L159 公平性红线 | §4 | §3.3 / §3.4 |
| `core/核心机制与数据流.md` | L282 `#9 指标定义…见` | §4 | §2.1 |
| `evolution/fitness.py` | L9 跨代/跨环境用原始指标 | §4 | §2.1 / §2.3 |
| `evolution/遗传繁殖与演化模型.md` | L97 各分量原始字段 | §4 | §2.1 |
| `learning/行为克隆学习.md` | L41 公平性红线 | §4 | §3.3 / §3.4 |

（我 lane 内同类失效指针已全部修掉，共 13 个文件；`core` L67/167/228/240 用 `§5` 属粒度较粗
但**不是断链**，无需改。）

### 4. 声明：`development/RGCD数学模型.md` §7 追加了一小节
在 §7 `Dynamical viability` 之后新增「**实测工作点（2026-09-26，可复现）**」（约 16 行）：
记录随机 q 通过率与判据 (iv) 的绑定关系，**只加这一节，未改动任何原有判据/阈值文字**。
成因：本轮为 F6 图取证需要把 viability 数字变成可重放凭证。若你认为该内容应换位置或措辞，
直接改即可（我不会有后续依赖）。

### 5. 一条实质性观察（**不是 bug 主张**，请你裁决是否调参）
viability 判据 **(iv) `ρ(W⁰) < 1` 是唯一绑定约束**：1000 次随机 q 发育里 **898 次（89.8%）**
因它失败；活跃子矩阵 ρ 中位 **1.63**，仅 **10.2%** 落在阈值下。判据 (i)(ii)(iii) 在 1000 次中
**一次也未触发**（与文档「(ii) 是解析保证、非阈值判据」相符，可反向当作 (ii) 实现的旁证）。
机理线索：`configs/default_model.yaml` 的 `w_bar_initial: 0.5` 配 `target_density: 0.15`、
约 37 个活跃神经元时，ρ 的典型值刚好越过 1。是否调属 model lane；我只记录实测分布。
凭证：`scripts/make_fig_viability.py` → `results/figs/dev_viability/data/fig_viability.xlsx`
（首 sheet `_manifest`，含 seed 与复现命令）。

### 6. P0-9 的**精确**状态（此前文档自相矛盾，已就地更正）
- **代码层已闭合**：`scripts/run_arena.py` 经 `core/ids.py::mint_id`（纯函数、确定性）铸造并
  注入 `genome_id`；`tests/test_collect_trajectories.py` 有断言。`arena/entities.py` 的
  `"unknown"` 现仅是「调用方不传」时的向后兼容缺省。
- **仍存两点**：(a) `evolution/population.py::advance_generation` **无生产调用方** ⇒ 该 id 只是
  确定性标签，**不对应真实演化出的基因型**；(b) 接线前采集的历史产物（`exp_traj_smoke`）
  仍是 `"unknown"`，须重采。

### 7. 两处小项
- `configs/experiment_seeds.yaml` 的**键名是 `seeds:`**，而多处文档以概念名 `formal_seeds` 引用
  （`research/notes/参数一致性审计.md` 已记为半登记）。报告正文已统一写 `seeds=`。
- viability 的 reason 词表（`missing_fate:*` / `motor_side_empty` / `no_sided_...` 等）已在
  `development/rgcd.py` 实现，但**尚未在 `core §10` 登记**；F6 脚本以消费方身份镜像了一份
  并用漂移守护测试钉住。**词表 owner 是否登记，属契约层决定**。
  另：`connectome/DanioNet设计规范.md` §5 只写「$x_i$ 低于中位者标 left」，实现是
  `left_count = |motor| // 2`（两者在偶/奇数下结果一致，且实现保证 `left ≤ right`）——
  **建议 spec 补这一句**。

### 8. 报告侧现状（供你判断优先级）
- 已完成并可编译：引言 / 方法 / 实验设计 / 局限与价值 / 可复现性（**29 页，0 错误，
  0 未定义引用**）。
- **仍空**：`04 基线与消融`（MLP/GRU/Fixed Sparse RNN 未实现）、`05 结果`（阻塞：BC 模块与
  契约已就绪，但**未接入流水线**，评估仍由 `ExpertPolicy` 驱动 ⇒ 「学习前/学习后」对照无数据）。
  这两章我不会用编造数字填。

---

## 追加（2026-09-26 夜）：文献登记（为 §1.3 取证）

> 为让报告 §1.3「与 NAS / HyperNEAT 的差异」能真正引用，本轮登记了 **5 条**新文献
> （`bibliography.md` **#222–#226**），全部经**一手核实**：OpenAlex DOI 直查，
> 其中 #226 另用 Crossref 独立复核；JMLR 无 DOI 故用官方页稳定链接（沿用既有惯例）。

| # | key | 条目 | status |
|---|---|---|---|
| 222 | `bib222_stanley2002` | Stanley & Miikkulainen, *Evolving Neural Networks through Augmenting
Topologies*, Evol. Comput. 10(2):99–127 (2002) | peer-reviewed |
| 223 | `bib223_stanley2009` | Stanley, D'Ambrosio & Gauci, *A Hypercube-Based Encoding…*, Artif. Life 15(2):185–212 (2009) | peer-reviewed |
| 224 | `bib224_elsken2019` | Elsken, Metzen & Hutter, *Neural Architecture Search: A Survey*, JMLR 20(55):1–21 (2019) | peer-reviewed |
| 225 | `bib225_liu2019` | Liu, Simonyan & Yang, *DARTS*, ICLR 2019 | **preprint**（登记 arXiv 版；见下） |
| 226 | `bib226_najarro2023` | Najarro, Sudhakaran & Risi, *Towards Self-Assembling ANNs through NDPs*, ALIFE 2023 | peer-reviewed |

### 需你处理的四条（均属你 lane，我未越界）

1. **Huizinga, Mouret & Clune 2014 (GECCO)「Evolving neural networks that are both modular
   and regular」至今未登记，但它是 H4「空间布线代价」的**设计依据** ——
   见 `research/reference/design-basis-connectome.json`（约 L154 附近）。
   本轮 §1.3 不需要它，故**我没有代为登记**（不越界）。**建议 H4 / connectome owner 补登记**，
   否则「有设计依据但引不出处」就是硬约束里的缺陷。
2. **`docs/参数总表.json:265` 的「口径待定」仍未裁决**：其 basis 写
   「≈ ES-HyperNEAT 5×5 substrate = 25 节点；但经典发育编码从 1 个细胞起步——口径待定」。
   本轮 #223/#124 已提供可引原文；且 `design-basis-connectome.json` 已警告
   「**不得用 CPPN 规模冒充 substrate 参数量**」。裁决属你的表。
3. **#225 DARTS 的 status**：我把它登记为 **arXiv 版 + `preprint`**，因为
   OpenReview（`forum?id=r1e3H0R9Fm`）返回反爬验证页、DBLP 返回 Access Denied，
   **无法一手核实 ICLR 正会页链接**，故不冒标 `peer-reviewed`（沿用 #213 惯例）。
   若你有可达的正会页链接，可升级该条。
4. **「48×48 矩阵只在 WS 侧内存、未落盘」这一表述应更正。**
   `paper/图表-数据对照表.md` §4 原先把 F7 的阻塞写成「需 48×48 矩阵落盘 + 与池伟豪一起定（api 边界）」，
   该前提**不成立**：48×48 张量不是 api/WS 侧的私产，而是 `DanioNet` 对发育产物做 batch 内补零后的
   **缓冲区**（`connectome/danionet.py` 的 `weights0` / `support` / `theta`，形状 `(batch, 48, 48)`），
   从发育产物直接可导出，与 api 落盘零依赖。本轮 `scripts/dump_connectome_matrix.py` 已**只依赖发育侧**
   导出全部 42 个基因型的 `w0` / `support` / `sign` / `theta`（`results/tables/connectome_matrix.json`），
   是这一点的存在性证明。请确认并更正你 lane 内（`arena` / `development` / `connectome` 文档）
   任何暗示「存在一个 api 依赖」的表述。
   （我已在我 lane 的 `paper/图表-数据对照表.md` §4 补记里写明；未改你的文档。）

### 已由我同步（告知，非请求）

- `research/notes/引用登记缺口.md`：§3.1 行 6、§3.2 行 29–30 原标 NEAT / HyperNEAT「未登记」，
  现已同步为 **「✅ 已登记 = #222 / #223」**（并修掉「Stanley 仅出现于 #124」这句已失效的旁注）。
  该文件是**活的缺口追踪**，条目一旦登记就应划销 —— 若以后仍见落差，请直接改它。

## 五、本轮新发现：`capture_rate` 的「已实现 / 已重跑」与落盘产物不一致（需你确认）

在 rebase 到 `fdffca8` / `98be94f` 后，我发现**三处上游断言缺少落盘凭证**，
已按「不引用未落盘的数字」处理报告，**未改你的文档、未重跑基线**：

1. **没有任何落盘 run 含 `capture_rate` 列。** 清点 `results/runs/*/metrics.csv`（共 22 个 run 目录）
   与 `results/tables/*_summary.json`（8 份），`capture_rate` 出现次数**均为 0**；
   现存 `exp_env_*` 的 `metrics.csv` mtime 为 **2026-09-26 10:02 UTC**，
   而 `98be94f` 的提交时间是 **12:16 UTC** —— 产物**早于**口径变更约 2 小时。
2. **`实验与评价体系.md` §2.1 的断言据此暂不成立**：该行称「`metrics.csv` / `seed_summary.json`
   均含 `capture_rate`」——对**变更后重跑**的 run 才成立；对现存产物不成立。
3. **§2.1 的环境效应数字（`food_rich` 21.3→27.3、`resource_scarce` 21.3→10.7）无法从现存产物复现**：
   现存 run 给出的是 `Σcaptures` **55→100** 与 **55→38**（我论文 §2.2 引的就是这两个，可复现）。
   两套数字的**单位或 run 世代**不同，需你指明来源。

另：`交接` 表 D1 行（`ec2eaf3` 条）写「全基线已重跑（v3）」——该表述我**未能在磁盘上找到凭证**，
请确认它指的是 §18.11 冒烟基线，还是 `exp_env_*` 四个环境实验（后者显然未重跑）。

**我的处理**（不入你的 lane）：论文中把这三点写成「主口径实现已就位，但**本文所依据的全部落盘 run
均早于该口径变更**，故所报之比值为诊断口径」，并明确「重建基线后方可补报主口径」——
即不引用任何未落盘的数字。**待你确认后**，若需要重跑四环境基线并重出图/表，我可以执行。

## 六、【请你处理】Demo 服务层（P0-8 / B3）—— 用户已指定由你实现

**为什么现在单列一条**：用户 2026-09-26 明确「**先等你确认；你的 api 写好之后我接着做前端**」。
因此这一条是**当前 Demo 的唯一闸门**，其余前端工作都已就绪并在等它。

### 事实基线（无需重新侦察）

- `src/evogenesis/api/{app,schemas,session,stubs,ws}.py` 与 `tests/test_api_contract.py` 已由 `d894cbb` 删除；
  `scripts/serve_api.py`、`scripts/start_demo.sh`、`Makefile` 的 `api`/`demo` 目标已由 `b4170aa` 删除；
  `pyproject.toml` 已移除 `fastapi`/`uvicorn`/`websockets`。`api/` 目录现仅存 `__init__.py`（0 字节）与两份文档。
- **前端完好**：29 个文件入库、`npm run build` 可出 `dist/`、`DanioArenaPanel.tsx`（224 行）已接实时会话。
- 本机 `.venv` **仍装有** `fastapi 0.141.1` / `starlette 1.7.0` / `uvicorn 0.54.0`（清单 G15）⇒ 零安装成本。

### 契约在哪 —— 请直接读，不要重新侦察

`research/notes/前端对接需求清单.md` 已把前端**实际调用面**逐行测全（含文件行号证据）：

- **实调用 4 个端点**：`POST /v1/sessions`、`DELETE /v1/sessions/{id}`（须返回 **204 无体**）、
  `POST /v1/sessions/{id}/release?steps=&use_expert=`（**query 参数，非 body**）、`GET /v1/sessions/{id}/snapshot`。
- **已定义但未被调用 2 个**（**仍属契约**，缺了会留 404 死代码）：`GET /v1/sessions/{id}`、`POST /v1/sessions/{id}/reset`。
- `snapshot` 的**渲染硬依赖字段**：`obstacles[].{x,y,radius}`、`prey.{x,y,size,alive}`、
  `predators.{x,y,size}`、`fish.{x,y,heading,energy,size,alive}`、`step`。
  （`session_id` / `events[]` / `fish[].speed` 是**声明未用**，可不阻塞。）
- **坐标系**：世界 `100×60` ↔ 位图 `640×384` 同比例映射（`sx/sy/sr`）。
- **前端已实现的降级语义**（服务层不必再管）：自调度轮询 `POLL_MS=100`（非 setInterval）；
  任一请求抛错即停循环、须用户手点 Release 才恢复；Reset 走 **delete + create**（不是 `POST /reset`）；
  Pause 只停前端轮询、**不调后端** `/pause`。
- **落地改动清单**在该文件第 179 行：新建 `api/{app,session,schemas}.py` + `scripts/serve_api.py` + `scripts/start_demo.sh`；
  `pyproject.toml` 加回三依赖；`Makefile` 加回 `demo` 目标。

### 两条必须满足的约束

1. **唯一硬约束：兼容 `frontend/src/api/arena.ts` 的既有调用面 ⇒ `frontend/**` 0 改动。**
   前端即契约；若服务层与它不一致，请改服务层而不是改前端（改前端会同时作废上述清单）。
2. **文档承诺必须与实现一致**：`api/API与系统工程.md:133` 承诺 `make demo` 等价 `./scripts/start_demo.sh`、
   浏览器开 `http://127.0.0.1:8000`；现 `Makefile` **无** `demo` 目标。两者必须收敛到同一事实。
   （`api/API与系统工程.md:154` 自认「生产由 FastAPI 托管 `frontend/dist` 免 CORS」尚未写进文档，建议一并补。）

### 交付后

告诉我一声即可 —— 我接着做前端接线与 Demo 流程（选参考图 → 冻色板 → 面板填充）。
**在你说开始之前，我不会动 `src/evogenesis/api/`**，避免与你撞 lane。
