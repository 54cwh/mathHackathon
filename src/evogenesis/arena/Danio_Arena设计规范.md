# Danio Arena 设计规范

## 1. 定位
Danio Arena 是 DanioNet 的行为测量环境，同时承担现场 Demo。目标是建立一个可控、可重复、可产生风险—收益冲突的生态任务，而不是追求完整真实流体动力学。

## 2. 世界
连续二维空间：

\[
100\times60
\]

更新频率：

\[
20\ Hz
\]

标准 episode：

\[
30s=600\ steps
\]

## 3. Live 默认对象
- 12 Danio fish
- 24 prey
- 3 predators
- 6 obstacles

Fast Evolution 使用 48 个 Danio 个体，不渲染所有轨迹。

## 4. 视野
鱼不拥有全图信息。每条鱼具有：
- left visual channel
- right visual channel
- finite sensory radius
- finite FOV

FOV/radius 为 config 参数，不作为真实斑马鱼解剖测量值。

## 5. 连续运动
动作：

\[
(\omega_t,v_t)
\]

方向：

\[
\theta_{t+1}=\theta_t+\omega_t\Delta t
\]

位置：

\[
\mathbf x_{t+1}=
\mathbf x_t+
v_t[\cos\theta_{t+1},\sin\theta_{t+1}]\Delta t
\]

体型增加时转向灵活性下降：

\[
\omega_{eff}=
\frac{\omega}{1+k_{turn}(size-1)}
\]

## 6. Energy / Hunger
\[
E_{t+1}
=
clip(E_t-C_{base}-C_{move}v_t^2+R_{food},0,E_{max})
\]

\[
H_t=1-\frac{E_t}{E_{max}}
\]

energy=0 时死亡。

## 7. Growth
吃到 prey 增加 biomass，biomass 使 size 缓慢增长并设上限。

体型增大带来：
- 可捕食更大 prey
- metabolic cost ↑
- turning inertia ↑

因此“大”不是单向优势。

## 8. Predation
必须同时满足：

\[
d<r_{capture}
\]

和：

\[
size_{hunter}>\kappa size_{target}
\]

初始：

\[
\kappa=1.25
\]

最终通过 play-test 校准。

## 9. PredatorPolicy
predator 不用神经网络：
- 巡游
- 发现合法目标后追踪
- 避障
- 丢失目标后恢复巡游

## 10. PreyPolicy
透明简单规则：
- stochastic wander
- obstacle avoidance
- proximity avoidance

## 11. ExpertPolicy
用于 imitation learning，不参与最终 DanioNet scoring：

\[
u=
w_pu_{prey}
-w_du_{predator}
-w_ou_{obstacle}
\]

prey attraction 随 hunger 增大：

\[
w_p=w_{p0}+k_HH
\]

再映射到连续：

\[
(\omega^*,v^*)
\]

## 12. 风险—收益冲突
Complex Scene 可设置：
- 高价值 prey 靠近 predator
- resource-scarce 时 hunger 提升 prey attraction
- obstacles 限制逃生路径

用于共同激活 prey / threat / integrator / hunger 机制。

## 13. 事件日志
每条鱼记录：
- generation
- encounters
- captures
- predator encounters
- escape successes
- collisions
- energy trajectory
- size trajectory
- survival steps
- motor commands
- selected neural activity snapshots

## 14. 历史依赖探针任务（H3，草案待确认）

检验 H3（异质 \(\tau\) 的作用）需要一个体现历史依赖的探针：
- Arena 维护隐藏真相 `last_seen_prey_pos=(x*,y*)` 与其时间 `t0`；
- prey 被遮挡 / 离开 FOV 达 \(D\) 步后，判定鱼能否回到 \((x^*,y^*)\)（回归半径 \(r_H\)）；
- 报告 \(P(D)\) 退化曲线；`integrator_memory` 激活可作辅助证据；
- 阴性对照：打乱历史（shuffle `last_seen_prey_pos`）后 \(P(D)\) 应下降。

依据：斑马鱼脑干 integrator 维持自我位置记忆、被动位移后数秒游回原位 `[bib#26]`；异质时间常数支撑记忆痕迹 `[bib#27]`。本任务是**抽象探针**，非真实范式复刻。

## 15. 12 维 observation 的语义归属

> 本节闭合 `../core/核心机制与数据流.md` §10 开放项 **#13**（原文：「12 维 observation 语义 owner（DanioNet §2 ↔ Arena §4 互指「待闭合」）」）与本文件「阅读问题」A 节 #1。
> 裁决依据为 `AGENTS.md` 既有条款；本节只做归属声明与索引，不新立规则、不发明数值。

### 15.1 归属声明：语义 owner 是 Arena

12 维 observation 是 **Arena 的产出物**，其语义 owner 是 `arena/` 文档（本文件与 `Danio_Arena实现说明.md`）。依据 `AGENTS.md`：

- `AGENTS.md:142`：`arena/Danio_Arena设计规范.md`（+ `Danio_Arena实现说明.md`）——「**产出** observation（12 维）、事件日志、每鱼记录」；
- `AGENTS.md:149`：「每个箭头的边界对象由**产出方**文档定义，消费方只引用（见上 producer owns）」；
- `AGENTS.md:126`：「模块内算法与常量语义 → 该模块文档」。

⇒ `../connectome/DanioNet设计规范.md` §2 是**消费方**的引用点：只引用本文件定义的语义，不改名、不另立定义。

`AGENTS.md:128` 的「禁止循环引用」条款要求边界对象指定唯一 owner、不得在两处各写一版 —— 本节的归属声明即该条款在 12 维 observation 上的落点，开放项 `#13` 由此闭合。

### 15.2 顺序权威：顺序冻结，机器可读权威是 `sensing.py::DIM_NAMES`

顺序冻结是硬性验收项：`../../../docs/验收清单.md:15`「12 维输入顺序固定」。

**机器可读的权威是 `arena/sensing.py` 的 `DIM_NAMES`（`sensing.py:25-38`），与 `observe()` 的返回顺序（`sensing.py:147-163`）逐项对齐**；`sensing.py:4-11` 的 docstring 以同一顺序声明该顺序为 `FROZEN`。12 维名字与索引如下（逐项抄自 `sensing.py`）：

| idx | 名称 | `sensing.py` 行 |
|---|---|---|
| 0 | `prey_left_signal` | 26 |
| 1 | `prey_right_signal` | 27 |
| 2 | `threat_left_signal` | 28 |
| 3 | `threat_right_signal` | 29 |
| 4 | `obstacle_left_signal` | 30 |
| 5 | `obstacle_right_signal` | 31 |
| 6 | `prey_relative_size` | 32 |
| 7 | `predator_relative_size` | 33 |
| 8 | `looming_rate` | 34 |
| 9 | `current_speed` | 35 |
| 10 | `energy` | 36 |
| 11 | `hunger` | 37 |

（按 1-based 计数时，**第 9 维即 idx 8 = `looming_rate`**。）

已逐项核对下列四处与本表一致：`../connectome/DanioNet设计规范.md:16-27`、`schemas/examples/README.md` 的 12 维语义表、`schemas/trajectory.schema.json:61`（`observation` 的 `description`）、`sensing.py:4-11`（docstring）。

### 15.3 归一化公式：实现既定，认领状态未冻结（不在此重写）

各分量如何由视野算出（强度线性衰减、`rel` 尺寸、looming 系数、左右分侧规则）**已实现并固化，但状态为「未认领」**：

- 认领表 `../../../research/notes/arena-api-决策认领表.md:15-19`（**A1**）：「12 维感官编码的归一化公式」；其「文档」栏记 `connectome/DanioNet设计规范.md §2` 只给 12 个维度名、公式全部未定义，待认领；
- `Danio_Arena实现说明.md:266`（§7 **A1** 行）：状态「已实现、已固化；**looming 通道在现状调用序下恒 0**（S20 实测），须一并认领」。

**公式本体见 `Danio_Arena实现说明.md` §3.1「规范 §4 视野」行（`:107`）、§3.2 **S20**（`:143`）与认领表 A1 的现状描述（`arena-api-决策认领表.md:16`）。本节不复制公式 —— 按 `AGENTS.md:128`「不得在两处各写一版」，公式保持单一出处。**

### 15.4 两项内容缺口

| # | 缺口 | 依据 | owner |
|---|---|---|---|
| N1 | **idx 8 `looming_rate` 在现状调用序下恒为 0**（除 `reset()` 后首帧）：`observe()` 总在步界调用，而 `_prev_predator_rel` 在上一步末尾用**同一函数**刷新，故 `pred_rel` 与 `prev` 由构造必然相等 ⇒ 该维**目前不携带信息** | `Danio_Arena实现说明.md:143`（**S20** 实测：seed 250927 首帧 12 条鱼中 2 条为 1.0，其后 40 步全 0）、`:281`（**F1**）、`:302`（**M13**） | Arena；修法与 A1 一并认领 |
| N2 | **同一顺序在七处并列陈述**（清单见 `Danio_Arena实现说明.md:343` ①–⑦）。按 `AGENTS.md:128` 应收敛为「**1 个 owner + 6 处引用**」 | `Danio_Arena实现说明.md:343`；`AGENTS.md:128` | 见下表 |

**N2 的收敛落点**（owner = 本节与 `sensing.py`，其余降为引用）：

| 序号 | 位置（`Danio_Arena实现说明.md:343` 的编号） | 目标角色 |
|---|---|---|
| ① | `src/evogenesis/arena/sensing.py`（docstring 与 `DIM_NAMES`） | **owner**（顺序与索引的机器可读权威） |
| ② | `schemas/examples/README.md` 的 12 维语义表 | 降为引用 |
| ③ | `schemas/examples/trajectory_example.jsonl`（观测向量列序） | 降为引用（数据列序须与 owner 一致） |
| ④ | `../core/核心机制与数据流.md` §4.2 的 `observation` 行 | 降为引用（现指向 `DanioNet §2`，改指本节） |
| ⑤ | `../connectome/DanioNet设计规范.md` §2 | 降为引用（消费方） |
| ⑥ | `../../../docs/参数总表.json` `sensory_dim` | 保留（Tier 3 拥有基数 `12` 与依据状态）；其 `source` 的指向待确认 |
| ⑦ | `../../../docs/验收清单.md:15`「12 维输入顺序固定」 | 保留（验收判据属地，不陈述具体顺序） |

②–⑤ 的具体替换句见 `../../../research/notes/12维observation语义归属-闭合提案.md`（②–⑤ 分属其他 owner 的 lane，本节只作归属声明，不代改）。

### 15.5 与「阅读问题」A 节 #1 的关系

A 节 #1 的两件事在本节分开记录：**归属已由 15.1 确立**（owner 为 Arena 自身，编码实现在 `sensing.py`，取值域为 `[0, 1]` —— `sensing.py:13` 声明，由 `Danio_Arena实现说明.md:313` 的 `test_obs_shape_and_ranges` 守护）；**公式的认领状态仍为 `草案待确认`**（认领表 A1）。归属闭合与数值冻结是两件事。

## 阅读问题（待确认）

> 逐份阅读本文时发现的未定义点，需与 05 / 06 / 16 及 `configs/default_arena.yaml` 对齐后确认。

### A. Arena ↔ DanioNet 接口（最关键）
1. **12 维 sensory 如何由视野算出未定义**
   - config 已给 `sensing.radius=18`、`fov_degrees=220`，但 left/right channel 如何编码（距离、方位、对象类型、相对朝向）以及如何拼成 12 维向量未写（对应 connectome/DanioNet设计规范.md `sensory_dim=12`）。
   - 影响：DanioNet 输入语义无法确定，感官回路与可视化无从实现。
   - **归属已确认**：本条的语义 owner 为 Arena 自身，顺序与索引的权威见本文件 §15「12 维 observation 的语义归属」；公式的认领状态仍为 `草案待确认`（认领表 A1）。

### B. 规则未闭合
2. **边界行为未定义**：100×60 空间内个体到边界如何处理（wrap / reflect / clamp / 惩罚）未写，config 无 boundary 项。
   - 影响：运动轨迹、可复现性、边界处视觉如何截断。
3. **碰撞 (collision) 后果未定义**：§13 记录 collisions，但撞 obstacle / 边界 / 同类后发生什么（穿模、反弹、扣 energy）未写。
4. **捕食关系是否双向未定义**：§8 给出通用捕食条件（`d<capture_radius` 且 `size_hunter>κ·size_target`），但 predator(3) 能否吃 Danio fish、被吃鱼的后果（死亡或扣分）未写。
5. **prey 是否重生 / 数量是否守恒未定义**：`live_prey=24` 是初始值；被吃后是否补充、能量是否守恒未写。
6. **escape success 判定未定义**：§13 记录 escape successes，但“怎样算一次成功逃脱”（脱离 radius、保持 N 步、存活至 episode 结束）未定义。
   - 影响：直接决定 evolution/遗传繁殖与演化模型.md fitness 的 E 分量。
7. **episode 结束与 survival 判定未定义**：30s/600 步结束后 survival 如何定义、与 energy=0 死亡如何交互、survival steps 如何归一化进 S 未写。
   - 影响：evolution/遗传繁殖与演化模型.md 的 S 分量与跨 episode 可比性。

### C. 参数缺失
8. **Δt 与 ω 单位未定**：hz=20 可推 Δt=0.05s，但 ω 是 rad/s 还是 rad/step 未写明；公式含 Δt 但未给值。
9. **初始布局未定义**：fish / prey / predator / obstacle 的初始位置（随机分布、固定 seed 布局、对称布置）未写。
   - 影响：固定 seed 可复现（docs/开发排期与人员分工.md 要求）。
10. **“高价值 prey” 未定义**：§12 使用 high-value prey，但 §3 只有单一类 24 prey，无价值分级参数。
11. **PredatorPolicy / PreyPolicy / ExpertPolicy 参数缺失**：巡游与追踪速度、避障半径，以及 ExpertPolicy 的 `w_p0 / k_H / w_d / w_o` 均未落在 config（后四个即 G4）。
