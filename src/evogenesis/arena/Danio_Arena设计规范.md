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

### 4.1 12 维 observation 编码（草案，本文件为编码 owner）

本文件负责**如何由视野算出** DanioNet §2 定义的 12 维向量（语义 / 顺序 / 值域以 DanioNet §2 为准）：

- `prey` / `threat` / `obstacle` 的 `_{left,right}_signal`：对 FOV 内该类目标按方位角以朝向为界分左右，取距离核 \((1-d/\text{radius})_+\) 之和（**左右划分与距离核为设计选择**，文献未规定）。
- `prey/predator_relative_size`：目标尺寸 / 自身尺寸。
- `looming_rate`：按 Gabbiani 1999 定义 \(\theta(t)=2\tan^{-1}(l/(v t))\)，取标定值 \(l/\lVert v\rVert\) `[bib#65]`。
- `current_speed`：**取自身上一步推进 \(v_{t-1}\)**（决策：与 energy/hunger 同属自身状态，见 `research/notes/契约决策记录.md`）。
- `energy` / `hunger`：直接取 Arena 生理状态（口径见 §6）。

依据：prey/threat 通道分离 `[bib#58][bib#60]`；详见 `research/reference/sensory-encoding-12d.md`。

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

## 阅读问题（待确认）

> 逐份阅读本文时发现的未定义点，需与 05 / 06 / 16 及 `configs/default_arena.yaml` 对齐后确认。

### A. Arena ↔ DanioNet 接口（最关键）
1. **12 维 sensory 如何由视野算出未定义**
   - config 已给 `sensing.radius=18`、`fov_degrees=220`，但 left/right channel 如何编码（距离、方位、对象类型、相对朝向）以及如何拼成 12 维向量未写（对应 connectome/DanioNet设计规范.md `sensory_dim=12`）。
   - 影响：DanioNet 输入语义无法确定，感官回路与可视化无从实现。

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
