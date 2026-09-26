# Danio Arena 设计规范

> **管辖范围**：Arena 世界/感官/物理/规则/事件与 **12 维 observation 编码**（§4.1）。产出：observation、事件、每鱼记录。不拥有：DanioNet 网络语义（见 `../connectome/DanioNet设计规范.md`）、参数取值（owner：`configs/default_arena.yaml` + `docs/参数总表.json`）。（层级与归属见 `AGENTS.md`「文档层级与优先级」。）
> 状态：**草案（契约重构 v0.9，2026-09-26）**。条款分两级：`【已定稿】` 可被论文与正式实验依赖；`【草案待确认】` 由实现先行落地、待认领，**不得进论文与正式实验**。待裁决清单见 §17 与 `research/notes/arena-api-决策认领表.md`。
> 与本目录 `Danio_Arena实现说明.md` 的分工：**本文件定义"应当怎样"（契约）**；实现说明描述"代码现在怎样"，并保留事件词表权威（其 §4.2）、参数↔代码映射与未认领登记。两者冲突时**本文件为准**。

**条款状态图例**：`【已定稿】` 可直接依赖；`【草案待确认】` 附"现状（代码）"与"备选"，认领后转已定稿。

## 1. 定位
Danio Arena 是 DanioNet 的行为测量环境，同时承担现场 Demo。目标是建立一个可控、可重复、可产生风险—收益冲突的生态任务，而不是追求完整真实流体动力学。【已定稿】

## 2. 世界
连续二维空间：

\[
100\times60
\]

更新频率：

\[
20\ Hz,\qquad \Delta t=1/20=0.05\ s
\]

标准 episode：

\[
30s=600\ steps
\]

【已定稿】单位为世界单位（world unit）。`episode_seconds` 与步数的关系由 `hz` 派生（\(\text{steps}=\text{seconds}\times hz\)）。

### 2.1 边界策略
【草案待确认】现状（代码）：位置裁剪（clamp）到 \([0,W]\times[0,H]\)，贴墙卡住并持续耗能，**不反弹、不出界即死**。备选：反弹 / 出界即死 / 边界惩罚。
- 影响：运动轨迹、边界处视觉截断、可复现性。

### 2.2 初始布局
【已定稿】出生点由拒绝采样生成，过程确定性、由 seed 完全决定：
- 采样：\(\mathbf x\sim U(0,W)\times U(0,H)\)，要求对全部障碍 `not contains(x, clearance)`；最多 200 次，失败回退世界中心 \((W/2,H/2)\)。
- clearance：fish 2.0 / prey 1.0 / predator 3.0 / obstacle \(r+1.0\)。
- 出生顺序：障碍 → 鱼 → 猎物 → 捕食者；障碍**先清空再逐个生成**，故同一局内障碍互不重叠、二次 reset 逐字段一致。
- 猎物初始尺寸 \(U(0.30,0.60)\)；障碍半径 \(U(1.5,3.5)\)。

> ⚠️ 复现性：拒绝采样次数取决于当次障碍布局，**障碍数量/半径范围/clearance 一旦改动，同 seed 下后续所有实体的随机流整体平移**，历史基线作废（详见实现说明 §5 D5）。

## 3. Live 默认对象
- 12 Danio fish
- 24 prey
- 3 predators
- 6 obstacles

Fast Evolution 使用 48 个 Danio 个体，不渲染所有轨迹。【已定稿】

## 4. 视野
鱼不拥有全图信息。每条鱼具有：
- left visual channel
- right visual channel
- finite sensory radius
- finite FOV

FOV/radius 为 config 参数，不作为真实斑马鱼解剖测量值。【已定稿】

### 4.1 12 维 observation 编码（本文件为编码 owner）
本文件负责**如何由视野算出** DanioNet §2 定义的 12 维向量（语义 / 顺序 / 值域以 DanioNet §2 为准）。【草案待确认】（公式由实现先行落地，待认领表 A1）

现状（代码）：
- `prey` / `threat` / `obstacle` 的 `_{left,right}_signal`：对 FOV 内该类目标按方位角以朝向为界分左右 —— **左右按 \(\mathrm{sign}(\sin(\text{rel\_bearing}))\) 划分**；强度取距离核 \((1-d/r)_{+}\)，**每通道求和后截断到 1.0**。
- `prey_relative_size`：\(\min(size_{prey}/size_{fish},1)\)；`predator_relative_size`：\(\min(size_{pred}/size_{fish}/2.5,1)\)。
- `looming_rate`：\(\mathrm{clip}(10\cdot\Delta\,\text{predator\_relative\_size},0,1)\)，其中相对尺寸取"视野半径内**最近**可见天敌"（与 env 共用同一函数），差分取最近一步。
- `current_speed`：取自身上一步推进 \(v_{t-1}\)（决策见 `research/notes/契约决策记录.md`）。
- `energy` / `hunger`：直接取 Arena 生理状态（口径见 §6）。

备选（待裁决 ④⑤）：
- `looming_rate` 亦可按 Gabbiani 1999 视觉角定义 \(\theta(t)=2\tan^{-1}(l/(vt))\)（标定取 \(l/\lVert v\rVert\)）——**与现状公式不同**，须二者取一。
- 每通道"求和后截断"与"先截断再求和"须与实现统一。

> ⚠️ 已知缺口：在现有调用序下 `looming_rate` 除 `reset()` 首帧外**恒为 0**（12 维第 9 维当前不携带信息）。修法（在 `step()` 内移动前后各取一次，或 prev 改在步首读取）会改变观测分布，须与 A1 一并认领。

依据：prey/threat 通道分离 `[bib#58][bib#60]`；详见 `research/reference/sensory-encoding-12d.md`。

## 5. 连续运动
动作：

\[
(\omega_t,v_t)
\]

方向与位置（**位移使用更新后的航向**）：

\[
\theta_{t+1}=\theta_t+\omega_{eff}\Delta t,\qquad
\mathbf x_{t+1}=\mathbf x_t+v_t[\cos\theta_{t+1},\sin\theta_{t+1}]\Delta t
\]

体型增加时转向灵活性下降：

\[
\omega_{eff}=\frac{\omega}{1+k_{turn}(size-1)},\qquad k_{turn}=0.35
\]

【已定稿】动作值与单位：\(\omega\in[-1,1]\)（rad/s）、\(v\in[0,1]\)（**世界单位/秒**）；每步位移 \(v\cdot\Delta t=0.05v\)。先裁剪 \(\omega\)，再施加转向惯性（故大鱼的**有效**角速度上限更小）。

## 6. Energy / Hunger
\[
E_{t+1}=\mathrm{clip}\!\left(E_t-C_{base}-C_{move}v_t^2+R_{food}\cdot\mathbb{1}[\text{本步捕获}],0,E_{max}\right),\qquad
H_t=1-\frac{E_t}{E_{max}}
\]

energy \(=0\) 时死亡。【已定稿】公式；**四系数取值 `【草案待确认】`**（现状 \(E_{max}=1.0\)、\(C_{base}=0.0008\)、\(C_{move}=0.0015\)、\(R_{food}=0.12\)，未进 `docs/参数总表.json`，待认领表 A3）。

## 7. Growth
吃到 prey 增加 biomass，biomass 使 size 缓慢增长并设上限：

\[
\text{biomass}\mathrel{+}=size_{prey},\qquad
size\leftarrow\min\big(size_{max},\ size+k_{growth}\cdot size_{prey}\big)
\]

体型增大带来：可捕食更大 prey、metabolic cost ↑、turning inertia ↑。因此"大"不是单向优势。

【草案待确认】（待认领表 A4）现状：\(size_0=1.0\)、\(size_{max}=2.5\)、\(k_{growth}=0.02\)；`biomass` 为**只写不读**的镜像量（实测单局 size 近乎不变 1.00→1.01）。备选：承认 `biomass` 为展示量并删去其耦合，或改用 `biomass` 驱动 size。

## 8. Predation
必须同时满足：

\[
d<r_{capture}\quad\text{且}\quad size_{hunter}>\kappa\, size_{target}
\]

**【已定稿】** 判据形式与 \(\kappa=1.25\)（\(\kappa\) 状态 `proposed_change`，最终由 play-test 标定）；**捕食为双向**：predator 可捕食 Danio fish，鱼可捕食 prey；被吃者即死亡。距判据为**纯距离，无朝向/口部角度**；每鱼每步**至多一条**捕食事件（命中第一个合格目标即处理）。

**【草案待确认】** \(r_{capture}=1.2\)（现状；待认领表 A2——是否采用、是否加朝向/口部角度）。

> ⚠️ 与生物量级冲突：真实斑马鱼为 gape-limited（探测 <1 BL、口裂 4–5% SL），而本项目 \(r_{capture}=1.2\)、\(\kappa=1.25\) 与之一致性差。属已知范围外偏差，见 `docs/参数总表.json` `citation_risks`。

## 9. PredatorPolicy
predator 不用神经网络：【已定稿】
- 巡游
- 发现合法目标后追踪
- 避障
- 丢失目标后恢复巡游

【已定稿】滞回与参数：旧目标仍存活且 \(d\le release=22\) → 保持锁定并全速追击；否则在 \(detect=15\) 内取**最近**存活鱼；无候选则返回"维持当前航向、巡游速度 \(0.40\)"。巡游速度 \(0.40\)、追击速度 \(0.65\)（`【草案待确认】`，待认领表 A5）。转向速率在 env 侧限制：\(\mathrm{clip}(\Delta\theta,\pm \text{turn\_rate}\cdot\Delta t)\)，`turn_rate` \(=5.0\) **rad/s**（\(\equiv 0.25\) rad/step，待认领表 A10）。

## 10. PreyPolicy
透明简单规则：【已定稿】结构
- stochastic wander
- obstacle avoidance
- ~~proximity avoidance~~ → 见下

【草案待确认】（待认领表 A5、M5/M6）现状：\(\omega\sim\mathcal N(0,0.8)\) 且截断到 \(\pm3.0\)（单位 rad/s），速度恒为 \(0.35\)；避障由 env 的前视点转向处理（gain \(=2.0\)）。**无主动逃跑**（prey 不感知鱼）。`PreyPolicy.avoid_gain`（\(=2.5\)）为**死参数**（env 从不传入触发量），应删除或接线。

## 11. ExpertPolicy
用于 imitation learning，不参与最终 DanioNet scoring：【已定稿】结构

\[
u=w_p u_{prey}-w_d u_{predator}-w_o u_{obstacle},\qquad w_p=w_{p0}+k_H H
\]

再映射到连续 \((\omega^*,v^*)\)。参数 \(w_{p0},k_H,w_d,w_o\) `【草案待确认】`（G4，未落 config）。

## 12. 风险—收益冲突
Complex Scene 可设置：【草案待确认】
- 高价值 prey 靠近 predator
- resource-scarce 时 hunger 提升 prey attraction
- obstacles 限制逃生路径

用于共同激活 prey / threat / integrator / hunger 机制。

**待裁决**：①「高价值 prey」价值分级未定义（§3 只有单一类 24 prey）；② environment（Food Rich / Predator Rich / Resource Scarce）三组当前**不改变任何参数**，"环境选择"尚无实际因果（M4）。

## 13. 事件日志与每鱼记录
**事件词表的唯一权威**在本目录 `Danio_Arena实现说明.md` §4.2 + `tests/test_arena.py::KNOWN_EVENTS`（v1，8 类点分层 `arena.*`，已生效）。本节不重复字段名。【已定稿】

每鱼记录（`per_fish_log()`，含全部 12 条鱼）应包含：

| 字段 | 状态 |
|---|---|
| generation | ✅（恒 0，未接演化） |
| encounters | ✅（\(d<r_{capture}\) 的近距接触计数） |
| captures | ✅ |
| predator encounters | ✅（口径＝捕食者**获得新目标**计数，非近距接触；待认领） |
| escape successes | ✅（口径见 §15 逃脱判定） |
| collisions | ✅ |
| energy trajectory | ✅ |
| size trajectory | ✅ |
| survival steps | ✅（步末对存活鱼自增；事件 payload 取自增前值） |
| motor commands | ✅（裁剪后的 \((\omega,v)\)） |
| selected neural activity snapshots | ❌ 未实现（需 DanioNet 接入） |

## 14. 历史依赖探针任务（H3）
检验 H3（异质 \(\tau\) 的作用）需要一个体现历史依赖的探针：【草案待确认】
- Arena 维护隐藏真相 `last_seen_prey_pos=(x*,y*)` 与其时间 \(t0\)；
- prey 被遮挡 / 离开 FOV 达 \(D\) 步后，判定鱼能否回到 \((x^*,y^*)\)（回归半径 \(r_H\)）；
- 报告 \(P(D)\) 退化曲线；`integrator_memory` 激活可作辅助证据；
- 阴性对照：打乱历史（shuffle `last_seen_prey_pos`）后 \(P(D)\) 应下降。

依据：斑马鱼脑干 integrator 维持自我位置记忆、被动位移后数秒游回原位 `[bib#26]`；异质时间常数支撑记忆痕迹 `[bib#27]`。本任务是**抽象探针**，非真实范式复刻。\(D\)、\(r_H\) 取值待定。

## 15. 繁殖/终止相关判定
【已定稿】episode 结束：`done = step_idx ≥ 600 或 非空种群全灭`；结束后 `step()` 幂等空转，`arena.episode_end` 每局**恰好一次**。空种群（`fish={}`）不判团灭。

【草案待确认】
- **逃脱判定**（A8）：现状为"捕食者换掉已锁定目标、且旧目标仍存活"即对旧目标计一次 escape；备选为"逃出 `release_radius` 才算"。旧目标已死亡（饿死/被吃）不计入。
- **团灭提前结束**（A9）：保留现状，或固定跑满 600 步 —— 影响 `fitness` 的 S 分量与跨 episode 可比性。
- **survival 定义与归一化**（阅读#7）：需明确 600 步满局、饿死、被捕食三类的 S 值口径。
- **prey 重生/守恒**（阅读#5）：现状不补充、不触发结束。

## 16. 参数表（本模块取值 → owner 为 `configs/` + `docs/参数总表.json`）

| 参数 | 值 | 单位 | 状态 |
|---|---|---|---|
| 世界 \(W\times H\) | 100 × 60 | world unit | 已定稿 |
| 更新频率 / \(\Delta t\) | 20 / 0.05 | Hz / s | 已定稿 |
| 标准 episode | 30 / 600 | s / step | 已定稿 |
| 种群（Live） | 12 / 24 / 3 / 6 | 个 | 已定稿 |
| Fast Evolution | 48 | 个 | 已定稿 |
| sensing.radius / fov | 18.0 / 220.0 | world unit / ° | 已定稿（`proposed_change` 待认领） |
| \(\kappa\)（capture_size_ratio） | 1.25 | — | `proposed_change` |
| \(r_{capture}\) | 1.2 | world unit | 草案待确认（A2） |
| \(k_{turn}\) | 0.35 | — | 草案待确认 |
| energy 四系数 | 1.0 / 0.0008 / 0.0015 / 0.12 | — | 草案待确认（A3） |
| growth | 1.0 / 2.5 / 0.02 | — | 草案待确认（A4） |
| prey：speed / size / wander | 0.35 / [0.30,0.60] / 0.8 | — | 草案待确认（A5） |
| predator：cruise / chase / detect / release / turn | 0.40 / 0.65 / 15 / 22 / 5.0 | — / — / wu / wu / rad/s | 草案待确认（A5/A10） |
| obstacle 半径 | [1.5, 3.5] | world unit | 已定稿 |

> ⚠️ `configs/default_arena.yaml` **当前无任何代码读取**（实现说明 §2.3-3 / M8 / 认领表 B7）：改 config 不影响仿真，与"参数 owner 是 `configs/`"冲突。**此项为冻结阻断项。**

## 17. 待裁决条款（认领清单）
以下条款为 `【草案待确认】`，须在 `research/notes/arena-api-决策认领表.md` 认领后转已定稿，方可冻结本文件：

| 组 | 条款 |
|---|---|
| 行为语义 | A6 边界策略；A7 碰撞后果（现状默认不触发，需重评指标）；A8 逃脱判定；A9 团灭提前结束；捕食双向/被吃后果（§8 已建议固定为双向，待确认）；prey 重生/守恒；survival 定义（§15） |
| 编码接口 | A1 12 维归一化（含 looming 公式二选一、每通道截断口径）；looming 恒 0 的修法 |
| 参数 | A2 \(r_{capture}\)；A3 能量四系数；A4 growth 与 biomass；A5 actors 12 项；A10 转向量纲；§12 高价值 prey 分级；G4 ExpertPolicy 权重 |
| 契约/工程 | §4.4 实例事件（重生成 vs 降级）；config 接线（B7/M8，**阻断**）；api 语义 B1–B6；本文件与实现说明的 owner 归属 |
