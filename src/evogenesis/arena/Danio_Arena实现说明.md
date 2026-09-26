# Danio Arena 实现说明（arena/）

> **管辖范围**：事件词表 v1（唯一权威）、参数表↔代码映射、实现细节与未认领决定。（层级与归属见 `AGENTS.md`「文档层级与优先级」。）

> 状态：实现说明（描述 `main` 上 `arena/` 的当前行为与数值口径）
> 归属：李辰钊（Arena / 系统）
> 上游契约：同目录 `Danio_Arena设计规范.md`、`../core/核心机制与数据流.md`、`../../../docs/参数总表.json`；接口侧见 `../api/API与系统工程.md` 与 `../api/API接口.md`
> ⚠️ 本文件描述**实现现在是什么样**，不等于**设计已如此规定**。凡上游文档未定义的数值与语义，状态一律为 `草案待确认`，
> 逐条列在 `research/notes/arena-api-决策认领表.md`，须经双方认领后写进上游文档才能升为契约。
> **未认领的数值不得进论文与正式实验。**

**与同目录 `Danio_Arena设计规范.md` 的分工：规范讲"应该怎样"（契约），本文件讲"现在怎样"（实现与其契约状态）。两者冲突时以规范为准，并以本文件 §7 / §10 记录收敛路径。**

代码位置：`src/evogenesis/arena/{config,entities,sensing,policies,env}.py`、`configs/default_arena.yaml`、`tests/test_arena.py`
本文档回答一个问题：**规范的规则落到代码里究竟变成了什么，以及哪些地方规范没写、代码却已经定型。**

**事实来源优先级：代码 > `configs/default_arena.yaml` > 本文档。** 本文档只做映射与记录，不发明规则；与代码冲突以代码为准（发现冲突请直接改本文档）。

**上游参数表**：`../../../docs/参数总表.json`（46 项 + `missing_required` 14 项）是本文档全部参数交叉引用的目标路径；§2.1 / §2.2 的「收录」列与 §2.3-2 的结论按该表核对（`sensing_radius` / `sensing_fov_degrees` / `predator_turn_rate` 均在表内，Arena 侧收录量 **13**）。

---

## 1. 模块清单

| 文件 | 职责 | 行数 | 对外接口 |
|---|---|---|---|
| `src/evogenesis/arena/config.py` | 冻结参数的数据类镜像（`WorldConfig` / `PopulationConfig` / `SensingConfig` / `EnergyConfig` / `GrowthConfig` / `ActorDefaults` / `ArenaConfig`），全部 `frozen=True` | 81 | `ArenaConfig()` |
| `src/evogenesis/arena/entities.py` | 实体：`Entity`（基类，含 `advance`）、`Fish`、`Prey`、`Predator`、`Obstacle`（含 `contains`） | 69 | 数据类；`Entity.advance()`、`Obstacle.contains()` |
| `src/evogenesis/arena/sensing.py` | 冻结 12 维感知编码器；`SENSORY_DIM = 12`、`DIM_NAMES`（索引对齐的可读名）、`nearest_predator_relative_size()`（编码器与 env 的**共用口径**） | 164 | `observe(...)`、`nearest_predator_relative_size(...)` |
| `src/evogenesis/arena/policies.py` | 三条透明规则策略：`ExpertPolicy`（模仿学习教师）、`PreyPolicy`（游走）、`PredatorPolicy`（巡游 / 追击 + 滞回） | 95 | `ExpertPolicy.__call__(obs)`、`PreyPolicy.act(rng, ...)`、`PredatorPolicy.plan(...)` |
| `src/evogenesis/arena/env.py` | `DanioArena` 主循环：运动 / 感知入口 / 能量 / 捕食（双向）/ 事件 / episode 终止 / 每鱼记录；`Event`、`StepResult` | 372 | `reset()`、`step(actions)`、`observe(fish_id)`、`per_fish_log()`、`.events` |
| `configs/default_arena.yaml` | 参数**唯一事实来源**（`config.py` docstring 明确此约束）；当前**无任何代码读取它**（见 §2.3） | 25 | — |
| `tests/test_arena.py` | 15 项冒烟 + 单元 + 回归测试；`KNOWN_EVENTS` 是事件词表的**机器可读权威名单** | 212 | — |

`src/evogenesis/arena/__init__.py` 为空（无 re-export）；调用方一律从子模块显式导入。

---

## 2. 参数表（代码 ↔ `configs/default_arena.yaml` 逐项对齐）

`config.py` 的 docstring 声明：

> Defaults mirror `configs/default_arena.yaml` (frozen values, docs/参数总表.json). All numbers MUST stay in sync with that file; the config object exists so experiments can override knobs without touching the frozen defaults.

下表逐项核对这一声明。

### 2.1 `WorldConfig` / `PopulationConfig` / `SensingConfig` / `EnergyConfig`

| 代码字段 | 代码默认值 | YAML 键 | YAML 值 | 一致 | `../../../docs/参数总表.json` 收录 |
|---|---|---|---|---|---|
| `world.width` | 100.0 | `world.width` | 100.0 | ✅ | ✅ `world_width` |
| `world.height` | 60.0 | `world.height` | 60.0 | ✅ | ✅ `world_height` |
| `world.hz` | 20 | `world.hz` | 20 | ✅ | ✅ `sim_hz` |
| `world.episode_steps` | 600 | `world.episode_steps` | 600 | ✅ | ✅ `episode_steps` |
| （无对应字段） | — | `world.episode_seconds` | 30 | ⚠️ YAML 独有 | ✅ `episode_seconds` |
| `population.n_fish` | 12 | `live_demo.fish` | 12 | ✅（键名不同） | ✅ `live_fish` |
| `population.n_prey` | 24 | `live_demo.prey` | 24 | ✅（键名不同） | ✅ `live_prey` |
| `population.n_predators` | 3 | `live_demo.predators` | 3 | ✅（键名不同） | ✅ `live_predators` |
| `population.n_obstacles` | 6 | `live_demo.obstacles` | 6 | ✅（键名不同） | ✅ `live_obstacles` |
| `sensing.radius` | 18.0 | `sensing.radius` | 18.0 | ✅ | ✅ `sensing_radius` |
| `sensing.fov_degrees` | 220.0 | `sensing.fov_degrees` | 220.0 | ✅ | ✅ `sensing_fov_degrees` |
| `energy.e_max` | 1.0 | `energy.e_max` | 1.0 | ✅ | ❌ |
| `energy.base_cost_per_step` | 0.0008 | `energy.base_cost_per_step` | 0.0008 | ✅ | ❌ |
| `energy.movement_cost_scale` | 0.0015 | `energy.movement_cost_scale` | 0.0015 | ✅ | ❌ |
| `energy.food_reward` | 0.12 | `energy.food_reward` | 0.12 | ✅ | ❌ |

`world.dt` 是派生属性：$dt = 1/hz = 0.05$ s。

### 2.2 `GrowthConfig` / `ActorDefaults`

| 代码字段 | 代码默认值 | YAML 键 | YAML 值 | 一致 | `../../../docs/参数总表.json` 收录 | 性质 |
|---|---|---|---|---|---|---|
| `growth.initial_size` | 1.0 | `growth.initial_size` | 1.0 | ✅ | ❌ | 实现值 |
| `growth.max_size` | 2.5 | `growth.max_size` | 2.5 | ✅ | ❌ | 实现值 |
| `growth.capture_size_ratio` | 1.25 | `growth.capture_size_ratio` | 1.25 | ✅ | ✅ `capture_size_ratio` | 已进表，`status=proposed_change`（规范 §8 当前取值 $\kappa = 1.25$，待 play-test 标定） |
| `growth.capture_radius` | 1.2 | `growth.capture_radius` | 1.2 | ✅ | ❌ | 实现值 |
| `growth.turn_inertia_scale` | 0.35 | `growth.turn_inertia_scale` | 0.35 | ✅ | ❌ | 实现值（$k_{turn}$） |
| `growth.biomass_to_size_gain` | 0.02 | **缺失** | — | ❌ | ❌ | **MVP 标定旋钮**（规范只说"缓慢增长并设上限"，未给数值） |
| `actors.prey_speed` | 0.35 | **缺失**（无 `actors:` 块） | — | ❌ | ❌ | **MVP 标定旋钮** |
| `actors.prey_size_min` | 0.30 | **缺失** | — | ❌ | ❌ | **MVP 标定旋钮** |
| `actors.prey_size_max` | 0.60 | **缺失** | — | ❌ | ❌ | **MVP 标定旋钮** |
| `actors.predator_size` | 2.0 | **缺失** | — | ❌ | ❌ | **MVP 标定旋钮** |
| `actors.predator_cruise_speed` | 0.40 | **缺失** | — | ❌ | ❌ | **MVP 标定旋钮** |
| `actors.predator_chase_speed` | 0.65 | **缺失** | — | ❌ | ❌ | **MVP 标定旋钮** |
| `actors.predator_detection_radius` | 15.0 | **缺失** | — | ❌ | ❌ | **MVP 标定旋钮** |
| `actors.predator_release_radius` | 22.0 | **缺失** | — | ❌ | ❌ | **MVP 标定旋钮**（滞回：超出此半径即丢失目标） |
| `actors.predator_turn_rate` | 5.0 | **缺失** | — | ❌ | ✅ `predator_turn_rate` | 单位 **rad/s**，见 §3.2 S14 / 认领表 A10。**已进 `../../../docs/参数总表.json`，是 `actors.*` 中唯一进表的项** |
| `actors.obstacle_radius_min` | 1.5 | **缺失** | — | ❌ | ❌ | **MVP 标定旋钮** |
| `actors.obstacle_radius_max` | 3.5 | **缺失** | — | ❌ | ❌ | **MVP 标定旋钮** |
| `actors.wander_turn_std` | 0.8 | **缺失** | — | ❌ | ❌ | **MVP 标定旋钮**（单位 **rad/s**） |

### 2.3 三条必须写明的结论

1. **`ActorDefaults` 整块（12 项）与 `growth.biomass_to_size_gain` 在 `configs/default_arena.yaml` 中不存在。** 即共 **13 项**未进 YAML。`config.py::ActorDefaults` 的 docstring 自己声明："MVP calibration knobs -- Danio_Arena设计规范.md says final values come from play-testing"，`biomass_to_size_gain` 也带 `# MVP calibration knob (play-test later)` 注释。因此这 13 项**不是冻结量**，报告引用时必须标注为"实现取值，待 play-test 标定"。
2. **`../../../docs/参数总表.json` 现收录 Arena 侧 13 个量**：`world_width` / `world_height` / `sim_hz` / `episode_seconds` / `episode_steps` / `live_fish` / `live_prey` / `live_predators` / `live_obstacles` / `capture_size_ratio` / `sensing_radius` / `sensing_fov_degrees` / `predator_turn_rate`。（该表另有 `sensory_dim` / `action_dim` / `body_length_mm` 等，属 DanioNet 侧契约，不是 Arena 世界参数。）`energy.*` 4 项、`growth` 除 `capture_size_ratio` 外的 4 项、`actors` 除 `predator_turn_rate` 外的 11 项**仍未进表** —— 它们与 `config.py` docstring 中"frozen values"的措辞有落差。**按代码口径处理：只有上表"`../../../docs/参数总表.json` 收录 = ✅"且该表 `status=confirmed` 的行才可称为冻结量；`capture_size_ratio` 虽已收录，但其 `status=proposed_change`，按此口径暂不算冻结量。**
3. **`configs/default_arena.yaml` 目前没有任何代码读取它。** 全仓库对 `default_arena` 的引用只有两处非执行字符串：`api/schemas.py::SessionCreate.arena_config_path` 的默认值，以及 `arena/config.py` docstring 的注释。`DanioArena.__init__` 在 `config=None` 时构造 `ArenaConfig()`，即**用 Python 硬编码默认值跑仿真**，YAML 是并行的、可能漂移的副本。这一点与"所有数值必须由 config 读取"（`../../../docs/参数总表.json` 末行）的要求尚未闭环，属已知实现债（见 §8 M8、`../api/API接口.md` §11 L2、认领表 B7）。

---

## 3. 规则 → 代码映射

### 3.1 规范节号 → 文件 / 函数 → 要点

| 规范 § | 主题 | 代码位置 | 要点 |
|---|---|---|---|
| §1 | 定位 | `env.py::DanioArena` | Arena 既是行为测量环境，也是现场 Demo 数据源；不追求流体动力学 |
| §2 | 世界 | `config.py::WorldConfig`、`WorldConfig.dt` | $100 \times 60$ 连续二维；20 Hz（$dt = 0.05$ s）；600 steps/episode。位置裁剪到 $[0,W] \times [0,H]$ |
| §3 | Live 默认对象 | `config.py::PopulationConfig`、`env.py::reset()` | 12 fish / 24 prey / 3 predators / 6 obstacles；由 `tests/test_arena.py::test_population_counts_match_frozen_defaults` 守护 |
| §4 | 视野 | `sensing.py::observe()`、`sensing.py::nearest_predator_relative_size()`、`DanioArena.observe(fish_id)` | 有限半径 + 有限 FOV；左右通道按 $\mathrm{sign}(\sin(rel))$ 划分；强度 $1 - d/r$ 线性衰减，每通道截断到 1.0；无全图信息 |
| §5 | 连续运动 | `Entity.advance()`、`DanioArena._omega_eff()`、`env.py::step()` 鱼循环 | $\theta \mathrel{+}= \omega_{eff} \cdot dt$，**位移用新航向**；$\omega_{eff} = \omega / (1 + k_{turn}(size-1))$；越界裁剪不反弹 |
| §6 | Energy / Hunger | `env.py::step()` 能量段、`config.py::EnergyConfig` | $E' = \mathrm{clip}(E - C_{base} - C_{move}v^2 + R_{food}\cdot\mathbb{1}[\text{本步捕获}], 0, E_{max})$；$H = 1 - E/E_{max}$；$E \le 0$ 判死 |
| §7 | Growth | `env.py::step()` 捕食段 | `biomass += prey.size`；`size = min(max_size, size + gain * prey.size)`；"大"同时带来更大 prey 与更大转向惯性。`biomass` 只写不读（认领表 A4） |
| §8 | Predation | `env.py::step()`（鱼吃猎物 + 捕食者吃鱼两段） | 双向同一判据：$d < r_{capture}$ **且** $size_{hunter} > \kappa \cdot size_{target}$ |
| §9 | PredatorPolicy | `policies.py::PredatorPolicy.plan()` + `env.py::step()` 捕食者段 | 巡游 → 追击 → 避障 → 恢复巡游；滞回由 `release_radius` 实现；转向速率限制在 env 不在 policy |
| §10 | PreyPolicy | `policies.py::PreyPolicy.act()` + `env.py::_steer_away_from_obstacles(prey, gain=2.0)` | 随机游走 + 避障；**MVP 无主动逃跑**（不被鱼感知） |
| §11 | ExpertPolicy | `policies.py::ExpertPolicy.__call__()`、`src/evogenesis/api/session.py::Session.advance()` | 仅用于模仿学习与现场 Demo 驱动；不参与 DanioNet scoring |
| §12 | 风险—收益冲突 | （未实现） | 高价值 prey 靠近 predator 等场景布置属后续迭代 |
| §13 | 事件日志 / 每鱼记录 | `env.py::per_fish_log()`、`entities.py::Fish` 缓冲字段 | 规范列 11 项，代码实现 10 项（1 项已声明未实现，见 §6） |

### 3.2 规范未逐字规定、但代码已定型的补充细节

以下细节规范没有写死，是实现的既定选择。**改动它们等于改动 Arena 行为，须同步 §10 变更纪律。** 标 ⚠️ 者为与 §10 变更纪律强相关、须双方同步的条目。

| # | 细节 | 代码事实 |
|---|---|---|
| S1 | **动作语义** | `actions[fid] = (ω, v)` 先各自裁剪：$\omega \in [-1,1]$、$v \in [0,1]$。`v` 是**世界单位/秒**的速度（不是归一化档位）：每步位移 $v \cdot dt = 0.05v$ 世界单位，30 s 内 $v=1$ 的鱼最多走 30 单位（世界宽 100） |
| S2 | **转向惯性施加位置** | 先裁剪 $\omega$ 到 $[-1,1]$，再除以 $1 + k_{turn}(size-1)$，因此大鱼的**有效**角速度上限小于小鱼 |
| S3 | **避障探测** | `_steer_away_from_obstacles()` 在 $pos + speed \cdot \hat{e}(\theta) \cdot 3.0$ 处做**前视点**探测；命中第一个障碍即转向并 `return`（不累加多障碍）；转角为 $\mathrm{sign}(diff) \cdot gain$（开关式，不按夹角比例），`gain` 默认 0.5（鱼 / 捕食者），猎物显式传 2.0 |
| S4 | **碰撞判定** | `obstacle.contains(fish.pos, 0.1)`：把鱼的碰撞半径视作常数 0.1，**与 `fish.size` 无关**；每个鱼每步**最多一条**碰撞事件（命中即 `break`），`collisions += 1` 同步自增 |
| S5 | **捕食尝试唯一性** | 鱼每步遍历猎物时，命中第一个 $d < r_{capture}$ 的猎物即处理并 `break` —— 每鱼每步**最多一条** `capture_attempt` 或 `prey_captured` |
| S6 | **`encounters` 语义** | 只在 $d < r_{capture}$ 时自增（近距接触），不是"看见"的计数 |
| ⚠️ S7 | **`predator_encounters` 语义** | **目标获取计数**，不是接触计数：捕食者 `plan()` 得到的目标与上一帧不同（含 `None → X` 与 `X → Y`）时对**新目标** `+= 1`。实现于 `env.py` 捕食者段：`if target is not None and target != prev_target: self.fish[target].predator_encounters += 1`。候选集只含存活鱼，故死鱼不会被计入 |
| S8 | **出生空地采样** | `_free_spot(clearance)`：拒绝采样至多 200 次，位置为 $U(0,W) \times U(0,H)$，要求对 `self.obstacles` 中所有障碍 `not contains(pos, clearance)`；200 次仍失败则回退世界中心 $(W/2, H/2)$。各类实体 clearance：fish 2.0、prey 1.0、predator 3.0、obstacle $r + 1.0$ |
| ⚠️ S9 | **出生顺序与随机消耗** | `reset()` 顺序为 障碍 → 鱼 → 猎物 → 捕食者。**障碍就地逐个生成**：`reset()` 先 `self.obstacles = []`，再由 `_spawn_obstacles()` 逐个 `append`，因此**同一 reset 内的障碍互不重叠**，且第二次 `reset()` 与第一次完全一致。每个实体的随机消耗为"若干次拒绝采样 + 1 次航向/尺寸 uniform"，**采样次数本身进入 RNG 消费路径**（见 §5 D5） |
| S10 | **猎物初始尺寸** | $U(0.30, 0.60)$ |
| S11 | **障碍尺寸** | 半径 $U(1.5, 3.5)$ |
| S12 | **猎物游走** | `PreyPolicy.act()`：$\omega \sim N(0, 0.8)$，裁剪到 $\pm 3.0$；速度恒为 `prey_speed = 0.35`。`PreyPolicy.avoid_gain = 2.5` **字段未被 env 使用**（env 不传 `obstacle_rel_bearing`，改由 `_steer_away_from_obstacles(prey, gain=2.0)` 处理避障）——该字段是死参数（见 §7 F2、§8 M6） |
| S13 | **捕食者滞回** | `plan()`：旧目标仍在 `fish_pos`（存活）且距离 $\le$ 22 → 保持锁定并全速追击；否则在 15 半径内取**最近**存活鱼；无候选则返回 `(None, 当前航向, 0.40)` |
| ⚠️ S14 | **捕食者转向速率限制** | env 侧对期望航向差做 $\mathrm{clip}(diff, -max\_turn, +max\_turn)$，其中 $max\_turn = \texttt{predator\_turn\_rate} \cdot dt = 5.0 \times 0.05 = 0.25$ rad/step。这是"转向速率限制在 env 而非 policy"的具体含义，由配置项 `predator_turn_rate`（rad/s）给出，与 0.25 rad/step 等价（认领表 A10） |
| S15 | **捕食者命中后行为** | 击杀后立刻 `pred.target_fish_id = None`；**同一捕食者因此不会**为自己的击杀发射 `arena.escape`（旧目标已死，见 S17 的条件），但**其他**也锁定该鱼的捕食者会（此时那条鱼仍存活） |
| S16 | **捕食者不参与能量/成长** | `Predator` 无 `energy` 字段；捕食者不饿、不长、不参与 leaderboard |
| ⚠️ S17 | **`arena.escape` 的真实触发条件** | `plan()` 返回的目标与 `pred.target_fish_id` 不同**且旧目标仍存活**时，才发射事件并对该鱼 `escape_successes += 1`。**旧目标已死亡（饿死，或被另一只捕食者吃掉）时既不发事件也不计数**，由 `test_dead_fish_not_credited_escape` 守护。指标口径须按此理解 |
| S18 | **`Predator.alive` 恒为真** | 全仓库没有任何 `pred.alive = False`（`.alive = False` 只出现在 prey 与 fish 上）；`step()` 捕食者段的 `if not pred.alive: continue`、以及 `sensing.nearest_predator_relative_size()` 里的 `if d.alive` 过滤都是**死分支**（保留不影响行为，改它也不改变结果）。见 §8 M7 |
| S19 | **`arena.energy_depleted` 的步数语义** | payload 的 `survival_steps` 取**自增之前**的值，即"死前已存活步数"；`Fish.survival_steps` 每步末对存活鱼自增 |
| ⚠️ S20 | **looming 记账口径** | `_prev_predator_rel` 在所有实体移动**之后**统一刷新，取值调用**编码器同一个函数** `sensing.nearest_predator_relative_size(fish, predators, radius, fov_degrees)`（＝"视野与半径内**最近**可见天敌"的 $rel$ 尺寸 $\min(pred.size / fish.size / 2.5, 1.0)$）；env 与编码器共用这一口径，`looming = clamp(10 \cdot \Delta rel, 0, 1)` 的差分才是真正的变化率。**实测（重要）**：在现有调用序下（`observe()` 总在步界被调用，而 `_prev_predator_rel` 在**上一步末尾**用同一函数刷新），$pred\_rel$ 与 $prev$ 由构造必然相等 ⇒ **`looming_rate` 通道除 `reset()` 后的第一次观测外恒为 0**（`reset()` 把 `Fish._prev_predator_rel` 重建为 0.0，故首帧可能出现 1 个饱和值 1.0）。实测 seed 250927：首帧 12 条鱼中 2 条为 1.0，其后 40 步全 0。⇒ 该通道目前**不携带信息**，属待认领（§7 A1）与待修的实现缺口（§8 M13） |
| ⚠️ S21 | **`step()` 的 done 守卫** | `__init__` / `reset()` 置 `self._episode_ended = False`；episode 结束后 `step()` **立即返回** `StepResult(self.step_idx, True, [])`（不再推进、不再发事件）。因此 ① `step_idx` 不会越过 600；② `arena.episode_end` 每次 episode **只发一次**；③ 结束后重复 `step()` 是幂等空转。由 `test_step_after_episode_end_is_inert` 守护 |
| ⚠️ S22 | **团灭判定** | `extinct = bool(self.fish) and all(not f.alive for f in self.fish.values())`；`done = step_idx >= episode_steps or extinct`。`bool(self.fish)` 使**空种群不判团灭**（否则空列表上 `all([]) == True` 会让 `fish = {}` 在第一步立刻结束）。`test_episode_terminates_at_max_steps` 覆盖正常路径；**空种群分支目前无测试**（§9 未覆盖项） |
| S23 | **死鱼不再感知** | `step()` 鱼循环、looming 段均 `if not fish.alive: continue`；`DanioArena.observe(fish_id)` 本身**不校验存活**，对死鱼仍会返回向量（其能量为 0） |

---

## 4. 事件词表 v1

### 4.1 信封

`Event` 是 `@dataclass(frozen=True)`，字段顺序 `seq, step, type, payload`；`Event.to_dict()` 输出：

```json
{"seq": 3, "type": "arena.prey_captured", "step": 42, "payload": { ... }}
```

| 字段 | 语义 |
|---|---|
| `seq` | 全局发射序，**从 1 起**，在 `_emit()` 内分配；`reset()` 归零 |
| `step` | 发射时的 `DanioArena.step_idx`（`step_idx` 在该 `step()` 末尾才自增，故步内事件与本步同号） |
| `type` | 点分层事件名，见 §4.2 |
| `payload` | 事件专属字段，见 §4.2 |

`StepResult.events` 是**本步新增事件**，返回前按 `seq` 排序；`DanioArena.events` 累积**整局**全部事件（不清理，直到 `reset()`）。

### 4.2 词表 v1（8 项，点分层 `arena.*`）

| # | `type` | 触发时机 | payload |
|---|---|---|---|
| 1 | `arena.spawn` | `reset()` 为每个 fish / prey / predator 各发一次（$12+24+3 = 39$ 条） | `entity_id` |
| 2 | `arena.capture_attempt` | 鱼与某猎物 $d <$ `capture_radius`(1.2) 且尺寸比 $\le \kappa$(1.25)；每鱼每步至多一条 | `fish_id, prey_id, distance, size_ratio, threshold, capture_radius, result` |
| 3 | `arena.prey_captured` | 鱼吃掉猎物（$d < 1.2$ 且 $size_{fish} > 1.25 \cdot size_{prey}$） | `fish_id, prey_id, distance, size_ratio, food_reward` |
| 4 | `arena.escape` | 捕食者**换掉**已锁定目标，且**该目标仍存活**（见 S17） | `fish_id, threat_source` |
| 5 | `arena.collision` | 鱼撞障碍（每鱼每步最多一次，命中即 `break`） | `fish_id, obstacle_id` |
| 6 | `arena.energy_depleted` | 能量结算后 $E \le 0$（饿死） | `fish_id, survival_steps` |
| 7 | `arena.fish_captured` | 捕食者吃掉鱼 | `fish_id, predator_id, survival_steps` |
| 8 | `arena.episode_end` | `step_idx >= 600` 或**非空种群**全部死亡（S22）；每 episode **恰好一次**（S21） | `steps, fish_alive, prey_remaining` |

**字段口径速记**

- `distance` / `size_ratio` 在发射前 `round(..., 3)`；`threshold` 与 `capture_radius` 直接取 config 原值（1.25 / 1.2），便于离线核对判据。
- `arena.capture_attempt.result` 在**当前实现下只会是字符串 `"too_small_to_eat"`**：距离不足的猎物在判据前就被 `continue` 跳过，不产生任何事件；尺寸达标的猎物直接走 `arena.prey_captured`。**因此草案里的 `"too_far"` 是永远不会出现的值**（见 §4.4）。
- `arena.escape.threat_source` 是**捕食者实体 id**（`predator_NN`），不是类型名。
- `arena.fish_captured.survival_steps` 与 `arena.energy_depleted.survival_steps` 同口径：发射时的 `Fish.survival_steps`（未自增）。
- **障碍不发射 spawn**：只有 fish / prey / predator 三类活动实体入事件。障碍的位置与半径、以及所有实体的实时位置/尺寸，走 snapshot（`GET /v1/sessions/{session_id}/snapshot`）而非事件流。
- `arena.episode_end` 的 `steps` 取 `step_idx`（此时已自增）：正常跑满恒为 600；**团灭提前结束时小于 600**（实测：灭绝后的第一步即结束，`steps` 为该步号）。
- **`escape_successes` 与 `predator_encounters` 都是"计数而非事件"**：它们只出现在 `per_fish_log()` / `FishCard.metrics` / leaderboard 侧，事件流里没有对应条目。

### 4.3 与 `../core/核心机制与数据流.md` §5.1 的关系

- `../core/核心机制与数据流.md` §5.1 已定为**设计侧参考**（该文件状态行注明"权威词表见 arena"，非待冻结）：它列"应有哪些事件"、命名 `arena.<event>`、**只增不删**。**事件词表的唯一权威是本文档 §4.2 + `tests/test_arena.py::KNOWN_EVENTS`（v1，已生效）**，字段名只在 §4.2 维护一套。
- **机器可读权威名单是 `tests/test_arena.py::KNOWN_EVENTS`**，由 `test_all_events_in_known_vocabulary` 守护（断言：整局事件的 `type` 均以 `arena.` 开头且属于该集合）。任何一方改词表都必须同时改这个集合。
- 命名风格与 WS 消息 `type` 的点分层约定（`../api/API与系统工程.md` §4.1 R11）一致：**磁盘与推送共用同一词表**。
- 词表状态：**v1 已生效**（池伟豪确认 2026-09-26；见 `research/notes/契约决策记录.md`）。本文件 §4.2 + `tests::KNOWN_EVENTS` 为事件词表的唯一权威。

### 4.4 与草案实例 `schemas/examples/event_log_example.jsonl` 的差异

该实例按 §5.1 **草案**生成，早于当前实现。**现状核对（已部分对齐，但未闭环）**：

| 实例行 | 实例现状 | 实现口径 | 状态 |
|---|---|---|---|
| 1 | `arena.spawn`, payload `{entity_id}` | `{entity_id}`（无坐标/尺寸；位置尺寸走 snapshot） | ✅ 键名已对齐 |
| 2 | `arena.capture_attempt`, `result: "too_small_to_eat"`, `size_ratio: 1.28`, `threshold: 1.25` | `capture_attempt` 仅在 `size_ratio ≤ κ` 时发射 | ❌ **判据自相矛盾**：`1.28 > 1.25` 应走 `prey_captured`，该行非法 |
| 3 | `arena.prey_captured`, `{fish_id, prey_id, distance, size_ratio, food_reward}` | 同字段 | ✅ 逐字对齐 |
| 4 | `arena.escape`, `{fish_id, threat_source}` | `{fish_id, threat_source}` | ✅ 字段已对齐（`reaction_latency_steps` 已移除） |
| — | 共 4 行 | 实现有 8 类 | ❌ **缺** `arena.collision` / `arena.energy_depleted` / `arena.fish_captured` / `arena.episode_end` |

**动作（二选一，尚未执行；责任人李辰钊）**：

- **首选**：依 v1 词表**重生成** `schemas/examples/event_log_example.jsonl`，覆盖 8 类事件并与 `tests/test_arena.py::KNOWN_EVENTS` 同源；同步更新 `schemas/examples/README.md` 的 provenance 段。**现状：未重生成**（仍 4 行，第 2 行判据矛盾未除）。
- **备选**：**降级**为"字段形状示意"，在文件头（或 README）显式标注"该实例仅示意信封形状，**字段名与取值不以本文为准**，以 `src/evogenesis/arena/Danio_Arena实现说明.md` §4.2 为准"，并保留"待重生成"标记。**现状：未降级。**

在该实例闭环（重生成或降级）前，**不得被代码依赖**（`schemas/examples/README.md` 已声明"冻结前不可被代码依赖"）。

---

## 5. 确定性 / 复现判据

**判据：同一 `(ArenaConfig 取值, master_seed)` ⇒ 逐事件一致的事件序列与逐字段一致的实体状态。** 该判据由 D1（唯一随机源）、D2（`reset()` 幂等）与 D3–D5 的消费顺序共同保障。

| # | 机制 | 代码事实 |
|---|---|---|
| D1 | **唯一随机源** | `np.random.default_rng(master_seed)`。`arena/` 内**不出现** `import random`、全局 `np.random.*` 调用、或任何时间/OS 熵来源（全仓 `import random` 仅存在于 `core/seed.py`、`evolution/evolution.py`、`genome/genome.py`，均不在 Arena 路径上） |
| ⚠️ D2 | **`reset()` 幂等** | `reset()` **重建** RNG（`np.random.default_rng(self.master_seed)`），并**先清空 `self.obstacles`** 再就地逐个生成障碍（S9）。因此同一 arena 反复 `reset()` 得到**逐字段一致**的初始局面（障碍位置与半径、每条鱼的位置/航向、每个猎物的位置/尺寸）。由 `test_reset_idempotent_on_same_instance` 守护（同时断言障碍的 `pos` 与 `radius`） |
| D3 | **reset 内消费顺序** | 障碍 → 鱼 → 猎物 → 捕食者。每障碍：1 次半径 uniform + `_free_spot`（≥1 次）；每鱼：`_free_spot(2.0)` + 1 次航向 uniform；每猎物：`_free_spot(1.0)` + 1 次航向 uniform + 1 次尺寸 uniform；每捕食者：`_free_spot(3.0)` + 1 次航向 uniform |
| D4 | **每步唯一消费点** | 猎物游走：每条**存活**猎物 1 次 `rng.normal(0.0, 0.8)`（`PreyPolicy.act`）。鱼、捕食者、障碍、looming 记账**均不消费 RNG** |
| D5 | **拒绝采样进入消费路径** | `_free_spot` 的采样**次数**取决于当前（本局）障碍布局，因此它是 RNG 消费路径的一部分 —— 一旦改动障碍数量/半径范围/clearance，后续所有实体的随机流都会平移。**这是复现性最脆弱的一环**：改动障碍数量/半径范围/clearance 会使后续所有实体的随机流整体平移，同一 seed 下的初始世界随之改变，历史基线不可直接对比 |
| D6 | **推进粒度的无关性** | `Session.advance(steps=k)` 就是 `k` 次 `step()`；每一步内的 RNG 消费只由**该步的状态**决定（D4：存活猎物数 × 1 次 normal）。因此"同一 seed 下推进到第 $k$ 步的状态"与"分几次调用推进到第 $k$ 步"无关（在 600 步上限内）。**注意**：这条只说粒度无关，不代表 `step()` 不消费 RNG |
| D7 | **测试守护** | `test_reset_deterministic_same_seed`（同 seed 实体一致）、`test_reset_different_seed_differs`（异 seed 不同）、`test_reset_idempotent_on_same_instance`（**同一实例二次 reset 一致**） |

**注意**：`DanioArena.__init__` 只接受 `master_seed`，`ArenaConfig` 通过构造参数传入；`SessionCreate.arena_config_path` 目前**未被读取**（见 `../api/API接口.md` §7.2）。要复现一局，必须记录 `ArenaConfig` 的**实际取值**（而非 YAML 路径）。

---

## 6. 每鱼记录字段表（规范 §13）

`DanioArena.per_fish_log()` 返回 `{fish_id: 记录}`，**包含全部 12 条鱼（含已死鱼）**。

| 规范 §13 声明 | `per_fish_log()` 键 | 来源字段 | 状态 |
|---|---|---|---|
| generation | `generation` | `Fish.generation`（恒 0，未接演化） | ✅ |
| encounters | `encounters` | `Fish.encounters` | ✅ 语义为"$d < r_{capture}$ 的近距接触数"（S6） |
| captures | `captures` | `Fish.captures` | ✅ |
| predator encounters | `predator_encounters` | `Fish.predator_encounters` | ✅ **已实现**：捕食者**获得新目标**时 +1（S7）。由 `test_predator_encounter_recorded_on_acquisition` 守护。⚠️ 口径是"被锁定次数"而非"近距遭遇次数"，属待认领（§7 A8 邻域） |
| escape successes | `escape_successes` | `Fish.escape_successes` | ✅ 口径见 S17（仅对**仍存活**的丢失目标计数） |
| collisions | `collisions` | `Fish.collisions` | ✅ |
| energy trajectory | `energy_trajectory` | `Fish.energy_trace` | ✅ 能量结算后追加（**在死亡判定之前**）。故对**存活鱼**与**被捕食者吃掉的鱼**有 `len(energy_trajectory) == survival_steps`；对**饿死鱼**多 1 条（该步写了 trace 但未自增 `survival_steps`）。`test_per_fish_log_completeness` 只在无死亡场景（10 步）覆盖此断言 |
| size trajectory | `size_trajectory` | `Fish.size_trace` | ✅ 与 `energy_trajectory` 同步追加（同样多 1 条于饿死鱼） |
| survival steps | `survival_steps` | `Fish.survival_steps` | ✅ |
| motor commands | `motor_commands` | `Fish.motor_log`（`(ω, v)` 元组列表，**裁剪后**的值） | ✅ |
| **selected neural activity snapshots** | — | — | ❌ **未实现**：规范 §13 声明的最后一项需 DanioNet 接入，当前 `Fish` 无对应缓冲区 |

`per_fish_log()` **不含**位置 / 航向 / 尺寸的逐帧轨迹 —— 那属于 snapshot（`../api/API接口.md` §1.8）与后续的 trajectory 落盘（`../core/核心机制与数据流.md` §4）。

---

## 7. 未认领的实现决定（指向 `research/notes/arena-api-决策认领表.md` A 节）

> **本节是本文档的契约状态核心。** 以下数值与语义由实现先于设计落地，`Danio_Arena设计规范.md` 与 `../../../docs/参数总表.json` 未定义；在认领表被回答、结论写进上游文档之前，状态一律为 **`草案待确认`**，**不得写进论文与正式实验**。

| 认领编号 | 未认领的内容 | 本文档对应节 | 实现现状 |
|---|---|---|---|
| **A1** | 12 维感官编码的归一化公式（线性衰减、$rel$ 尺寸、looming 系数 10、左右分侧规则） | §4、S20 | 已实现、已固化；**looming 通道在现状调用序下恒 0**（S20 实测），须一并认领 |
| **A2** | 捕食几何：`capture_radius = 1.2`（纯距离，无朝向/口部角度）、$\kappa = 1.25$ | §2.1、§2.2、§3.1 §8 | $\kappa$ 已进 `../../../docs/参数总表.json`；半径 1.2 未认领 |
| **A3** | 能量四系数：`e_max` / `base_cost_per_step` / `movement_cost_scale` / `food_reward` | §2.1 | 已实现，未进 `../../../docs/参数总表.json` |
| **A4** | 生长：`initial_size` / `max_size` / `biomass_to_size_gain`；`biomass` 为只写不读的镜像量 | §2.2、§3.1 §7 | 已实现；实测单局 size 几乎不动 |
| **A5** | `actors` 整组 12 项（含 `predator_turn_rate`） | §2.2 | 已实现；YAML 无 `actors:` 段，未进 `../../../docs/参数总表.json` |
| **A6** | 边界策略：clamp 到 $[0,W] \times [0,H]$（贴墙卡住、持续耗能），不反弹、不出界即死 | §3.1 §2、§3.2 S1 | 已实现 |
| **A7** | 碰撞语义：仅"鱼–障碍"，重叠即**每步 +1**，无位移/能量后果，可穿模 | S4 | 已实现。⚠️ **实测：默认场景 5 个 seed × 600 步均为 0 次 `arena.collision`**（障碍互不重叠 + `_steer_away_from_obstacles` 生效）。该事件在当前默认场景下近乎不触发，指标意义需重新评估 |
| **A8** | escape 判定：**换目标**即算被弃目标"逃脱成功"（死亡导致的切换不计入） | S17 | 已实现（死鱼导致的切换不计入，见 S17）；"是否应改为逃出 `release_radius` 才算"待认领 |
| **A9** | 团灭提前结束：`step_idx >= 600` **或**非空种群全灭 → episode 结束 | S22 | 已实现；影响跨 episode 可比性 |
| **A10** | 天敌/猎物转向量纲：天敌统一为 `predator_turn_rate = 5.0` **rad/s**（等价原 0.25 rad/step），猎物 `wander_turn_std = 0.8` **rad/s** | S14、S20 邻域、§2.2 | 已实现；**数值等价，但单位口径本身待确认** |

另有两项**实现侧发现**，不属认领表原有编号，但同样不得在未确认前用于指标：

| # | 发现 | 证据 |
|---|---|---|
| F1 | **`looming_rate` 通道在现状下恒 0**（除 `reset()` 后首帧） | §3.2 S20 的实测；根因是"prev 在上一步末尾刷新"与"observe 在步界调用"使两者同源同值 |
| F2 | **`PreyPolicy.avoid_gain` 是死参数** | S12：`act()` 的 `obstacle_rel_bearing` 形参从未被 env 传入 |

---

## 8. MVP 边界（明确未做项）

| # | 未做项 | 说明 |
|---|---|---|
| M1 | 神经控制 | 鱼由外部 `actions` 驱动；DanioNet 推理未接入，`Fish.genome_id` 恒 `"unknown"`、`generation` 恒 0 |
| M2 | ~~`predator_encounters` 恒 0~~ | ✅ **已实现**：目标获取计数，见 S7 |
| M3 | selected neural activity snapshots | 规范 §13 最后一项，未实现（见 §6） |
| M4 | 规范 §12 风险—收益冲突场景 | 高价值 prey 靠近捕食者 / resource-scarce 抬升 hunger 的场景布置未做；`environment` 字段已进 API 但**不改变任何参数**（见 `../api/API接口.md` §7.2） |
| M5 | 猎物主动逃跑 | `PreyPolicy` 不感知鱼；规范 §10 的 "proximity avoidance" 目前只有避障版本 |
| M6 | `PreyPolicy.avoid_gain` | 死参数（S12、F2） |
| M7 | 捕食者能量 / 成长 / 死亡 | 捕食者恒存活、无代谢（S16、S18） |
| M8 | 配置加载 | YAML **不被读取**（§2.3）；`ArenaConfig` 硬编码 |
| M9 | 障碍物为非凸形状 | 障碍只用圆 `contains`，无多边形/复杂几何 |
| M10 | 流体动力学 | 规范 §1 已明确排除，非遗漏 |
| M11 | episode 内重生成猎物 | 猎物被吃光后不补充，也不触发结束（结束只看鱼） |
| M12 | 手动控制通路 | `Session.advance(use_expert=False)` 存在但**无端点暴露手动 action**（`release` 只给 `steps`/`use_expert`） |
| M13 | looming 通道无信息 | 见 S20 / F1：口径已统一，但整条通道在现状调用序下恒 0，等于 12 维里的第 9 维目前是常数 0；修法（在 `step()` 内、实体移动前后各取一次，或把 prev 改在步首读取）会改变 RNG 无关但会改变观测分布，需与 A1 一并认领 |
| M14 | `world.episode_seconds` 未进代码 | YAML 有 `world.episode_seconds: 30`，`WorldConfig` 无对应字段（§2.1 的 ⚠️ 行），故 `dt`/步数与它无关 |

---

## 9. 测试覆盖（`tests/test_arena.py`，15 项）

| # | 测试 | 守护的契约 |
|---|---|---|
| 1 | `test_reset_deterministic_same_seed` | D1/D3：同 seed 下鱼的 pos/heading、猎物的 pos/size 逐字段一致 |
| 2 | `test_reset_different_seed_differs` | 种子确实生效（防"seed 被忽略"的假确定性） |
| 3 | `test_obs_shape_and_ranges` | 12 维、有限、全在 $[0,1]$（§3.1 §4） |
| 4 | `test_population_counts_match_frozen_defaults` | 12 / 24 / 3 / 6（`../../../docs/参数总表.json` 冻结量） |
| 5 | `test_capture_grants_food_reward` | §3.1 §7 + §8：捕获后 `captures == 1`、猎物死亡、能量精确为 $0.5 - 0.0008 + 0.12 = 0.6192$（`abs=1e-9`） |
| 6 | `test_too_small_to_eat_attempt_logged` | §4.2 #2：`result == "too_small_to_eat"`，且猎物存活 |
| 7 | `test_starvation_death_event` | §4.2 #6：$E < C_{base}$ 时判死并发射 `arena.energy_depleted`，`fish_id` 正确 |
| 8 | `test_episode_terminates_at_max_steps` | §3.1 §2 + §4.2 #8：600 步 `done`，`payload["steps"] == 600` |
| 9 | `test_turn_inertia_reduces_bigger_fish_turning` | §3.1 §5：$\omega_{eff}$ 随 size 单调下降 |
| 10 | `test_all_events_in_known_vocabulary` | **§4.2 词表权威守护**：120 步内所有事件均以 `arena.` 开头且在 `KNOWN_EVENTS` 内 |
| 11 | `test_per_fish_log_completeness` | §6 字段齐全（含 `predator_encounters` 的**存在性**）+ 无死亡场景下轨迹长度一致 |
| **12** | `test_reset_idempotent_on_same_instance` | **D2**：同一实例二次 `reset()` 后，每条鱼的 pos、每个障碍的 pos **与 radius** 与首次完全一致 |
| **13** | `test_step_after_episode_end_is_inert` | **S21**：跑满 600 步后再 `step()` 仍 `done`、`step_idx` 保持 600、`arena.episode_end` 计数不增 |
| **14** | `test_dead_fish_not_credited_escape` | **S17**：把 `pred.target_fish_id` 指向一条已死鱼后 `step()`，该鱼 `escape_successes` 保持 0 且本步无 `arena.escape` |
| **15** | `test_predator_encounter_recorded_on_acquisition` | **S7**：捕食者从"无目标"切到目标鱼的下一步，该鱼 `predator_encounters >= 1` |

**未覆盖**（已知缺口）：`arena.collision` 的**触发**无专项测试；`arena.escape` 的"活鱼被换掉"正向分支无专项测试（只测了死鱼反向）；`arena.spawn` 恰为 39 条无测试；`_free_spot` 的 200 次回退分支无测试；**空种群不判团灭（S22）无专项测试**（`bool(self.fish)` 分支只在人工验证中跑过）；`observe()` 对死鱼仍返回向量（S23）无测试。

⚠️ 其中前两项**在默认场景下无法自然触发**（见附录实测：5 个 seed × 600 步的 `arena.collision` 与 `arena.escape` 均为 0），要补测试必须手工构造场景（如把鱼直接放到障碍上 / 手工指定 `pred.target_fish_id` 后让其换目标）。

---

## 10. 变更纪律

改下列任一内容，必须**同时**改对应文件，否则 CI 或契约会静默漂移。**代码 / 配置 / 测试 / 样例路径为仓库根相对；文档交叉引用为本文件所在目录相对。**

| 改动 | 必须同步 |
|---|---|
| **事件词表**（增删 `type`、改 payload 字段名/含义） | ① `src/evogenesis/arena/env.py` 的发射点；② `tests/test_arena.py::KNOWN_EVENTS`；③ 本文档 §4.2；④ `../core/核心机制与数据流.md` §5.1 摘要表；⑤ `schemas/examples/event_log_example.jsonl`（重生成，见 §4.4）；⑥ 若涉及前端消费：`frontend/src/api/arena.ts` 的 `ArenaEvent`；⑦ 若涉及 WS 推送：`../api/API与系统工程.md` §4.1 R11 |
| **冻结参数值**（`capture_size_ratio` / 世界尺寸 / Hz / 步数 / 种群数） | ① `configs/default_arena.yaml`（**唯一事实来源**）；② `src/evogenesis/arena/config.py` 默认值；③ `../../../docs/参数总表.json`；④ `tests/test_arena.py::test_population_counts_match_frozen_defaults`（种群数）；⑤ 本文档 §2；⑥ 报告中的参数表快照 |
| **MVP 标定旋钮**（`biomass_to_size_gain`、`actors` 中 `../../../docs/参数总表.json` 未收录的 11 项——`predator_turn_rate` 已进表故不在内、以及任何 `../../../docs/参数总表.json` 未收录的感知/能量/成长值） | ① `configs/default_arena.yaml`（**需先补上当前缺失的 `actors:` 块与 `biomass_to_size_gain`**）；② `config.py` 默认值；③ 本文档 §2.2；④ 建议同步把新值补进 `../../../docs/参数总表.json`，否则"冻结"一词不成立 |
| ⚠️ **障碍生成方式 / `n_obstacles` / 半径范围 / clearance** | ① `env.py::_spawn_obstacles()` 与 `reset()`（必须保持"先清空、再就地逐个生成"）；② 本文档 §3.2 S9、§5 D2/D5；③ `test_reset_idempotent_on_same_instance`；④ **一切历史冒烟基线作废**（RNG 流全局平移） |
| **12 维感知顺序**（`sensing.DIM_NAMES` / `observe()` 返回顺序） | ① `src/evogenesis/arena/sensing.py`（docstring 与 `DIM_NAMES`）；② `schemas/examples/README.md` 的 12 维语义表；③ `schemas/examples/trajectory_example.jsonl`（观测向量列序）；④ `../core/核心机制与数据流.md` §4.2 的 `observation` 行；⑤ `../connectome/DanioNet设计规范.md` §2；⑥ `../../../docs/参数总表.json` `sensory_dim`；⑦ **顺序冻结是验收清单硬性要求，改动需双方同步** |
| ⚠️ **looming 口径**（`nearest_predator_relative_size` / `_prev_predator_rel` 刷新位置） | ① `sensing.py` 与 `env.py`（**两者必须继续共用同一函数**，否则差分重新变成聚合口径差）；② 本文档 S20 / §7 F1 / §8 M13；③ 认领表 A1 |
| **`ArenaConfig` 字段增删** | ① `config.py`；② `configs/default_arena.yaml`；③ 本文档 §2；④ `../api/API接口.md` §7.2（`arena_config_path` 一旦真正生效，字段集即成为对外契约） |
| **`per_fish_log()` 键名** | ① `env.py`；② `tests/test_arena.py::test_per_fish_log_completeness` 的 `required` 集合；③ 本文档 §6；④ `Danio_Arena设计规范.md` §13 |

---

## 附：冒烟基线

本文件自测基线：`master_seed = 250927`、600 步、12 条 ExpertPolicy 鱼、默认 `ArenaConfig()`。

| 项 | 值 |
|---|---|
| 猎物捕获 | 5 / 24（`arena.prey_captured` 计数亦为 5） |
| 存活 | 12 / 12 |
| 事件计数 | `arena.spawn` 39 + `arena.prey_captured` 5 + `arena.episode_end` 1 = **45** |
| 吞吐 | 约 267 steps/s（单进程、CPU） |
| 测试 | `pytest tests/test_arena.py tests/test_api_contract.py` → **24 passed**（`test_arena.py` 15 + `test_api_contract.py` 9） |

⚠️ **历史基线（9 / 24 猎物捕获、约 236 steps/s）不可与本节数值直接对比**：障碍生成方式（S9）一旦变动，同一 seed 下的初始世界即不同（D5）。

**多 seed 实测（600 步，12 条 ExpertPolicy 鱼，默认配置）**：

| seed | `arena.prey_captured` | `arena.fish_captured` | `arena.collision` | `arena.escape` | `arena.energy_depleted` | 存活 |
|---|---|---|---|---|---|---|
| 1 | 10 | 2 | 0 | 0 | 0 | 10 |
| 7 | 12 | 1 | 0 | 0 | 0 | 11 |
| 42 | 8 | 2 | 0 | 0 | 0 | 10 |
| 1234 | 5 | 2 | 0 | 0 | 0 | 10 |
| 250927 | 5 | 0 | 0 | 0 | 0 | 12 |

**三条给指标口径的提醒**：① 默认场景下 `arena.collision` 与 `arena.escape` **一次都不触发**（A7 / A8 待认领）；② 饥饿在 600 步内不会发生（$C_{base} \times 600 = 0.48 < E_{max} = 1.0$，且有食物奖励补回），因此"饿死"路径在默认配置下同样观测不到；③ 死亡全部来自捕食者。
