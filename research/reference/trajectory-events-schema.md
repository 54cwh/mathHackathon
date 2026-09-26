# 轨迹 schema 与事件词表：外部惯例调研

> 搜索时间：2026-09-26　|　落盘 JSON：`research/reference/trajectory-events-schema.json`
> 目的：为 EvoGenesis 两份未定稿数据契约提供外部依据，并给出综合推荐。
> 约束：本文件是证据与过程，不作契约；所有结论分「外部权威」「设计选择-待确认」。

## 0. 待裁决问题回顾

EvoGenesis 有两份契约未定稿：

| # | 契约 | 现状 | 权威冲突 |
|---|---|---|---|
| 1 | `schemas/trajectory.schema.json` | 未冻结；草案字段见 `core/核心机制与数据流.md` §4.2 | 无外部参照，草案缺 episode 级元数据 |
| 2 | Arena 事件词表 | `core` §5.1 是设计侧 6 类草案；`arena/Danio_Arena设计与实现说明.md` §18.4.2 是实现侧 v1（8 类点分层 `arena.*`）；机器可读权威是 `tests/test_arena.py::KNOWN_EVENTS` | 两边事件名与类别数不一致，未裁决 |

调研方法：GitHub 找实现（RLDS / Minari / D4RL / robomimic / HF datasets），OpenAlex+官方规范找理论锚点（JSON Schema / Confluent / SemVer / OpenTelemetry / 事件溯源实证论文）。共 20 条证据，全部附来源 URL。

## 1. 轨迹数据集格式惯例（结论 A 的依据）

四家 episodic 轨迹数据集在结构上高度一致，分两级：

| 来源 | Episode 级 | Step 级 | episode 元数据 |
|---|---|---|---|
| RLDS（T-01） | Episode = Step 的 Dataset + metadata | 必填 `is_first` / `is_last`；可选 `observation` / `action` / `reward` / `is_terminal` / `discount` | `episode_id` / `agent_id` / `environment_config` / `experiment_id` / `invalid`（均建议、非强制） |
| Minari（T-03） | HDF5 `episode_N` 组 | `observations` / `actions` / `rewards` / `terminations` / `truncations` | `id` / `seed` / `total_timesteps` |
| robomimic（T-05） | HDF5 `demo_N` 组 | `actions` / `rewards` / `dones` / `obs` 子组 | 顶层 `env_args`（JSON 字符串）/ `total` |
| D4RL（T-07） | 扁平数组 | `observations` / `actions` / `rewards` / `terminals` / `timeouts` / `infos` | 无逐 episode 元数据 |

可提炼的三条共性：

1. **episode 级元数据必须显式存在**：标识、种子、总步数、环境配置分列。EvoGenesis §4.2 草案把这些（除 experiment/episode/environment/generation 的部分 ID 外）都压进了逐 step 行，重复冗余且缺 `seed` / `total_steps` / 终止类型。
2. **终止与截断分列**：Minari 用 `terminations` vs `truncations`，D4RL 用 `terminals` vs `timeouts`，RLDS 用 `is_terminal=true/false` 区分。这对应本项目的「跑满 600 步（截断）」与「种群全灭提前结束（终止）」，也应分开编码。
3. **同一次数据集内所有 step 字段一致**：RLDS 明文要求，HF/Arrow（T-09）因列式强制同类型，缺失字段以 null 填充。

## 2. schema 版本化惯例（结论 A-5 的依据）

- **JSON Schema 自身版本**：`$schema` 声明方言（dialect），必须位于根级、作用于整个文档；`$id` 给唯一标识（V-01）。本项目既有 `schemas/*.schema.json` 已统一用 draft 2020-12，`trajectory.schema.json` 应沿用。
- **数据 schema 的兼容性语义**：Confluent Schema Registry 给出 7 级兼容性（V-02）。对 JSON Schema，**BACKWARD 允许加可选字段、删字段；FULL 仅允许增删可选字段**。transitive 变体要求新 schema 与**全部历史版本**兼容。
- **版本号语义**：SemVer 2.0.0（V-03）规定 MAJOR=不兼容变更、MINOR=向后兼容新增、PATCH=向后兼容修复；发布后内容不可改，弃用先经 MINOR 再于 MAJOR 移除。
- **破坏性但可转换时**：事件溯源用 upcaster 在读取时把旧 JSON 转成新 schema，只维护最新版（V-04；同行评议实证见 E-04）。

## 3. 结构化事件词表惯例（结论 B 的依据）

- **事件类型名 = 稳定命名 + 唯一确定结构**：OpenTelemetry 规定 `EventName` 应唯一标识事件结构（attributes 与 body），非空 EventName 的记录才叫 Event（E-01）。
- **事件名不含动态值**：OTel 明文 `Event names MUST NOT include dynamic values`，标识符等放 attributes（E-02）。这直接支持 `arena.<event>` 固定名 + `payload` 承载 `fish_id`/`prey_id`。
- **命名规则**：小写、点号命名空间、多词 snake_case、两名不得复用、只增不删（弃用标 deprecated）（E-03）。
- **演化方法**：同行评议的工业实证归纳出五种事件 schema 演化方法（versioned events / weak schema / upcasting / in-place transformation / copy-and-transform）（E-04）。

## 4. 综合推荐

### 4.1 轨迹 schema 推荐字段集

外部无先例的项已标「设计选择-待确认」。文件组织沿用 core §4.5 的逐 episode JSONL，episode 元数据放**第 1 行 header 记录**（`record_type: "episode"`），后续为 step 记录（`record_type: "step"`）。该 header 行做法是设计选择，外部数据集均为嵌套结构。

**Episode header（第 1 行）**

| 字段 | 类型 | 必填 | 依据 |
|---|---|---|---|
| `schema_version` | str (SemVer) | required | V-03；core §4.2 |
| `record_type` | str const `"episode"` | required | 设计选择 |
| `experiment_id` | str | required | core §4.2；RLDS |
| `episode_id` | str | required | core §4.2；RLDS |
| `environment_id` | str | required | core §4.2 |
| `generation_id` | int | required | core §4.2 |
| `fish_id` / `genome_id` | str | required | core §4.2 |
| `episode_seed` | int | required | Minari `seed`（T-03）；复现 |
| `total_steps` | int | required | Minari `total_timesteps`（T-03） |
| `terminated` | bool | required | Minari/D4RL 分列（T-03/T-07） |
| `truncated` | bool | required | 同上 |
| `sensory_dim` / `action_dim` | int const 12 / 2 | optional | Minari 存 space 元数据；防维度漂移 |
| `hz` | int 20 | optional | core §4.2 参数 |
| `environment_config` | object/str | optional | RLDS `environment_config`；robomimic `env_args` |
| `obs_dim_names` | str[12] | optional | 冻结 12 维顺序（验收硬项） |
| `config_hash` / `git_commit` | str | optional | robomimic `env_args`；复现 |

**Step 记录（第 2 行起）**

| 字段 | 类型 | 必填 | 依据 |
|---|---|---|---|
| `record_type` | str const `"step"` | required | 设计选择 |
| `step` | int 0–599 | required | core §4.2 |
| `observation` | number[12] | required | core §4.2（顺序冻结） |
| `expert_action` | number[2] | required | core §4.2 |
| `reward` | number | optional | RLDS/D4RL/Minari 均带；BC 训练不需要，语义为 0 或 `food_reward` |
| `is_first` / `is_last` | bool | optional | RLDS 必填惯例（T-01） |
| `terminated` / `truncated` | bool | optional | 逐 step 终止信号 |

**dtype**：落盘 JSON number；canonical in-memory dtype 为 float32（core §0），schema 描述中显式注明。`next_observation` 仅为 Q-learning 服务（D4RL），BC 不需要，不推荐加入。

**`schema_version` 兼容策略**：采用 SemVer；MINOR=只加可选字段（向后兼容），MAJOR=删/改名、可选改必填、改类型或语义；因轨迹是归档产物，建议按 BACKWARD_TRANSITIVE 执行（读端须能读全部历史 MAJOR），可纯函数转换的破坏性变更用 upcaster。采用 SemVer 本身是设计选择。

### 4.2 事件词表权威与冻结元信息

**权威归属**：以 `arena/Danio_Arena设计与实现说明.md` §18.4.2（8 类 `arena.*`）+ `tests/test_arena.py::KNOWN_EVENTS`（机器可读，测试守护）为 v1 唯一权威；`core/核心机制与数据流.md` §5.1 降为设计参考。核心 §10 #2 需按此裁定并回写。

| 冻结所需项 | 内容 |
|---|---|
| envelope 公共字段 | `schema_version`(SemVer) / `experiment_id` / `episode_id` / `environment_id` / `generation_id` / `step` / `seq`(从 1 起) / `type` / `payload` |
| 命名规则 | 全小写、点号命名空间 `arena.<event>`、多词 snake_case、事件名不含 `fish_id`/`prey_id` 等动态值（E-02/E-03） |
| payload schema | 以 `type` 为键的 `$defs`，逐类覆盖 §4.2 八型的 payload（entity_id / fish_id,prey_id,distance,size_ratio,threshold,capture_radius,result / food_reward / threat_source / obstacle_id / survival_steps / predator_id / steps,fish_alive,prey_remaining） |
| 冻结纪律 | 词表只增不删，废弃标 deprecated；改 type 或 payload 字段名/含义需同步 env.py、KNOWN_EVENTS、§4.2、core §5.1、示例 jsonl、前端 `ArenaEvent`、WS R11（arena §7 已列全） |

「词表 + 守卫测试作为权威」无外部标准直接规定，属设计选择，但方向被 OTel 命名/唯一性规范与事件溯源稳定命名实践支持。

## 5. 风险点

| 级别 | 风险 | 处置 |
|---|---|---|
| 阻断 | core §5.1 裸名事件 vs arena v1 点分层事件名、类别数不一致 | 负责人先裁定权威，再回写 core §10 #2 |
| 阻断 | `schemas/examples/event_log_example.jsonl` 与实现冲突：spawn payload 带坐标（实现无）、`result:"too_far"`（实现不可能出现）、escape 多出 `reaction_latency_steps`、只覆盖 4/8 类 | 按 arena §4.4「首选」依 v1 重生成示例 |
| 重要 | `expert_action` 与 RL 惯例 `action` 命名不同 | schema description 注明等价，防与 policy action/ΔW 混淆 |
| 重要 | 新增 `terminated`/`truncated` 需与 `experiment/实验与评价体系.md` 的 fitness/存活口径对齐 | 确认 owner，避免跨模块各写一版 |
| 重要 | Minari 许可显示 Other（GitHub 未识别 SPDX） | 复用其代码前人工核对 LICENSE 条款 |

## 6. 明确缺口（未找到，不用低质结果充数）

- 未找到外部规范对「JSONL 逐 episode 一文件 + header 行 + `record_type` 判别」的权威先例（RLDS/Minari/robomimic 均为嵌套结构或列式），该组织方式为**设计选择**。
- 未找到对本项目 `schema_version` 字段名与位置的外部规定，SemVer 用法为**设计选择**。
- 未找到外部标准规定「词表 + 守卫测试」作为冻结权威，属工程模式综合推荐。
- D4RL 仓库已归档（数据迁往 Minari），仅作字段命名出处，不作活跃依赖。

## 7. 证据索引

JSON 中 `items[]` 共 20 条，分三组：`T-01…T-10`（轨迹格式）、`V-01…V-05`（版本化）、`E-01…E-05`（事件词表）。每条附 `url` / `source_url`，repo 类附 gh CLI 实测 star 与 SPDX 许可，paper 类附 OpenAlex 引用数与 `peer_review` 标记。
