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
| E2 | **`trajectory_example.jsonl` 仍陈旧** | 8 行仅 4 键、无 header；`schemas/examples/README.md:17` 标待重生成（对照 `event_log` 已闭环） |
| E3 | **文献待登记** | `bibliography.md` `待登记-2`（Arena 生物学 5 组，一条未登记）、`-3`（`reference_magnitudes` 6 条）、`-4`（#217 License 复核）、`-5`（前端资源） |
| E4 | **`docs/declaration/THIRD_PARTY.md` 空表** | 开来源码机制对照 `[bib#215]–[bib#220]` 未声明；`待登记-4` |
| E5 | **参数总表 arena 组** | 1 `missing`（`body_length_mm`，属长度契约）、33 `no_basis`；`env_*` 三组状态「草案待确认」 |
| E6 | ~~`episodes.jsonl` 只计 6/8 类事件~~ ✅ **已闭合（2026-09-26）**：`run_arena EVENT_KEYS` 补齐 8 类；`make_figs` 事件图同步 8 列 | — |
| E7 | **run 产物 JSON schema 未建** | `metadata.json`/`population.jsonl`/`episodes.jsonl`/`seed_summary.json`（`experiment §5.2` 自述「待实现」）；`schemas/run_metadata.schema.json` 待建 |
| E8 | **arena 实体快照无生产者** | `API接口.md:151` 需 `fish[].x/y/heading/speed/energy/size/alive`；api 移除后无代码产出（= B3） |
| E9 | **`run_chain.py` 缺 `--environment`/overrides 与多代/BC 接口** | Exp F 三组环境无法用 DanioNet 驱动；B1/B2 前置 |
| E10 | **`viable_pairs` 丢弃 non-viable** | evolution 回填 fitness 需「全部个体 + viability 掩码 + `F=0`」；B1 前置接口缺口 |
| E11 | Tier6 副本 `delta-B-and-penetrance.*` 仍用旧分母 `capture_attempts` | 非契约（Tier6），暂不清 |

## 五、arena 实现完善（P2，勿混入基线改动）

1. **`prey_capture` 口径（§4）**：`prey_capture = captures / max(encounters, 1)`，分母 = **尺寸门之前**的纯距离接触数（`arena` S6），**不是** `capture_attempts`。`capture_attempts` 降为诊断列（`capture_attempts − captures` = 「进过口但吃不下」）。实现 `experiment/metrics.py::prey_capture_rate`；每鱼记录 16 列。依据 `experiment/实验与评价体系.md` §2.1（指标契约）。
2. **可用的驱动/评价入口**（均在 `main`，已被测试守护）：
   - `scripts/run_arena.py --experiment-id <id>`（`--emit-trajectories` 可落 Stage-1 轨迹）：3 seed × 600 步，落 `results/runs/<id>-s<seed>/`（`metrics.csv`/`population.jsonl`/`episodes.jsonl`/`seed_summary.json`）。
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

## 六、已冻结、可直接依赖（供对齐）

- **评价入口**：`scripts/run_arena.py`（落 `metrics.csv`/`population.jsonl`/`episodes.jsonl`/**`events.jsonl`**/`seed_summary.json`）；`--emit-trajectories` 落 Stage-1 轨迹（`genome_id` 已为稳定 ID）。
- **event log**：`schemas/event_log.schema.json`；`experiment/events.py`（header + 8 类事件）。
- **基线（可重生成、不入库）** `exp_arena_expert_ref_v3`（A14 后重跑）：`survival 0.9188`、`capture_rate 0.0030`、`prey_capture 0.5148`、`escape_success 0.3032`、`energy_efficiency −9.25e−4`、`composite_fitness 0.3828`。
- **稳定 ID / 世代**：`DanioArena(..., fish_ids, genome_ids, generation)`；`pipeline/arena_episode.py` 与 `experiment/collect.py` 均注入。

`scripts/run_arena.py --emit-trajectories` → 每 run 落 `trajectories/episode_ep0001.jsonl`（首行 header + 逐 step），字段/格式严格照 `schemas/trajectory.schema.json`（jsonschema 逐条校验）。实跑 `exp_traj_smoke`（1 seed）6601 step，obs ⊂ [0,1]、step ⊂ [0,599]、`is_first`/`is_last` 各 12 条，全通过。当日唯一缺口 = P0-9（`genome_id` 全为 `"unknown"`）。
> **【2026-09-26 稍后就地更正】** 该缺口此后已在**代码层**闭合：`scripts/run_arena.py`
> 经 `core/ids.py::mint_id`（纯函数、确定性）铸造并注入 `genome_id`，
> `tests/test_collect_trajectories.py` 有断言。**仍存的是**：
> (a) `evolution/population.py::advance_generation` 无生产调用方 ⇒ id 只是确定性标签，
> 不对应真实演化出的基因型；(b) 本条记录的 `exp_traj_smoke` 产物采于接线之前，
> 仍是 `"unknown"`，须重采。详见 `paper/latex/sections/07-reproducibility.tex` §已知缺口。

---

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
