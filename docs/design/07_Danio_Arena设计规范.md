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
