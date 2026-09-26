# Danio Arena 设计规范

> **管辖范围**：Arena 世界/感官/物理/规则/事件与 **12 维 observation 编码**（§4.1）。产出：observation、事件、每鱼记录。不拥有：DanioNet 网络语义（见 `../connectome/DanioNet设计规范.md`）、参数取值（owner：`configs/default_arena.yaml` + `docs/参数总表.json`）。（层级与归属见 `AGENTS.md`「文档层级与优先级」。）
> 状态：**规范与实现合并稿（契约草案 v1.0，2026-09-26）**。条款分两级：`【已定稿】` 可被论文与正式实验依赖；`【草案待确认】` 由实现先行落地、待认领，**不得进论文与正式实验**。待裁决清单见 §17 与 `research/notes/arena-api-决策认领表.md`。
> 本文件合并定义 Arena 的契约（应当怎样）与实现映射（代码现在怎样）。契约条款优先；实现映射记录代码事实、参数映射、事件词表和未认领决定。

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

> **尺度声明【已定稿】**：本项目的 world unit（wu）是抽象仿真长度单位，不与真实斑马鱼体长（BL）建立固定换算；与距离有关的参数仅按无量纲比率进行生物学校准。`size` 表示相对体型状态，不代表真实 BL。幼虫实验数据仅作为无量纲行为关系的生物学先验，不视为成鱼尺度的直接测量。
> 依据：方案 B 裁决（2026-09-26，见 `research/notes/契约决策记录.md`）；`research/reference/zebrafish-escape-capture.{json,md}` T2。本声明同时闭合 §8 旧记的尺度冲突。

### 2.1 边界策略
【已定稿】（2026-09-26，认领表 A6）新增显式配置项 `world.boundary`，取值 `clamp` / `reflect`；**正式实验默认 `reflect`**。
- `reflect`：**镜面反射**——越界分量取反射（`x<0 ⇒ x←-x`、`y<0 ⇒ y←-y`，对应速度分量同号翻转；朝向按墙法线镜面反射：x 向越界 `θ←π−θ`、y 向越界 `θ←−θ`）。**确定性、不消耗随机数**，故同 seed 随机流不受影响。
- `clamp`（旧默认）**废弃为正式实验默认**：贴墙卡住并持续耗能属**隐性能耗**，使跨 seed 的能量与 survival 不可比；保留为对照 / 历史复现选项。
- 鱼与脚本实体（prey / predator）一律适用同一策略。
- 影响：运动轨迹、边界处视觉截断、可复现性。

### 2.2 初始布局
【已定稿】出生点由拒绝采样生成，过程确定性、由 seed 完全决定：
- 采样：\(\mathbf x\sim U(0,W)\times U(0,H)\)，要求对全部障碍 `not contains(x, clearance)`；最多 200 次，失败回退世界中心 \((W/2,H/2)\)。
- clearance：fish 2.0 / prey 1.0 / predator 3.0 / obstacle \(r+1.0\)。
- 出生顺序：障碍 → 鱼 → 猎物 → 捕食者；障碍**先清空再逐个生成**，故同一局内障碍互不重叠、二次 reset 逐字段一致。
- 猎物初始尺寸 \(U(0.30,0.60)\)；障碍半径 \(U(1.5,3.5)\)。

> ⚠️ 复现性：拒绝采样次数取决于当次障碍布局，**障碍数量/半径范围/clearance 一旦改动，同 seed 下后续所有实体的随机流整体平移**，历史基线作废（详见 §18.5 D5）。

## 3. Live 默认对象
- 12 Danio fish
- 24 prey
- 3 predators
- 6 obstacles

**两种规模，勿混用【已定稿】**：`Live`/Demo 与 `ExpertPolicy` 基线用 **12** 鱼（本节默认，`population.n_fish=12`）；**Fast Evolution / Experiment F** 用 **48** 个 Danio 个体（`configs/evolution.yaml::population_size`），由编排层按实际 viable 数覆盖 `population.n_fish`（`pipeline/arena_episode.py`）后传入 Arena，不渲染全部轨迹。`experiment §4` 的 12 鱼前置区分力检查属前者。

## 4. 视野
鱼不拥有全图信息。每条鱼具有：
- left visual channel
- right visual channel
- finite sensory radius
- finite FOV

FOV/radius 为 config 参数，不作为真实斑马鱼解剖测量值。【已定稿】

### 4.1 12 维 observation 编码（本文件为编码 owner）
> **值域契约**：12 维的语义 / 顺序 / **值域 `[0,1]`** / dtype（`float32`）由 `../connectome/DanioNet设计规范.md` §2（v1.8，2026-09-26 冻结）own；本节职责是**编码规则**，其结果须映射到该区间。
> ⚠️ **dtype 现状（对齐缺口）**：`sensing.observe()` 返回 **`float64`**（`sensing.py:162` `dtype=float`），而 DanioNet §2 契约是 `float32`。当前由下游转换为 `float32`（`pipeline/arena_episode.py` 写入 `np.float32` 数组；`core §7` 定「消费方转换」），故**契约未被违反**；但若未来直接把 `arena.observe()` 输出喂给 DanioNet，须先转 `float32`。改 Arena 内部 dtype 会轻微改变 `ExpertPolicy` 动作（float64→float32 舍入）从而作废 §18.11 基线，故**暂不改**。
本文件负责**如何由视野算出** DanioNet §2 定义的 12 维向量（语义 / 顺序 / 值域以 DanioNet §2 为准）。【草案待确认】（公式由实现先行落地，待认领表 A1）

现状（代码）：
- `prey` / `threat` / `obstacle` 的 `_{left,right}_signal`：对 FOV 内该类目标按方位角以朝向为界分左右 —— **左右按 \(\mathrm{sign}(\sin(\text{rel\_bearing}))\) 划分**；强度取距离核 \((1-d/r)_{+}\)，**每通道求和后截断到 1.0**。
- `prey_relative_size`：\(\min(size_{prey}/size_{fish},1)\)；`predator_relative_size`：\(\min(size_{pred}/size_{fish}/\texttt{predator\_size\_ref},1)\)（`sensing.predator_size_ref`，现 2.5）。
- `looming_rate`：**角尺寸扩张率**。角尺寸 \(\theta=2\arctan((size/2)/r)\)，取"视野半径 + FOV 内**所有**可见天敌的 **max** \(\theta\)"（多天敌以最著者为准，依据 `research/reference/looming-and-growth.md`）；相对扩张率 \(1/\tau=(\theta_{after}-\theta_{before})/(\theta_{after}\,\Delta t)\)（**分母 \(\theta_t=\theta_{after}\)**，同所引依据）；编码 \(\mathrm{clip}((1/\tau)/R_{loom},0,1)\)，\(R_{loom}=\texttt{sensing.looming\_norm}\)（现 3.5，**标定占位** \([2,5]\,\mathrm{s^{-1}}\)）。**相位（修复 M13/F1）**：步首采样 \(\theta_{before}\)、步尾（全部实体移动后）采样 \(\theta_{after}\)，结算本步扩张率并缓存到 `Fish._looming_rate`；`observe()` 只读该已结算值（= 最近一步扩张率，与其余各维同为「当前状态」相位）。任一端不可见（\(\theta=0\)）即记 0。
- `current_speed`：取自身上一步推进 \(v_{t-1}\)（决策见 `research/notes/契约决策记录.md`）。
- `energy` / `hunger`：直接取 Arena 生理状态（口径见 §6）。

已裁决：
- `looming_rate` 采用**角尺寸扩张率**（Gabbiani 1999 视觉角的离散形式）：\(\theta=2\arctan((size/2)/r)\)、max 聚合、\(R_{loom}\) 归一、步首-步尾差分。
- 每通道"求和后截断"口径已与实现统一（`_split_channels` 每通道 `min(...,1.0)`）。

> ✅ **已修（2026-09-26，M13/F1）**：`looming_rate` 步首/步尾采样结算并缓存，携带信息；`R_loom` 为标定占位，待 play-test 在 \([2,5]\) 内标定后转 `confirmed`（`docs/参数总表.json` `looming_norm`）。

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
E_{t+1}=\mathrm{clip}\!\left(E_t-C_{base}-C_{move}v_t^2-C_{pen}p_t+R_{food}\cdot f(size_{prey})\cdot\mathbb{1}[\text{本步捕获}],0,E_{max}\right),\qquad H_t=1-\frac{E_t}{E_{max}}
\]

其中 `p_t = max(0, r_obs + r_fish − d)` 为本步**障碍穿透深度**（不重叠时为 0）；`f(s) = s / s̄`、`s̄ = 0.45`。

energy `=0` 时死亡。【已定稿】公式。**四系数取值**（`E_max=1.0`、`C_base=0.0008`、`C_move=0.0015`、`R_food=0.12`）认领表 A3 已签「接受并登记」，待补 `docs/参数总表.json`。

**2026-09-26 新增两项**：
- `C_pen`（`energy.collision_penalty`，**标定占位**）：碰撞软惩罚系数，与「硬不穿透」配合，见 §18.7 A7。
- `f`：能量回报随猎物体型的归一化函数。取 `f(s)=s/s̄`、`s̄=0.45`（= prey 尺寸区间 `[0.30,0.60]` 的中点），使**均值回报 ≈ R_food = 0.12**，**不破坏 A3 已完成的能量预算**（否则「每局至少吃 ~4 条才能活到 600 步」的结论作废）。`s̄` 属归一化约定（设计选择，非生物学量）。

## 7. Growth
【已定稿】（2026-09-26，认领表 A4 + 用户裁决「面积式」）吃到 prey 后按**面积守恒带损耗**增长：

\[
size\leftarrow\min\big(size_{max},\ sqrt{size^2+g\cdot size_{prey}^2}\big)
\]

- `g`（`growth.prey_area_gain`，**标定占位**）：开源机制对照报告区间 0.1–0.35（[bib#215] 实取 0.35），本仓库占位 **0.2**；须 play-test 标定后才可冻结。**依据性质【已定稿·声明】**：该区间来自开源游戏实现（[bib#215]，**非同行评审**），本仓库只**借鉴机制、自行重写**，未复制代码或素材；论文引用时必须声明其为工程对照而非学术依据。
- **边际递减内生**：自身越大，同一 prey 带来的**相对**增幅越小，无需额外调参；`size_max` 退化为**硬上限**（不再依赖公式自然收敛）。
- `Fish.biomass` **字段删除**：面积式下 `size` 已完整编码生长，该字段无角色，同时消除原「只写不读」缺陷。原线性系数 `biomass_to_size_gain` 由 `prey_area_gain` 取代。
- 【已定稿·声明】**与真实斑马鱼时间尺度不符**：30 s 内真实鱼质量变化仅 ~1e−5 量级，故**局内可见生长属游戏化抽象**（`问题定义与研究假设.md` §4 建模假设 7「growth 是生态游戏化抽象」）。论文中须显式声明，**不得**表述为生物学实测；生物学校准的生长应放到跨 episode / 世代尺度讨论。

体型增大带来：可捕食更大 prey、metabolic cost ↑、turning inertia ↑。因此「大」不是单向优势——"大吃小"的收益被机动性代价部分抵消。

## 8. Predation
必须同时满足**三条**：

\[
d<r_{capture}\quad\text{且}\quad size_{hunter}\ge\kappa\, size_{target}\quad\text{且}\quad \lvert\Delta\theta\rvert\le\frac{\theta_{cone}}{2}
\]

**【已定稿】** 判据形式**含边界**：$size_{hunter}\ge\kappa\, size_{target}$（等价 `prey_size ≤ predator_size / κ`）。$\kappa=1.25$ 保持（**设计选择**：未找到斑马鱼直接的最大可吞猎物/体长上限；替代物种 20–27% SL 度量的是**猎物体高**，不可倒数为 κ）。**该来源的登记状态【已定稿】**：Mihalitsis & Bellwood 2017 已登记为 **`[bib#221]`**（PLoS ONE 12(9):e0184679，2026-09-26 经 OpenAlex `W2753764258` 核验）；引用时限定语（替代物种 / **猎物体高** / **不可倒数为 κ**）须随引。**耦合约束【已定稿】**：$size_{predator}\ge\kappa\, size_{max}$——否则最大体型个体不可捕食；因 $size\leftarrow\min(size_{max},\cdot)$ 会**钳住**体型，该免疫态是**吸收态**。**捕食为双向**：predator 可捕食 Danio fish，鱼可捕食 prey；被吃者即死亡。每鱼每步**至多一条**捕食事件（命中第一个合格目标即处理）。

**【前向锥·已定稿（2026-09-26 实现）】** 目标要纳入捕食判定，还须位于**猎人朝向的前向锥**内：$\lvert\Delta\theta\rvert$ 为猎物相对**猎人**朝向的方位角，$\theta_{cone}$（`growth.capture_cone_degrees`）$=120\,^{\circ}$ 为**总锥角**（半锥 $60\,^{\circ}$）。锥角属**设计选择**（dossier T2 `add_directionality`；[bib#217]/[bib#218] 对照），非实测值；默认值 120° 由用户 2026-09-26 裁决。
**双向同一**：判据对两个方向对称——predator 吃鱼与鱼吃 prey，均按**各自作为猎人**的朝向锥判定。
$encounters$ 语义**不变**（仍为 $d<r_{capture}$ 的近距接触计数，见 §18.3.2 S6）：锥只作用于**捕获判定**，不改变接触计数。**【2026-09-26 同日追加】** 该量自即日起同时是 `实验与评价体系.md` §2.1 `prey_capture` 的**分母**（原以 `capture_attempts` 为分母，因确定性捕获导致口径退化而改判，见 §13 字段表与 S6 行）。

**【已定稿】** $r_{capture}=4.61$（方案 B：按 $r_{capture}/sensing.radius=\sqrt{0.16\times0.41}=0.256$ 校准，可接受域 2.88–7.38；见 `research/notes/契约决策记录.md`）。**前向锥（总锥角 120°）已于 2026-09-26 实现**（§17 A2 该项闭合）。

**【已定稿】捕食尝试计数（2026-09-26，用户裁定）**：`capture_attempts` 每鱼每步至多 +1，条件为「猎物进入 `d < r_capture` **且在猎人前向锥内**」并**判定了尺寸口径**；吃到（`size_hunter ≥ κ·size_target`）与判定为太小（`arena.capture_attempt`）**都计**。锥外的猎物不计（§17 S5：命中第一个半径内猎物即 `break`，故每步至多一次判定）；`encounters` 仍是**纯距离**口径（S6），两者不可互替。**【2026-09-26 同日改判】** 该量**不再充当 `实验与评价体系.md` §2.1 `prey_capture` 的分母**，降为**诊断列**：`§2.1 分母 = encounters`（尺寸门之前的纯距离口径，S6）；`capture_attempts − captures` = 「进过口但吃不下」的次数。理由：默认 `growth.capture_success_prob = 1.0`（本 § a）使 `capture_attempts == captures` 恒成立，以之为分母的指标只能取 1.0/0.0，均值退化为「有过机会的个体占比」。

> **a. 捕食是否引入随机失败——【已定稿】（2026-09-26）**：新增 config 旋钮
> `growth.capture_success_prob ∈ [0,1]`（`configs/default_arena.yaml`、`docs/参数总表.json` 已登记）。
> **默认 `1.0` = 确定性捕获**（历史行为，尺寸门通过即捕获，**不消费随机数**）；
> `prob < 1` 时，尺寸门通过后按 `prob` 判定，**扑击失败**记 `arena.capture_attempt`
> （`result="missed"`）且猎物存活。失败判定消费 `arena_dynamics` 流。
> 语义：该量是**鱼的捕食成功率**（predator 吃鱼仍为脚本化、确定性）。
> `prob=1.0` 时，任何以「首次接触」为单位的去重口径仍恒等于 1、零方差（论证见 `../experiment/实验与评价体系.md` §2.1），
> 故 `composite_fitness` 捕食分量按条件式取 `capture_rate`。

> **已知局限（未采纳项）**：开源机制对照报告建议距离口径改为「半径和」（$d<r_1+r_2$，使捕食圈随体型缩放）。**未采纳**——$r_{capture}=4.61$ 是同日刚裁决冻结的方案 B 值，改口径会使该标定与耦合约束 $size_{predator}\ge\kappa\,size_{max}$ 整体作废。记为后续项（§19 P2）。

> ⚠️ 原记「与生物量级冲突」。**根因＝`world unit ↔ BL` 换算缺失，已由 §2 尺度声明闭合**（方案 B：不建立固定换算，只按无量纲比率校准）。故本节参数不再与成鱼 BL 直接比对；校准口径是 `r_capture / sensing.radius` 与 $\kappa$ 的无量纲关系。

## 9. PredatorPolicy
predator 不用神经网络：【已定稿】
- 巡游
- 发现合法目标后追踪
- 避障
- 丢失目标后恢复巡游

【已定稿】滞回与参数：旧目标仍存活且 \(d\le release=22\) → 保持锁定并全速追击；否则在 \(detect=15\) 内取**最近**存活鱼；无候选则返回"维持当前航向、巡游速度 \(0.40\)"。

【已定稿·D8 裁决（2026-09-26）】`detect=15`（获取新锁定）< `sensing.radius=18`（鱼视野）< `release=22`（放弃锁定）的**不对称是有意设计**（依据 D，设计选择）：三者是**不同量**——`detect` 是捕食者**获取**新目标的阈值、`release` 是**已锁定追击**的滞回上界、`sensing.radius` 是鱼的**瞬时视野**。故存在 `18<d≤22` 的「已锁定但鱼看不见」窗口，模拟**追击惯性**（捕食者可持续追击暂时游出鱼视野的目标）；鱼在 `d≤18` 内仍能感知并逃离（`threat_*_signal`、ExpertPolicy）。该不对称**不视为缺陷**；若未来要求二者一致，须显式改参数并重跑基线。巡游速度 \(0.40\)、追击速度 \(0.65\)（`【草案待确认】`，待认领表 A5）。转向速率在 env 侧限制：\(\mathrm{clip}(\Delta\theta,\pm \text{turn\_rate}\cdot\Delta t)\)，`turn_rate` \(=5.0\) **rad/s**（\(\equiv 0.25\) rad/step，待认领表 A10）。

## 10. PreyPolicy
透明简单规则：【已定稿】结构
- stochastic wander
- obstacle avoidance
- ~~proximity avoidance~~ → 见下

【草案待确认】（待认领表 A5、M5/M6）现状：\(\omega\sim\mathcal N(0,0.8)\) 且截断到 \(\pm3.0\)（单位 rad/s），速度恒为 \(0.35\)；避障由 env 的前视点转向处理（gain \(=2.0\)）。**无主动逃跑**（prey 不感知鱼）。~~`PreyPolicy.avoid_gain`（\(=2.5\)）死参数~~ ✅ **2026-09-26 已删除**（连同未用的 `obstacle_rel_bearing` 形参）；避障统一由 env `_steer_away_from_obstacles(prey, gain=2.0)` 处理。

## 11. ExpertPolicy
用于 imitation learning，不参与最终 DanioNet scoring：【已定稿】结构

> **Provenance【已定稿·声明】**：本节为本仓库自写的简单加权规则。曾评估借鉴 `[bib#217]`（`tghbrk/fish-eat-fish`，**未声明许可证**）的三态状态机 + 计时器滞后，**经核实未被采用**（`arena/policies.py` 无状态机），故**无代码或素材复制**；该评估项仍须补进 `docs/declaration/THIRD_PARTY.md`。

\[
u=w_p u_{prey}-w_d u_{predator}-w_o u_{obstacle},\qquad w_p=w_{p0}+k_H H
\]

再映射到连续 \((\omega^*,v^*)\)。参数 \(w_{p0},k_H,w_d,w_o\) `【草案待确认】`（G4，未落 config）。

## 12. 风险—收益冲突
**2026-09-26 已定稿三项**（认领表 §12；依据 dossier T3）：

1. **prey 再生（R2 开放可再生）**：存活 prey 数 `< K = population.n_prey` 时，每 `population.prey_regrowth_steps` 步补 1 只（**确定性定时**；新个体位置用既有随机流采样）。
   - 依据（dossier T3 §3.1 资源核算）：24 prey / 12 fish ≈ 每鱼至多 2 次捕获 → `prey_capture` 分量在 episode **后半段饱和**、fitness 随时间漂移；开放再生使觅食压力在 600 步内近似**稳态**。
   - 占位值 `prey_regrowth_steps = 25`（**派生**：`episode_steps / n_prey = 600/24`，使再生速率与消耗速率同量级；**无生物学锚点，属设计选择**）。
2. **高价值 prey 分级**：`V_prey = e_prey/(1+h_prey)`，`e_prey ∝ size^α`（α∈[1,3]）、`h_prey ∝ size`（dossier T3 §3.2，最优食谱理论口径）。
   - 因 `V(·)` 对 α≥1、size>0 **严格单调递增**，**top-V 集合 ≡ top-size 集合**，故操作判据直接取 **`size ≥ 75th 分位`**（无需为 α 选值；α 只在需要 V 的**数值**时才有意义）。
3. **能量回报随体型**：`R_food · f(size_prey)`，`f(s)=s/s̄`、`s̄=0.45`（见 §6）。否则分级只影响 growth、不影响即时能量，「机制不成立」（dossier T3 §3.2）。

**其他**：
- **稀有度不作价值维度**（dossier T3：未检索到「稀有本身提高单次捕获价值」的生态学证据；最优食谱理论把遇率与收益率分开）。
- **待裁决（未闭合）**：environment（Food Rich / Predator Rich / Resource Scarce）三组当前**不改变任何参数**，「环境选择」尚无实际因果（M4）。
- 高价值 prey 靠近 predator / resource-scarce 时 hunger 提升 prey attraction / obstacles 限制逃生路径——用于共同激活 prey / threat / integrator / hunger 机制；**场景布局属后续项**。

## 13. 事件日志与每鱼记录
**事件词表的唯一权威**在本文件 §18 实现映射的事件词表 + `tests/test_arena.py::KNOWN_EVENTS`（v1，8 类点分层 `arena.*`，已生效）。本节不重复字段名。【已定稿】

每鱼记录（`per_fish_log()`，含全部 12 条鱼）应包含：

| 字段 | 状态 |
|---|---|
| generation | ✅（缺省 0；可由构造 `generation` 注入，见 §18.1；多代演化接入后为真实代数） |
| genome_id | ⚠️ 不在 `per_fish_log()`；`Fish.genome_id` 由构造注入（`genome_ids`，P0-9），供轨迹落盘读取 |
| encounters | ✅（\(d<r_{capture}\) 的近距接触计数；**＝`实验与评价体系.md` §2.1 `prey_capture` 分母**） |
| captures | ✅ |
| capture attempts | ✅（诊断列：进过前向锥的口，含「太小吃不下」；分母改用 encounters，见 §8/§18.6） |
| predator encounters | ✅（口径＝捕食者**获得新目标**（被锁定）计数，非近距接触；S7 已定稿） |
| escape successes | ✅（口径见 §15 逃脱判定） |
| collisions | ✅ |
| energy trajectory | ✅ |
| size trajectory | ✅ |
| survival steps | ✅（步末对存活鱼自增；事件 payload 取自增前值） |
| motor commands | ✅（裁剪后的 \((\omega,v)\)） |
| selected neural activity snapshots | ❌ 未实现——**不属 arena 职责**：激活量归 `connectome`/`DanioNet`（`brain.activation` 由 api/WS 推送），arena 不缓存网络隐藏状态（见 `M3`） |

## 14. 历史依赖探针任务（H3）
**任务定义【已定稿】（2026-09-26）**：检验 H3（异质 \(\tau\) 的作用）需要一个体现历史依赖的探针：
- Arena 维护隐藏真相 `last_seen_prey_pos=(x*,y*)` 与其时间 \(t0\)；
- prey 被遮挡 / 离开 FOV 达 \(D\) 步后，判定鱼能否回到 \((x^*,y^*)\)（回归半径 \(r_H\)）；
- 报告 \(P(D)\) 退化曲线；`integrator_memory` 激活可作辅助证据；
- 阴性对照：打乱历史（shuffle `last_seen_prey_pos`）后 \(P(D)\) 应下降。

**实现状态【未实现】**：`arena/` 当前无探针代码（无 `last_seen_prey_pos` 字段、无回归判定、无 shuffle 对照）；\(D\)、\(r_H\) 取值待定。**H3 的主证据不依赖本探针**——`integrator_memory` 单元激活统计可作辅助证据，探针为**可选增强**；实现须单列（新增 `Fish` 字段、可能新增事件类型，按 §18.10「事件词表」变更纪律同步 `KNOWN_EVENTS`）。列入 §19 P1。

依据：斑马鱼脑干 integrator 维持自我位置记忆、被动位移后数秒游回原位 `[bib#26]`；异质时间常数支撑记忆痕迹 `[bib#27]`。本任务是**抽象探针**，非真实范式复刻。\(D\)、\(r_H\) 取值待定。

## 15. 繁殖/终止相关判定
【已定稿】episode 结束：`done = step_idx ≥ 600`（**一律跑满 600 步**）。个体死亡只**冻结该个体**，不提前结束。结束后 `step()` 幂等空转，`arena.episode_end` 每局**恰好一次**。空种群（`fish={}`）不判团灭。
> **A9 裁决（2026-09-26）**：原「非空种群全灭即提前结束」**已废弃**——提前结束使 episode 长度内生，破坏跨 episode / 跨 seed 的 fitness 可比性。若日后恢复，必须同时落盘 `truncated` 标志与**实际** `episode_length` 并做协变量校正。

【已定稿】**逃脱判定（A8）——威胁结局制**：一次 escape 成立需**同时**满足
1. 该鱼**曾被某捕食者锁定**；
2. 该锁定被**放弃**（换目标 / 限时追击超时 / 丢失）；
3. 放弃后该鱼**继续存活 ≥ `actors.escape_hold_steps` 步**（默认 20 步 = 1 s @20 Hz，**标定占位**）。

仅「换目标」而未通过存活窗口者**不计**；旧目标已死亡（饿死 / 被吃）**不计**。
> 理由：原「换目标即算逃脱」会把「捕食者只是看到更近的鱼」这一**捕食者侧重决策**记成猎物功劳，上偏最大（dossier T1 `avoid` / `do_not_add`）。

【已定稿】**限时追击**：捕食者新增 `actors.predator_max_chase_steps`（默认 80 步，**标定占位**；@20 Hz 对应开源对照报告 3–5 s @60 fps，[bib#218] `fish.py:124,205-208`）。**依据性质**：开源游戏实现（[bib#218] `MonkWarrior08/Interactive_Fish_Eating_Game`，MIT，**非同行评审**；仅借鉴机制、自行重写）。连续追击超过该步数即放弃当前目标、恢复巡游——使「放弃」有明确因果，而非仅由换目标触发。

【已定稿】**survival 定义与归一化**：`S = survival_steps / 600`（固定分母、线性；满局存活 `S=1.0`，饿死 / 被捕食按实际存活步数取值）。加权合成 fitness 前，各分量须**显式尺度归一化**，并诊断分量间相关。

【已定稿】**prey 重生/守恒**：走 **R2 开放可再生**（见 §12）——不再「不补充」。

## 16. 参数表（本模块取值 → owner 为 `configs/` + `docs/参数总表.json`）
| 参数 | 值 | 单位 | 状态 |
|---|---|---|---|
| 世界 W×H | 100 × 60 | world unit | 已定稿 |
| 更新频率 / Δt | 20 / 0.05 | Hz / s | 已定稿 |
| 标准 episode | 30 / 600 | s / step | 已定稿 |
| 种群（Live） | 12 / 24 / 3 / 6 | 个 | 已定稿 |
| Fast Evolution | 48 | 个 | 已定稿 |
| `world.boundary` | reflect | — | 已定稿（2026-09-26，A6） |
| sensing.predator_size_ref | 2.5 | — | 已定稿（设计选择；相对尺寸归一参考） |
| sensing.looming_norm | 3.5 | s^-1 | **标定占位** \([2,5]\)（play-test 前不得冻结） |
| sensing.radius / fov | 18.0 / 220.0 | world unit / ° | 已定稿（**2026-09-26 按审计 A12 更正**：`proposed_change` 已不在参数总表的允许词表内、且无任何条目使用该档，已从 legend 移除；若需「建议改值」请用该表的 `changes_pending`） |
| κ（capture_size_ratio） | 1.25 | — | 已定稿（设计选择） |
| r_capture | 4.61 | world unit | 已定稿（方案 B） |
| θ_cone（capture_cone_degrees） | 120 | °（**总**锥角） | 已定稿（设计选择） |
| k_turn | 0.35 | — | 草案待确认 |
| energy 四系数 | 1.0 / 0.0008 / 0.0015 / 0.12 | — | 已定稿（A3 已签；依据 D，已进参数总表） |
| C_pen（collision_penalty） | 见 config | — | **标定占位** |
| growth | 1.0 / 2.5 / g=0.2（prey_area_gain） | — | **标定占位**（A4 面积式） |
| `capture_success_prob`（鱼捕食成功率） | 1.0（默认=确定性） | — | 已定稿（2026-09-26；§8 a） |
| prey 再生间隔（prey_regrowth_steps） | 25 | step | **标定占位**（派生 600/24） |
| 逃脱存活窗口（escape_hold_steps） | 20 | step | **标定占位** |
| 限时追击（predator_max_chase_steps） | 80 | step | **标定占位** |
| prey：speed / size / wander | 0.35 / [0.30,0.60] / 0.8 | — | 草案待确认（A5） |
| predator：cruise / chase / detect / release / turn | 0.40 / 0.65 / 15 / 22 / 5.0 | — / — / wu / wu / rad/s | 草案待确认（A5/A10） |
| obstacle 半径 | [1.5, 3.5] | world unit | 已定稿 |

## 17. 待裁决条款（认领清单）
以下条款为 `【草案待确认】`，须在 `research/notes/arena-api-决策认领表.md` 认领后转已定稿。**2026-09-26 已认领 9 项**（见 `research/notes/契约决策记录.md`「A3 签署结果」）。

| 组 | 条款 |
|---|---|
| 行为语义 | ✅ A6 边界策略；✅ A7 碰撞后果；✅ A8 逃脱判定；✅ A9 团灭提前结束；✅ 捕食双向/被吃后果（§8）；✅ prey 重生/守恒（§12）；✅ survival 定义（§15）。**余**：M4 环境三组仍不改变任何参数 |
| 编码接口 | ✅ A1 12 维归一化**已定**（含 looming 角尺寸扩张率、每通道截断口径）；仅余 `looming_norm`（R_loom）标定占位 |
| 参数 | ✅ A2 r_capture + 前向锥（4.61 + 120° 均已实现）；A3 能量四系数（已签，已进参数总表）；✅ A4 growth/biomass（面积式；g 为标定占位）；A5 actors **14 项**（已签，**已进 YAML 与参数总表**）；✅ A10 转向量纲；✅ §12 高价值 prey 分级；G4 ExpertPolicy 权重（待落 config） |
| 契约/工程 | §18 实例事件（重生成 vs 降级）；~~config 接线~~ ✅ 已闭合（loader + Arena 映射 + 调用方接线，2026-09-26）；api 语义 B1–B6；本文件的契约与实现映射分界 |

## 18. 实现映射（原 Danio Arena 实现说明）

> **管辖范围**：事件词表 v1（唯一权威）、参数表↔代码映射、实现细节与未认领决定。（层级与归属见 `AGENTS.md`「文档层级与优先级」。）

> 状态：实现说明（描述 `main` 上 `arena/` 的当前行为与数值口径）
> 归属：李辰钊（Arena / 系统）
> 上游契约：本文件前半部分、`../core/核心机制与数据流.md`、`../../../docs/参数总表.json`、`../connectome/DanioNet设计规范.md` §2（12 维语义/顺序/值域）；下游消费/编排见 `../pipeline/模型链装配.md`、`../experiment/实验与评价体系.md`、`scripts/run_arena.py`、`scripts/collect_trajectories.py`；接口侧见 `../api/API与系统工程.md` 与 `../api/API接口.md`（实现层已移除、待重写）
> ⚠️ 本文件描述**实现现在是什么样**，不等于**设计已如此规定**。凡上游文档未定义的数值与语义，状态一律为 `草案待确认`，
> 逐条列在 `research/notes/arena-api-决策认领表.md`，须经双方认领后写进上游文档才能升为契约。
> **未认领的数值不得进论文与正式实验。**

**本节是合并稿的实现映射：前半部分规范讲"应该怎样"（契约），本节讲"现在怎样"（实现与其契约状态）。两者冲突时以前半部分规范为准。**

代码位置：`src/evogenesis/arena/{config,entities,sensing,policies,env}.py`、`configs/default_arena.yaml`、`tests/test_arena.py`
本文档回答一个问题：**规范的规则落到代码里究竟变成了什么，以及哪些地方规范没写、代码却已经定型。**

**事实来源优先级：代码 > `configs/default_arena.yaml` > 本文档。** 本文档只做映射与记录，不发明规则；与代码冲突以代码为准（发现冲突请直接改本文档）。

**上游参数表**：`../../../docs/参数总表.json`（项数、`missing_required` 计数与状态均以该文件为准，随登记变动）是本文档全部参数交叉引用的目标路径；§2.1 / §2.2 的「收录」列与 §2.3-2 的结论按该表核对（`sensing_radius` / `sensing_fov_degrees` / `predator_turn_rate` 均在表内，参数总表 v0.12 中 `group="arena"` 共 **43** 项，其中 `sim_hz` 为 `confirmed`、`predator_size`/`episode_steps`/`capture_radius`/`episode_seconds` 为 `derived`，余为 `no_basis`，`body_length_mm` 为 `missing`）。

---

### 18.1 模块清单
| 文件 | 职责 | 行数 | 对外接口 |
|---|---|---|---|
| `src/evogenesis/arena/config.py` | 冻结参数的数据类镜像（`WorldConfig` / `PopulationConfig` / `SensingConfig` / `EnergyConfig` / `GrowthConfig` / `ActorDefaults` / `ArenaConfig`），全部 `frozen=True`；含 `load_arena_config()` / `arena_config_snapshot()` | 197 | `ArenaConfig()`、`load_arena_config()` |
| `src/evogenesis/arena/entities.py` | 实体：`Entity`（基类，含 `advance(boundary=...)`）、`Fish`、`Prey`、`Predator`、`Obstacle` | 97 | 数据类；`Entity.advance()`、`Obstacle.contains()` |
| `src/evogenesis/arena/sensing.py` | 12 维感知编码器；`SENSORY_DIM = 12`、`DIM_NAMES`、`nearest_predator_relative_size()`、`nearest_predator_angular_size()`（looming 角尺寸，env 消费） | 195 | `observe(...)`、`nearest_predator_relative_size(...)`、`nearest_predator_angular_size(...)` |
| `src/evogenesis/arena/policies.py` | 三条透明规则策略：`ExpertPolicy`、`PreyPolicy`、`PredatorPolicy`（巡游 / 追击 + 滞回 + **限时追击**） | 105 | `ExpertPolicy.__call__(obs)`、`PreyPolicy.act(rng, ...)`、`PredatorPolicy.plan(...)` |
| `src/evogenesis/arena/env.py` | `DanioArena` 主循环：运动 / 边界 / 感知入口 / 能量 / 碰撞 / 捕食（双向 + 前向锥）/ prey 再生 / 逃脱结算 / 事件 / 每鱼记录 | 562 | `reset()`、`step(actions)`、`observe(fish_id)`、`per_fish_log()`、`.events`；构造 **必传** `spawn_seed` / `dynamics_seed`，可注入 `fish_ids` / `genome_ids` / `generation` |
| `configs/default_arena.yaml` | 参数**唯一事实来源**；Arena 侧加载器已落地，run 目录由 `experiment/runlayout.py` 建（`scripts/run_arena.py` / `run_chain.py` / `run_evolution.py` 调用） | 48 | — |
| `tests/test_arena.py` | 29 项冒烟 + 单元 + 回归测试；`KNOWN_EVENTS` 是事件词表的**机器可读权威名单** | 503 | — |

`src/evogenesis/arena/__init__.py` 为空（无 re-export）；调用方一律从子模块显式导入。

**实体 id（定稿）**：`DanioArena(config, *, spawn_seed, dynamics_seed, fish_ids=None, genome_ids=None)` 可注入 `fish_ids`（实体 id）与 `genome_ids`（写入 `Fish.genome_id`，供 `schemas/trajectory.schema.json` 的 `genome_id` 字段）——均取 `core §3.1` 稳定 ID（`pipeline/` 负责铸造）。传入时 `self.fish` 与 `per_fish_log()` 以稳定 `fish_id` 为键、`Fish.genome_id` 为稳定 `genome_id`；不传时保留旧默认（`fish_XX` / `"unknown"`，向后兼容，`tests/test_arena.py` 沿用）。两者长度须等于 `population.n_fish` 且各自互异，否则构造报 `ValueError`。prey/predator/obstacle 的 `prey_XX` 等不在 `core §3.1` 稳定 ID 之列，保持内部命名。另可注入 `generation`（`int`，缺省 0），写入每个 `Fish.generation`；`pipeline/arena_episode.py` 与 `experiment/collect.py` 均透传本代代数。

### 18.2 参数表（代码 ↔ `configs/default_arena.yaml` 逐项对齐）

> 加载入口：`arena/config.py::load_arena_config()`（分层 `CLI > env > file > default`，优先级语义 owner 为 `core §config`）；键名约定与 `core/config.py::ModelConfig` 一致
> （section 名 = dataclass 名、键名 = 字段名），由 `tests/test_arena_config.py` 守护。

`config.py` 的 docstring 声明：

> Defaults mirror `configs/default_arena.yaml` (frozen values, docs/参数总表.json). All numbers MUST stay in sync with that file; the config object exists so experiments can override knobs without touching the frozen defaults.

下表逐项核对这一声明。

#### 18.2.1 `WorldConfig` / `PopulationConfig` / `SensingConfig` / `EnergyConfig`
| 代码字段 | 代码默认值 | YAML 键 | YAML 值 | 一致 | 参数总表 收录 |
|---|---|---|---|---|---|
| `world.width` | 100.0 | `world.width` | 100.0 | ✅ | ✅ `world_width` |
| `world.height` | 60.0 | `world.height` | 60.0 | ✅ | ✅ `world_height` |
| `world.hz` | 20 | `world.hz` | 20 | ✅ | ✅ `sim_hz` |
| `world.episode_steps` | 600 | `world.episode_steps` | 600 | ✅ | ✅ `episode_steps` |
| `world.boundary` | 'reflect' | `world.boundary` | 'reflect' | ✅ | ✅ `world_boundary` |
| `population.n_fish` | 12 | `population.n_fish` | 12 | ✅ | ✅ `live_fish` |
| `population.n_prey` | 24 | `population.n_prey` | 24 | ✅ | ✅ `live_prey` |
| `population.n_predators` | 3 | `population.n_predators` | 3 | ✅ | ✅ `live_predators` |
| `population.n_obstacles` | 6 | `population.n_obstacles` | 6 | ✅ | ✅ `live_obstacles` |
| `population.prey_regrowth_steps` | 25 | `population.prey_regrowth_steps` | 25 | ✅ | ✅ `prey_regrowth_steps` |
| `sensing.radius` | 18.0 | `sensing.radius` | 18.0 | ✅ | ✅ `sensing_radius` |
| `sensing.predator_size_ref` | 2.5 | `sensing.predator_size_ref` | 2.5 | ✅ | ✅ `predator_size_ref` |
| `sensing.looming_norm` | 3.5 | `sensing.looming_norm` | 3.5 | ✅ | ✅ `looming_norm`（标定占位） |
| `sensing.fov_degrees` | 220.0 | `sensing.fov_degrees` | 220.0 | ✅ | ✅ `sensing_fov_degrees` |
| `energy.e_max` | 1.0 | `energy.e_max` | 1.0 | ✅ | ✅ `e_max` |
| `energy.base_cost_per_step` | 0.0008 | `energy.base_cost_per_step` | 0.0008 | ✅ | ✅ `base_cost_per_step` |
| `energy.movement_cost_scale` | 0.0015 | `energy.movement_cost_scale` | 0.0015 | ✅ | ✅ `movement_cost_scale` |
| `energy.food_reward` | 0.12 | `energy.food_reward` | 0.12 | ✅ | ✅ `food_reward` |
| `energy.collision_penalty` | 0.001 | `energy.collision_penalty` | 0.001 | ✅ | ✅ `collision_penalty` |

`world.dt` 是派生属性：dt = 1/hz = 0.05 s。`world.episode_seconds` 是**YAML 独有的派生只读键**（不参与构造，见 `DERIVED_READONLY_KEYS`）。
`world.boundary` 在 `WorldConfig.__post_init__` 中校验取值（`reflect` / `clamp`），非法值在**加载期**即报错（不再静默回退）。

#### 18.2.2 `GrowthConfig` / `ActorDefaults`
| 代码字段 | 代码默认值 | YAML 键 | YAML 值 | 一致 | 参数总表 收录 |
|---|---|---|---|---|---|
| `growth.initial_size` | 1.0 | `growth.initial_size` | 1.0 | ✅ | ✅ `initial_size` |
| `growth.max_size` | 2.5 | `growth.max_size` | 2.5 | ✅ | ✅ `max_size` |
| `growth.capture_size_ratio` | 1.25 | `growth.capture_size_ratio` | 1.25 | ✅ | ✅ `capture_size_ratio` |
| `growth.capture_radius` | 4.61 | `growth.capture_radius` | 4.61 | ✅ | ✅ `capture_radius` |
| `growth.capture_cone_degrees` | 120.0 | `growth.capture_cone_degrees` | 120.0 | ✅ | ✅ `capture_cone_degrees` |
| `growth.turn_inertia_scale` | 0.35 | `growth.turn_inertia_scale` | 0.35 | ✅ | ✅ `turn_inertia_scale` |
| `growth.capture_success_prob` | 1.0 | `growth.capture_success_prob` | 1.0 | ✅ | ✅ `capture_success_prob` |
| `growth.prey_area_gain` | 0.2 | `growth.prey_area_gain` | 0.2 | ✅ | ✅ `prey_area_gain` |
| `actors.prey_speed` | 0.35 | `actors.prey_speed` | 0.35 | ✅ | ✅ `prey_speed` |
| `actors.prey_size_min` | 0.3 | `actors.prey_size_min` | 0.3 | ✅ | ✅ `prey_size_min` |
| `actors.prey_size_max` | 0.6 | `actors.prey_size_max` | 0.6 | ✅ | ✅ `prey_size_max` |
| `actors.predator_size` | 3.125 | `actors.predator_size` | 3.125 | ✅ | ✅ `predator_size` |
| `actors.predator_cruise_speed` | 0.4 | `actors.predator_cruise_speed` | 0.4 | ✅ | ✅ `predator_cruise_speed` |
| `actors.predator_chase_speed` | 0.65 | `actors.predator_chase_speed` | 0.65 | ✅ | ✅ `predator_chase_speed` |
| `actors.predator_detection_radius` | 15.0 | `actors.predator_detection_radius` | 15.0 | ✅ | ✅ `predator_detection_radius` |
| `actors.predator_release_radius` | 22.0 | `actors.predator_release_radius` | 22.0 | ✅ | ✅ `predator_release_radius` |
| `actors.predator_turn_rate` | 5.0 | `actors.predator_turn_rate` | 5.0 | ✅ | ✅ `predator_turn_rate` |
| `actors.obstacle_radius_min` | 1.5 | `actors.obstacle_radius_min` | 1.5 | ✅ | ✅ `obstacle_radius_min` |
| `actors.obstacle_radius_max` | 3.5 | `actors.obstacle_radius_max` | 3.5 | ✅ | ✅ `obstacle_radius_max` |
| `actors.wander_turn_std` | 0.8 | `actors.wander_turn_std` | 0.8 | ✅ | ✅ `wander_turn_std` |
| `actors.escape_hold_steps` | 20 | `actors.escape_hold_steps` | 20 | ✅ | ✅ `escape_hold_steps` |
| `actors.predator_max_chase_steps` | 80 | `actors.predator_max_chase_steps` | 80 | ✅ | ✅ `predator_max_chase_steps` |

#### 18.2.3 三条必须写明的结论

1. **`ActorDefaults` 整块（**14 项**）已全部进 `configs/default_arena.yaml` 的 `actors:` 段**（2026-09-26 补入；此前这 14 项在 YAML 中无归属）。同一提交把键名对齐 dataclass：`live_demo.{fish,prey,predators,obstacles}` → `population.{n_fish,n_prey,n_predators,n_obstacles}`。**更正（2026-09-26，审计 A13）**：本节原写「12 项 + `growth.biomass_to_size_gain`」，但该字段已随 A4 面积式**删除**（现为 `growth.prey_area_gain`），且 `ActorDefaults` 实为 **14** 个字段、YAML `actors:` 段亦为 **14** 个键 —— 三种说法（12 项 / 14 项 / 含 biomass）已统一为本句。
2. **`../../../docs/参数总表.json`（v0.12）已收录 `group="arena"` 共 43 项**，覆盖 `world` / `population` / `sensing` / `energy`（含 `collision_penalty`）/ `growth`（含 `prey_area_gain`）/ `actors` 全部字段。其中 `sim_hz` 为 `confirmed`，`predator_size` / `episode_steps` / `capture_radius` / `episode_seconds` 为 `derived`，其余为 `no_basis`（依据 D＝设计选择，**非「未登记」**）；`status` 描述**依据强度**、不表示冻结与否（冻结与否见本文件条款状态）。`body_length_mm` 记为 `missing`（属 DanioNet 侧长度契约，不是 Arena 世界参数）；`world.boundary` 已进表（`world_boundary`，§2.1 表 ✅）。
3. **`configs/default_arena.yaml` 已有调用方读取它 —— 该实现债 2026-09-26 闭合。** **Arena 侧加载已落地**：`arena/config.py::load_arena_config(path)`（严格构造，未知 section/键即报错）与 `arena_config_snapshot()`；键名已对齐 dataclass（`live_demo.*` → `population.*`，并补 `actors:` 段），由 `tests/test_arena_config.py` 的「YAML ↔ dataclass 逐字段一致」守护。**调用方接线已完成**：`experiment/runlayout.py::create_run_dir` 对 Arena 型配置（顶层键 ⊆ `ARENA_SECTIONS`）调用 loader，并落盘 **`arena_config_resolved.json`（已解析值快照）** —— 因为「原始 YAML 副本」与实际生效值可能漂移（默认值 / env / overrides）。**原对外服务层 `api/session.py` 已按用户决定移除**；arena 配置现行调用方为 `experiment/runlayout.py`（落盘 `arena_config_resolved.json`）、`scripts/run_arena.py`、`scripts/collect_trajectories.py`、`src/evogenesis/experiment/environments.py` 与 `src/evogenesis/pipeline/arena_episode.py`。与「所有数值必须由 config 读取」（`../../../docs/参数总表.json` 末行）的要求**已闭环**（见 §8 M8、认领表 B7）。

---

### 18.3 规则 → 代码映射

#### 18.3.1 规范节号 → 文件 / 函数 → 要点

| 规范 § | 主题 | 代码位置 | 要点 |
|---|---|---|---|
| §1 | 定位 | `env.py::DanioArena` | Arena 既是行为测量环境，也是现场 Demo 数据源；不追求流体动力学 |
| §2 | 世界 | `config.py::WorldConfig`、`WorldConfig.dt` | $100 \times 60$ 连续二维；20 Hz（$dt = 0.05$ s）；600 steps/episode。位置裁剪到 $[0,W] \times [0,H]$ |
| §3 | Live 默认对象 | `config.py::PopulationConfig`、`env.py::reset()` | 12 fish / 24 prey / 3 predators / 6 obstacles；由 `tests/test_arena.py::test_population_counts_match_frozen_defaults` 守护 |
| §4 | 视野 | `sensing.py::observe()`、`sensing.py::nearest_predator_relative_size()`、`sensing.py::max_predator_angular_size()`（looming）、`DanioArena.observe(fish_id)` | 有限半径 + 有限 FOV；左右通道按 $\mathrm{sign}(\sin(rel))$ 划分；强度 $1 - d/r$ 线性衰减，每通道截断到 1.0；无全图信息 |
| §5 | 连续运动 | `Entity.advance()`、`DanioArena._omega_eff()`、`env.py::step()` 鱼循环 | $\theta \mathrel{+}= \omega_{eff} \cdot dt$，**位移用新航向**；$\omega_{eff} = \omega / (1 + k_{turn}(size-1))$；越界按 `world.boundary` 处理（默认 `reflect` 镜面反射，`clamp` 为对照） |
| §6 | Energy / Hunger | `env.py::step()` 能量段、`config.py::EnergyConfig` | $E' = \mathrm{clip}(E - C_{base} - C_{move}v^2 - C_{pen}p_t + R_{food}\cdot f(size_{prey})\cdot\mathbb{1}[\text{本步捕获}], 0, E_{max})$；$H = 1 - E/E_{max}$；$E \le 0$ 判死 |
| §7 | Growth | `env.py::step()` 捕食段 | $size \leftarrow \min(max_size, \sqrt{size^2 + g\cdot prey\_size^2})$（面积守恒式，A4）；"大"同时带来更大 prey 与更大转向惯性 |
| §8 | Predation | `env.py::step()`（鱼吃猎物 + 捕食者吃鱼两段） | 双向同一判据：$d < r_{capture}$ **且** $size_{hunter} \ge \kappa \cdot size_{target}$ **且**目标在猎人前向锥（总锥角 $\theta_{cone}=120^{\circ}$）内 |
| §9 | PredatorPolicy | `policies.py::PredatorPolicy.plan()` + `env.py::step()` 捕食者段 | 巡游 → 追击 → 避障 → 恢复巡游；滞回由 `release_radius` 实现；转向速率限制在 env 不在 policy |
| §10 | PreyPolicy | `policies.py::PreyPolicy.act()` + `env.py::_steer_away_from_obstacles(prey, gain=2.0)` | 随机游走 + 避障；**MVP 无主动逃跑**（不被鱼感知） |
| §11 | ExpertPolicy | `policies.py::ExpertPolicy.__call__()`（`ExpertPolicy`→`DanioNet` 切换点已由 `pipeline/arena_episode.py` 接入，`scripts/run_chain.py` 为模型评估入口；对外服务层 `api/` 待重写） | 仅用于模仿学习与现场 Demo 驱动；不参与 DanioNet scoring |
| §12 | 风险—收益冲突 | `env.py::reset()`/`step()`（prey 再生）、`_prey_reward()` | R2 开放可再生（每 `prey_regrowth_steps` 补 1）、高价值＝size 75th 分位、回报随体型（$f(s)=s/\bar{s}$）均已落地；仅「高价值 prey 靠近 predator」的**场景布置**未做 |
| §13 | 事件日志 / 每鱼记录 | `env.py::per_fish_log()`、`entities.py::Fish` 缓冲字段 | 规范列 12 项，代码实现 11 项（1 项已声明未实现，见 §6） |

#### 18.3.2 规范未逐字规定、但代码已定型的补充细节

以下细节规范没有写死，是实现的既定选择。**改动它们等于改动 Arena 行为，须同步 §10 变更纪律。** 标 ⚠️ 者为与 §10 变更纪律强相关、须双方同步的条目。

| # | 细节 | 代码事实 |
|---|---|---|
| S1 | **动作语义** | `actions[fid] = (ω, v)` 先各自裁剪：$\omega \in [-1,1]$、$v \in [0,1]$。`v` 是**世界单位/秒**的速度（不是归一化档位）：每步位移 $v \cdot dt = 0.05v$ 世界单位，30 s 内 $v=1$ 的鱼最多走 30 单位（世界宽 100） |
| S2 | **转向惯性施加位置** | 先裁剪 $\omega$ 到 $[-1,1]$，再除以 $1 + k_{turn}(size-1)$，因此大鱼的**有效**角速度上限小于小鱼 |
| S3 | **避障探测** | `_steer_away_from_obstacles()` 在 $pos + speed \cdot \hat{e}(\theta) \cdot 3.0$ 处做**前视点**探测；命中第一个障碍即转向并 `return`（不累加多障碍）；转角为 $\mathrm{sign}(diff) \cdot gain$（开关式，不按夹角比例），`gain` 默认 0.5（鱼 / 捕食者），猎物显式传 2.0 |
| S4 | **碰撞判定** | `obstacle.contains(fish.pos, 0.1)`：把鱼的碰撞半径视作常数 0.1，**与 `fish.size` 无关**；每个鱼每步**最多一条**碰撞事件（命中即 `break`），`collisions += 1` 同步自增 |
| S5 | **捕食尝试唯一性** | 鱼每步遍历猎物时，命中第一个 $d < r_{capture}$ 的猎物即处理并 `break` —— 每鱼每步**最多一条** `capture_attempt` 或 `prey_captured` |
| S6 | **`encounters` 语义** | 每鱼每步**至多 1 次**：遍历猎物遇到**首个** $d < r_{capture}$ 即自增并 `break`（纯距离，尺寸门之前），不是"看见"的计数。**同时是 `实验与评价体系.md` §2.1 `prey_capture` 的分母**（2026-09-26 改判；原分母 `capture_attempts` 降为诊断列） |
| ⚠️ S7 | **`predator_encounters` 语义** | **目标获取计数**，不是接触计数：捕食者 `plan()` 得到的目标与上一帧不同（含 `None → X` 与 `X → Y`）时对**新目标** `+= 1`。实现于 `env.py` 捕食者段：`if target is not None and target != prev_target: self.fish[target].predator_encounters += 1`。候选集只含存活鱼，故死鱼不会被计入 |
| S8 | **出生空地采样** | `_free_spot(clearance)`：拒绝采样至多 200 次，位置为 $U(0,W) \times U(0,H)$，要求对 `self.obstacles` 中所有障碍 `not contains(pos, clearance)`；200 次仍失败则回退世界中心 $(W/2, H/2)$。各类实体 clearance：fish 2.0、prey 1.0、predator 3.0、obstacle $r + 1.0$ |
| ⚠️ S9 | **出生顺序与随机消耗** | `reset()` 顺序为 障碍 → 鱼 → 猎物 → 捕食者。**障碍就地逐个生成**：`reset()` 先 `self.obstacles = []`，再由 `_spawn_obstacles()` 逐个 `append`，因此**同一 reset 内的障碍互不重叠**，且第二次 `reset()` 与第一次完全一致。每个实体的随机消耗为"若干次拒绝采样 + 1 次航向/尺寸 uniform"，**采样次数本身进入 RNG 消费路径**（见 §5 D5） |
| S10 | **猎物初始尺寸** | $U(0.30, 0.60)$ |
| S11 | **障碍尺寸** | 半径 $U(1.5, 3.5)$ |
| S12 | **猎物游走** | `PreyPolicy.act(rng)`：$\omega \sim N(0, 0.8)$，裁剪到 $\pm 3.0$；速度恒为 `prey_speed = 0.35`。避障由 env `_steer_away_from_obstacles(prey, gain=2.0)` 处理。~~`avoid_gain` 死参数~~ 已于 2026-09-26 删除（见 §7 F2、§8 M6） |
| S13 | **捕食者滞回** | `plan()`：旧目标仍在 `fish_pos`（存活）且距离 $\le$ 22 → 保持锁定并全速追击；否则在 15 半径内取**最近**存活鱼；无候选则返回 `(None, 当前航向, 0.40)` |
| ⚠️ S14 | **捕食者转向速率限制** | env 侧对期望航向差做 $\mathrm{clip}(diff, -max\_turn, +max\_turn)$，其中 $max\_turn = \texttt{predator\_turn\_rate} \cdot dt = 5.0 \times 0.05 = 0.25$ rad/step。这是"转向速率限制在 env 而非 policy"的具体含义，由配置项 `predator_turn_rate`（rad/s）给出，与 0.25 rad/step 等价（认领表 A10） |
| S15 | **捕食者命中后行为** | 击杀后立刻 `pred.target_fish_id = None`；**同一捕食者因此不会**为自己的击杀发射 `arena.escape`（旧目标已死，见 S17 的条件），但**其他**也锁定该鱼的捕食者会（此时那条鱼仍存活） |
| S16 | **捕食者不参与能量/成长** | `Predator` 无 `energy` 字段；捕食者不饿、不长、不参与 leaderboard |
| ⚠️ S17 | **`arena.escape` 的真实触发条件** | `plan()` 返回的目标与 `pred.target_fish_id` 不同**且旧目标仍存活**时，才发射事件并对该鱼 `escape_successes += 1`。**旧目标已死亡（饿死，或被另一只捕食者吃掉）时既不发事件也不计数**，由 `test_dead_fish_not_credited_escape` 守护。指标口径须按此理解 |
| S18 | **`Predator.alive` 恒为真** | 全仓库没有任何 `pred.alive = False`（`.alive = False` 只出现在 prey 与 fish 上）。~~捕食者段 `if not pred.alive` 死分支与 `sensing` 的 `if d.alive` 过滤~~ 已于 2026-09-26 清理。见 §8 M7 |
| S19 | **`arena.energy_depleted` 的步数语义** | payload 的 `survival_steps` 取**自增之前**的值，即"死前已存活步数"；`Fish.survival_steps` 每步末对存活鱼自增 |
| ✅ S20 | **looming 口径（已修）** | 角尺寸 \(\theta=2\arctan((size/2)/r)\) 取"视野与半径内**最近**可见天敌"，在 `step()` 内**实体移动前**同相位计算，差分得 \(1/\tau=(\Delta\theta/\theta)/\Delta t\)、按 `sensing.looming_norm` 归一缓存于 `Fish._looming_rate`，`observe()` 只读；不可见置 0。回归：`tests/test_sensing_looming.py`（携带信息 / 无天敌恒 0） |
| ⚠️ S21 | **`step()` 的 done 守卫** | `__init__` / `reset()` 置 `self._episode_ended = False`；episode 结束后 `step()` **立即返回** `StepResult(self.step_idx, True, [])`（不再推进、不再发事件）。因此 ① `step_idx` 不会越过 600；② `arena.episode_end` 每次 episode **只发一次**；③ 结束后重复 `step()` 是幂等空转。由 `test_step_after_episode_end_is_inert` 守护 |
| ⚠️ S22 | **终止只由步数决定** | `done = self.step_idx >= self.cfg.world.episode_steps`（`env.py:483`）；个体全灭**不**提前结束（§15 A9 已废弃团灭提前结束）。由 `test_extinction_does_not_end_episode_early` 守护 |
| S23 | **死鱼不再感知** | `step()` 鱼循环、looming 段均 `if not fish.alive: continue`；`DanioArena.observe(fish_id)` 本身**不校验存活**，对死鱼仍会返回向量（其能量为 0） |

---

### 18.4 事件词表 v1

#### 18.4.1 信封

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

#### 18.4.2 词表 v1（8 项，点分层 `arena.*`）

| # | `type` | 触发时机 | payload |
|---|---|---|---|
| 1 | `arena.spawn` | `reset()` 为每个 fish / prey / predator 各发一次（$12+24+3 = 39$ 条） | `entity_id` |
| 2 | `arena.capture_attempt` | 鱼与某猎物 $d <$ `capture_radius`(4.61)、猎物在**前向锥**内、且尺寸比 $< \kappa$(1.25，即太小不可吞)；每鱼每步至多一条 | `fish_id, prey_id, distance, size_ratio, threshold, capture_radius, result` |
| 3 | `arena.prey_captured` | 鱼吃掉猎物（$d <$ `capture_radius`(4.61)、在前向锥内、且 $size_{fish} \ge \kappa \cdot size_{prey}$，$\kappa=1.25$ 判据含边界） | `fish_id, prey_id, distance, size_ratio, food_reward` |
| 4 | `arena.escape` | 捕食者**换掉**已锁定目标，且**该目标仍存活**（见 S17） | `fish_id, threat_source` |
| 5 | `arena.collision` | 鱼撞障碍（每鱼每步最多一次，命中即 `break`） | `fish_id, obstacle_id` |
| 6 | `arena.energy_depleted` | 能量结算后 $E \le 0$（饿死） | `fish_id, survival_steps` |
| 7 | `arena.fish_captured` | 捕食者吃掉鱼 | `fish_id, predator_id, survival_steps` |
| 8 | `arena.episode_end` | `step_idx >= episode_steps`（600）；个体全灭**不**提前结束（§15 A9 / S22）；每 episode **恰好一次**（S21） | `steps, fish_alive, prey_remaining` |

**字段口径速记**

- `distance` / `size_ratio` 在发射前 `round(..., 3)`；`threshold` 与 `capture_radius` 直接取 config 原值（1.25 / 4.61），便于离线核对判据。
- `arena.capture_attempt.result` 取值为 `"too_small_to_eat"`（尺寸门没过）或 `"missed"`（尺寸门过了但扑击失败，仅 `growth.capture_success_prob < 1` 时可能出现）；距离不足的猎物在判据前即被 `continue` 跳过、不产生事件。**草案里的 `"too_far"` 是永远不会出现的值**（见 §4.4）。
- `arena.escape.threat_source` 是**捕食者实体 id**（`predator_NN`），不是类型名。
- `arena.fish_captured.survival_steps` 与 `arena.energy_depleted.survival_steps` 同口径：发射时的 `Fish.survival_steps`（未自增）。
- **障碍不发射 spawn**：只有 fish / prey / predator 三类活动实体入事件。障碍的位置与半径、以及所有实体的实时位置/尺寸，走 snapshot（`GET /v1/sessions/{session_id}/snapshot`）而非事件流。
- `arena.episode_end` 的 `steps` 取 `step_idx`（此时已自增）：一律跑满，恒为 600。
- **`escape_successes` 与 `predator_encounters` 都是"计数而非事件"**：它们只出现在 `per_fish_log()` / `FishCard.metrics` / leaderboard 侧，事件流里没有对应条目。

#### 18.4.3 与 `../core/核心机制与数据流.md` §5.1 的关系

- `../core/核心机制与数据流.md` §5.1 已定为**设计侧参考**（该文件状态行注明"权威词表见 arena"，非待冻结）：它列"应有哪些事件"、命名 `arena.<event>`、**只增不删**。**事件词表的唯一权威是本文档 §4.2 + `tests/test_arena.py::KNOWN_EVENTS`（v1，已生效）**，字段名只在 §4.2 维护一套。
- **机器可读权威名单是 `tests/test_arena.py::KNOWN_EVENTS`**，由 `test_all_events_in_known_vocabulary` 守护（断言：整局事件的 `type` 均以 `arena.` 开头且属于该集合）。任何一方改词表都必须同时改这个集合。
- 命名风格与 WS 消息 `type` 的点分层约定（`../api/API与系统工程.md` §4.1 R11）一致：**磁盘与推送共用同一词表**。
- 词表状态：**v1 已生效**（池伟豪确认 2026-09-26；见 `research/notes/契约决策记录.md`）。本文件 §4.2 + `tests::KNOWN_EVENTS` 为事件词表的唯一权威。

#### 18.4.4 与草案实例 `schemas/examples/event_log_example.jsonl` 的差异

**现状核对（2026-09-26：已重生成并闭环）**：`schemas/examples/event_log_example.jsonl` 已按 v1 词表重生成，覆盖 **8 类事件各一条**，payload 与实现逐字段一致（信封 `{seq, type, step, payload}` 与 §18.4.1 同源）。原第 2 行判据矛盾已消除（现为 `size_ratio=0.2 < κ=1.25` 的 `too_small_to_eat`；另新增 `"missed"` 取值，仅 `capture_success_prob<1` 时出现）。

- 6 类取自默认 `ArenaConfig()`、示例种子 `20260925` 的真实 600 步 episode（首次出现）；
- `arena.capture_attempt` 与 `arena.energy_depleted` 在默认配置下不可自然观测，由受控场景触发（arena 真实代码路径产出）。
- provenance 明细见 `schemas/examples/README.md`。该实例现**可被代码依赖**（与 `tests/test_arena.py::KNOWN_EVENTS` 同词表）。

---

### 18.5 确定性 / 复现判据

**判据：同一 `(ArenaConfig 取值, spawn_seed, dynamics_seed)` ⇒ 逐事件一致的事件序列与逐字段一致的实体状态。** 该判据由 D1（两条随机源）、D2（`reset()` 幂等）与 D3–D5 的消费顺序共同保障。

| # | 机制 | 代码事实 |
|---|---|---|
| D1 | **两条随机源（已拆，A14 闭合）** | `spawn_seed` → `np.random.default_rng(spawn_seed)`（**出生/再生**：`reset()` 布局、`_free_spot`、regrowth）；`dynamics_seed` → `np.random.default_rng(dynamics_seed)`（**逐步动力学**：猎物游走）。两者均为 `core §3` 整数子种子，由调用方经 `SeedManager.seed("arena_spawn"/"arena_dynamics", index)` 派生后传入（`core §3` 整数种子例外；实验路径 `experiment/collect.py`、`pipeline`）。`arena/` 内**不出现** `import random`、全局 `np.random.*` 调用、或任何时间/OS 熵来源 |
| ⚠️ D2 | **`reset()` 幂等** | `reset()` **重建两条 RNG**（`default_rng(spawn_seed)` / `default_rng(dynamics_seed)`），并**先清空 `self.obstacles`** 再就地逐个生成障碍（S9）。因此同一 arena 反复 `reset()` 得到**逐字段一致**的初始局面（障碍位置与半径、每条鱼的位置/航向、每个猎物的位置/尺寸）。由 `test_reset_idempotent_on_same_instance` 守护（同时断言障碍的 `pos` 与 `radius`） |
| D3 | **reset 内消费顺序** | 障碍 → 鱼 → 猎物 → 捕食者。每障碍：1 次半径 uniform + `_free_spot`（≥1 次）；每鱼：`_free_spot(2.0)` + 1 次航向 uniform；每猎物：`_free_spot(1.0)` + 1 次航向 uniform + 1 次尺寸 uniform；每捕食者：`_free_spot(3.0)` + 1 次航向 uniform |
| D4 | **每步唯一消费点** | 猎物游走：每条**存活**猎物 1 次 `dynamics_rng.normal(0.0, 0.8)`（`PreyPolicy.act`）；再生（每 `prey_regrowth_steps` 步）消费 `spawn_rng`。鱼、捕食者、障碍、looming 记账**均不消费 RNG** |
| D5 | **拒绝采样进入消费路径** | `_free_spot` 的采样**次数**取决于当前（本局）障碍布局，消费 `spawn_rng`，因此它是 spawn 流消费路径的一部分 —— 一旦改动障碍数量/半径范围/clearance，后续所有实体的随机流都会平移。**这是复现性最脆弱的一环**：改动障碍数量/半径范围/clearance 会使后续所有实体的随机流整体平移，同一 seed 下的初始世界随之改变，历史基线不可直接对比 |
| D6 | **推进粒度的无关性** | 「推进 k 步」（原 `api/session.py::Session.advance(steps=k)`，该服务层已按用户决定移除）就是 `k` 次 `step()`；每一步内的 RNG 消费只由**该步的状态**决定（D4：存活猎物数 × 1 次 normal）。因此「同一 seed 下推进到第 $k$ 步的状态」与「分几次调用推进到第 $k$ 步」无关（在 600 步上限内）。**注意**：这条只说粒度无关，不代表 `step()` 不消费 RNG |
| D7 | **测试守护** | `test_reset_deterministic_same_seed`（同 seed 实体一致）、`test_reset_different_seed_differs`（异 seed 不同）、`test_reset_idempotent_on_same_instance`（**同一实例二次 reset 一致**） |

**注意**：`DanioArena.__init__(config, *, spawn_seed, dynamics_seed)` 接受**已解析**的 `ArenaConfig` 与两个整数子种子；要复现一局，必须记录 `ArenaConfig` 的**实际取值**而非 YAML 路径 —— `experiment/runlayout.py` 落盘的 `arena_config_resolved.json` 即为此用。（原 `SessionCreate.arena_config_path` 随 `api/` 服务层一并移除。）

---

### 18.6 每鱼记录字段表（规范 §13）

`DanioArena.per_fish_log()` 返回 `{fish_id: 记录}`，**包含全部 12 条鱼（含已死鱼）**。

| 规范 §13 声明 | `per_fish_log()` 键 | 来源字段 | 状态 |
|---|---|---|---|
| generation | `generation` | `Fish.generation`（缺省 0；由构造 `generation` 注入，代循环经 `experiment/evolution_run.py` 传本代世代号） | ✅ |
| encounters | `encounters` | `Fish.encounters` | ✅ 语义为"$d < r_{capture}$ 的近距接触数"（S6）。**自 2026-09-26 起同时是 `实验与评价体系.md` §2.1 `prey_capture` 的分母** |
| captures | `captures` | `Fish.captures` | ✅ |
| capture attempts | `capture_attempts` | `Fish.capture_attempts` | ✅ **2026-09-26 新增**（用户裁定「进过口」口径）：每鱼每步**至多 1 次** —— 猎物 $d < r_{capture}$ **且**在猎人前向锥内**且**判定了尺寸口径，**不论吃到与否**（吃到走 `arena.prey_captured`，太小走 `arena.capture_attempt`）。因此**逐事件对齐**于既有事件，且恒有 `capture_attempts ≥ captures`。**曾**是 `实验与评价体系.md` §4 `prey_capture` 的分母，**2026-09-26 同日降为诊断列**（`capture_attempts − captures` = 「进过口但吃不下」的次数；§4 分母改指 `encounters`，见上两行）。由 `test_capture_attempts_counts_eaten_prey_as_well` 与 `test_too_small_to_eat_attempt_logged` 守护 |
| predator encounters | `predator_encounters` | `Fish.predator_encounters` | ✅ **已实现且已定稿**：捕食者**获得新目标**（被锁定）时 +1（S7）。由 `test_predator_encounter_recorded_on_acquisition` 守护。下游 `experiment §2.1/§2.2` 以此为 `escape success` 分母 |
| escape successes | `escape_successes` | `Fish.escape_successes` | ✅ 口径见 S17（仅对**仍存活**的丢失目标计数） |
| collisions | `collisions` | `Fish.collisions` | ✅ |
| energy trajectory | `energy_trajectory` | `Fish.energy_trace` | ✅ 能量结算后追加（**在死亡判定之前**）。故对**存活鱼**与**被捕食者吃掉的鱼**有 `len(energy_trajectory) == survival_steps`；对**饿死鱼**多 1 条（该步写了 trace 但未自增 `survival_steps`）。`test_per_fish_log_completeness` 只在无死亡场景（10 步）覆盖此断言 |
| size trajectory | `size_trajectory` | `Fish.size_trace` | ✅ 与 `energy_trajectory` 同步追加（同样多 1 条于饿死鱼） |
| survival steps | `survival_steps` | `Fish.survival_steps` | ✅ |
| motor commands | `motor_commands` | `Fish.motor_log`（`(ω, v)` 元组列表，**裁剪后**的值） | ✅ |
| **selected neural activity snapshots** | — | — | ❌ **未实现**：规范 §13 声明的最后一项需 DanioNet 接入，当前 `Fish` 无对应缓冲区 |

`Fish.genome_id`（经 `genome_ids` 注入，缺省 `"unknown"`）是实体属性、`Fish.generation` 由 `generation` 注入（缺省 0），**都不在 `per_fish_log()` 键内**；轨迹落盘（BC：`scripts/collect_trajectories.py`；整群回放：`scripts/run_arena.py --emit-behavior-trace`）直接读 `arena.fish[fid].genome_id`。

`per_fish_log()` **不含**位置 / 航向 / 尺寸的逐帧轨迹 —— 那属于 snapshot（`../api/API接口.md` §1.8）与后续的 trajectory 落盘（`../core/核心机制与数据流.md` §4）。

---

### 18.7 未认领的实现决定（指向 `research/notes/arena-api-决策认领表.md` A 节）

> **本节是本文档的契约状态核心。** 以下数值与语义由实现先于设计落地。**2026-09-26 已有 9 项被认领并落地**（A2/A4/A5/A6/A7/A8/A9/§12/§15，用户签署「按建议」，见 `research/notes/契约决策记录.md`「A3 签署结果」）：这些行转为**已定稿**，其余仍为 **`草案待确认`**，**不得写进论文与正式实验**。

| 认领编号 | 未认领的内容 | 本文档对应节 | 实现现状 |
|---|---|---|---|
| **A1** | 12 维感官编码的归一化公式（线性衰减、$rel$ 尺寸、looming 角扩张率、左右分侧规则） | §4、S20 | **大部分已定稿、已固化**；looming 已改角尺寸扩张率并修复恒 0（2026-09-26）；**仅余 `looming_norm`（R_loom）为标定占位**，play-test 标定后本项转已定稿 |
| **A2** ✅ | 捕食几何：`capture_radius = 4.61`、$\kappa = 1.25$（判据含边界）、**前向锥 120°（总锥角）** | §2.1、§2.2、§3.1 §8 | **2026-09-26 已裁决并全部落地**：半径与 κ 已进参数总表；**前向锥已实现**（`growth.capture_cone_degrees`）。未采纳「半径和」口径（§8 已知局限） |
| **A3** ✅ | 能量四系数 + 新增 $C_{pen}$（`collision_penalty`）与回报函数 $f$ | §2.1、§6 | 已实现；**四系数与 `collision_penalty` 均已进参数总表**（2026-09-26；表内 `status=no_basis`，依据 D＝设计选择）。`food_reward` 现为**均值**（按 `prey.size` 缩放、中点归一），A3 预算不变 |
| **A4** ✅ | 生长：改为**面积守恒式** `size ← min(size_max, sqrt(size^2 + g*prey_size^2))`，$g$ = `prey_area_gain` | §2.2、§3.1 §7 | **2026-09-26 已改**（用户裁决「面积式」）：局内生长可见、边际递减内生；`Fish.biomass` **字段删除**（消除「只写不读」）；`prey_area_gain` 已进参数总表（**标定占位** 0.2） |
| **A5** ✅ | `actors` 整组 14 项（含 `predator_turn_rate`、`escape_hold_steps`、`predator_max_chase_steps`） | §2.2 | 已实现；**已进 `configs/default_arena.yaml` 的 `actors:` 段与参数总表**（2026-09-26，登记为 play-test 旋钮） |
| **A6** ✅ | 边界策略：新增 `world.boundary`，默认 **`reflect`**（镜面反射） | §2.1、§3.1 §2 | **2026-09-26 已改**：`reflect` 确定性、不消耗随机数；旧 `clamp` 降为对照选项（隐性能耗使跨 seed 能量不可比） |
| **A7** ✅ | 碰撞语义：**硬不穿透**（投影回障碍表面、零反弹）+ **软惩罚**（按穿透深度扣能量 `collision_penalty`） | S4、§6 | **2026-09-26 已改**。事件 payload **未改动**（惩罚经 `energy_trace` 可观测）。⚠️ 计数仍近乎不触发（0 次/5 seed×600 步），故仍**不作 headline 指标** |
| **A8** ✅ | escape 判定：**威胁结局制** —— 曾被锁定 且 捕食者放弃后继续存活 ≥ `escape_hold_steps` 才计 | S17、§15 | **2026-09-26 已改**：仅换目标未过存活窗口者不计；另加**限时追击** `predator_max_chase_steps`（超时放弃，且在该鱼离开探测半径前不再锁定它） |
| **A9** ✅ | episode 终止：**一律跑满 `episode_steps`（600）**；个体死亡只冻结该个体 | S22、§15 | **2026-09-26 已改**：不再因团灭提前结束（提前结束使 episode 长度内生、破坏跨 seed 可比性） |
| **A10** ✅ | 天敌/猎物转向量纲：`predator_turn_rate = 5.0` **rad/s**，`wander_turn_std = 0.8` **rad/s** | S14、§2.2 | 已实现；**2026-09-26 已签接受 5.0 rad/s** |
| **§12** ✅ | prey 再生（R2 开放可再生）+ 高价值分级 + `food_reward` 随体型 | §12 | **2026-09-26 已落地**：每 `prey_regrowth_steps`（占位 25）补 1 只至 `n_prey`；高价值 = `size` 的 75th 分位（V 对 size 单调 ⇒ top-V ≡ top-size，故 α 无需取值）；回报见 A3 行 |
| **§15** ✅ | survival 定义与归一化 | §15 | **2026-09-26 已落地**：`S = survival_steps / 600`（固定分母、线性）；加权前须显式尺度归一化 |

另有两项**实现侧发现**，不属认领表原有编号，但同样不得在未确认前用于指标：

| # | 发现 | 证据 |
|---|---|---|
| ✅ F1 | ~~`looming_rate` 通道恒 0~~ | 已修（2026-09-26）：步前同相位角尺寸差分 + 缓存（§4.1、S20、M13） |
| F2 | ~~`PreyPolicy.avoid_gain` 是死参数~~ ✅ **已删除（2026-09-26）** | S12 |

---

### 18.8 MVP 边界（明确未做项）

| # | 未做项 | 说明 |
|---|---|---|
| M1 | 神经控制 | 鱼由外部 `actions` 驱动，Arena 不内嵌网络；DanioNet 推理已由 `pipeline/arena_episode.py` 接入（`scripts/run_chain.py`，DanioNet 驱动模型评估）。`generation` 可由构造注入（缺省 0；代循环已接入）。`Fish.genome_id` 已可由构造注入（`genome_ids`，P0-9，2026-09-26），缺省仍 `"unknown"` |
| M2 | ~~`predator_encounters` 恒 0~~ | ✅ **已实现**：目标获取计数，见 S7 |
| M3 | selected neural activity snapshots | 规范 §13 最后一项未实现；**owner = `connectome`/`DanioNet`（+ api 推送）**，arena 不缓存网络激活（见 §6） |
| M4 | 规范 §12 风险—收益冲突**场景布置** | **2026-09-26**：高价值 prey 的**定义**与 prey 再生已落地（§12）；但「高价值 prey 靠近捕食者 / resource-scarce 抬升 hunger」的**场景布置仍未做**，`environment` 字段已进 API 但**不改变任何参数**（见 `../api/API接口.md` §7.2） |
| M5 | 猎物主动逃跑 | `PreyPolicy` 不感知鱼；规范 §10 的 "proximity avoidance" 目前只有避障版本 |
| M6 | ~~`PreyPolicy.avoid_gain`~~ | ✅ **已删除（2026-09-26）**（S12、F2） |
| M7 | 捕食者能量 / 成长 / 死亡 | 捕食者恒存活、无代谢（S16、S18） |
| M8 | ~~配置加载~~ | ✅ **已闭合**（2026-09-26）：loader 落地（严格构造 + 分层）；YAML↔dataclass 键名对齐；**调用方已接线** —— `experiment/runlayout.py`（落盘 `arena_config_resolved.json`）、`scripts/run_arena.py`、`scripts/collect_trajectories.py`、`experiment/environments.py`、`pipeline/arena_episode.py` 均读取 arena 配置（原 `api/` 服务层已按用户决定移除） |
| M9 | 障碍物为非凸形状 | 障碍只用圆 `contains`，无多边形/复杂几何 |
| M10 | 流体动力学 | 规范 §1 已明确排除，非遗漏 |
| M11 | ~~episode 内重生成猎物~~ | ✅ **已实现**（2026-09-26，§12 R2）：每 `prey_regrowth_steps`（占位 25）补 1 只至 `n_prey`；新个体以 `arena.spawn` 事件落盘 |
| M12 | 手动控制通路 | 原 `api/session.py` 的 `advance(use_expert=False)` 未暴露手动 action 端点；**该服务层已按用户决定移除**，手动 action 通路待随 `api/` 重写落地 |
| ✅ M13 | ~~looming 通道无信息~~ | 已修（2026-09-26）：`nearest_predator_angular_size` + 步前缓存；回归 `tests/test_sensing_looming.py`。剩余：`looming_norm` 标定占位（A1） |
| M14 | `world.episode_seconds` 未进代码 | YAML 有 `world.episode_seconds: 30`，`WorldConfig` 无对应字段（§2.1 的 ⚠️ 行），故 `dt`/步数与它无关 |

---

### 18.9 测试覆盖（`tests/test_arena.py`，29 项）

| # | 测试 | 守护的契约 |
|---|---|---|
| 1 | `test_reset_deterministic_same_seed` | D1/D3：同 seed 下鱼的 pos/heading、猎物的 pos/size 逐字段一致 |
| 2 | `test_reset_different_seed_differs` | 种子确实生效（防"seed 被忽略"的假确定性） |
| 3 | `test_obs_shape_and_ranges` | 12 维、有限、全在 $[0,1]$（§3.1 §4） |
| 4 | `test_population_counts_match_frozen_defaults` | 12 / 24 / 3 / 6（`../../../docs/参数总表.json` 冻结量） |
| 5 | `test_capture_grants_food_reward` | §3.1 §7 + §8 + §6：捕获后 `captures == 1`、猎物死亡、payload 的 `food_reward == round(0.12*size/0.45, 6)`、能量 == `0.5 - 0.0008 + reward`（`abs=1e-9`）；鱼朝向显式设为 0（锥内） |
| 6 | `test_too_small_to_eat_attempt_logged` | §4.2 #2：`result == "too_small_to_eat"`，且猎物存活（朝向同样显式对齐前向锥） |
| 7 | `test_starvation_death_event` | §4.2 #6：$E < C_{base}$ 时判死并发射 `arena.energy_depleted`，`fish_id` 正确 |
| 8 | `test_episode_terminates_at_max_steps` | §3.1 §2 + §4.2 #8：600 步 `done`，`payload["steps"] == 600` |
| 9 | `test_turn_inertia_reduces_bigger_fish_turning` | §3.1 §5：$\omega_{eff}$ 随 size 单调下降 |
| 10 | `test_all_events_in_known_vocabulary` | **§4.2 词表权威守护**：120 步内所有事件均以 `arena.` 开头且在 `KNOWN_EVENTS` 内 |
| 11 | `test_per_fish_log_completeness` | §6 字段齐全（含 `predator_encounters` 的**存在性**）+ 无死亡场景下轨迹长度一致 |
| **12** | `test_reset_idempotent_on_same_instance` | **D2**：同一实例二次 `reset()` 后，每条鱼的 pos、每个障碍的 pos **与 radius** 与首次完全一致 |
| **13** | `test_step_after_episode_end_is_inert` | **S21**：跑满 600 步后再 `step()` 仍 `done`、`step_idx` 保持 600、`arena.episode_end` 计数不增 |
| **14** | `test_dead_fish_not_credited_escape` | **S17**：把 `pred.target_fish_id` 指向一条已死鱼后 `step()`，该鱼 `escape_successes` 保持 0 且本步无 `arena.escape` |
| **15** | `test_predator_encounter_recorded_on_acquisition` | **S7**：捕食者从"无目标"切到目标鱼的下一步，该鱼 `predator_encounters >= 1` |

| **16** | `test_forward_cone_blocks_capture_from_behind` | **§8 前向锥**：半径内但在猎人身后 0.5 的猎物**不可捕**、不发 `capture_attempt`；但 `encounters` 仍 +1（**S6 纯距离语义不变**） |
| **17** | `test_boundary_reflect_is_deterministic_and_inbounds` | **§2.1**：`reflect` 为镜面反射（位置与朝向均按解析值反射）且保持在世界内 |
| **18** | `test_boundary_clamp_is_still_available` | **§2.1**：`clamp` 保留为对照选项 |
| **19** | `test_boundary_config_default_and_validation` | **§2.1**：默认 `boundary == "reflect"`；非法取值在推进时即 `ValueError`（不静默回退） |
| **20** | `test_area_conservation_growth` | **§7**：捕获后 `size == min(max_size, sqrt(size0^2 + g*prey_size^2))`，且 `size` 严格增大（局内生长可见） |
| **21** | `test_prey_reward_is_mean_preserving` | **§6/§12**：猎物尺寸取区间中点时回报恰等于 `energy.food_reward`（归一化使均值不变） |
| **22** | `test_prey_regrowth_refills_toward_capacity` | **§12（R2）**：低于承载量时每 `prey_regrowth_steps` 补 1 只、新增 id 连续、发 `arena.spawn` |
| **23** | `test_escape_requires_survival_window` | **§15（A8）**：锁定 → 放弃 → 存活窗口未满**不计**；满 `escape_hold_steps` 后计 1 次且事件恰好 1 条 |
| **24** | `test_extinction_does_not_end_episode_early` | **§15（A9）**：鱼全灭后 `step()` 仍不 `done`、`step_idx` 正常推进 |
| **25** | `test_predator_gives_up_after_limited_chase` | **§9（A8）**：`max_chase_steps` 内保持追击、超出即放弃（返回巡游速度）；被 ban 的鱼在探测半径内不再被重新锁定 |
| **26** | `test_predator_size_coupling_invariant` | **§8 耦合约束**：`predator_size >= kappa * max_size` |
| **27** | `test_capture_boundary_is_inclusive_at_max_size` | **§8 边界含入**（捕食者→鱼）：`size_ratio == kappa` 仍被吃、`max_size` 恰可捕、其上不可捕；猎人朝向已对齐锥内 |
| **28** | `test_prey_capture_boundary_is_inclusive` | **§8 边界含入**（鱼→prey）：`size_ratio == kappa` 仍可吃（朝向对齐） |
| **29** | `test_capture_attempts_counts_eaten_prey_as_well` | **§18.4.2 #2/#3**：吃到猎物时 `capture_attempts` 与 `captures` 同步 +1（恒有 `capture_attempts ≥ captures`） |

**未覆盖**（已知缺口）：`reset` 侧的 24 条 `arena.spawn` 无专项测试；`_free_spot` 的 200 次回退分支无测试；`observe()` 对死鱼仍返回向量（S23）无测试；**`arena.collision` 的触发**在默认场景下仍无法自然发生（见 A7 行）。

⚠️ 其中前两项**在默认场景下无法自然触发**（见附录实测：5 个 seed × 600 步的 `arena.collision` 与 `arena.escape` 均为 0），要补测试必须手工构造场景（如把鱼直接放到障碍上 / 手工指定 `pred.target_fish_id` 后让其换目标）。

---

### 18.10 变更纪律

改下列任一内容，必须**同时**改对应文件，否则 CI 或契约会静默漂移。**代码 / 配置 / 测试 / 样例路径为仓库根相对；文档交叉引用为本文件所在目录相对。**

| 改动 | 必须同步 |
|---|---|
| **事件词表**（增删 `type`、改 payload 字段名/含义） | ① `src/evogenesis/arena/env.py` 的发射点；② `tests/test_arena.py::KNOWN_EVENTS`；③ 本文档 §4.2；④ `../core/核心机制与数据流.md` §5.1 摘要表；⑤ `schemas/examples/event_log_example.jsonl`（重生成，见 §4.4）；⑥ 若涉及前端消费：`frontend/src/api/arena.ts` 的 `ArenaEvent`；⑦ 若涉及 WS 推送：`../api/API与系统工程.md` §4.1 R11 |
| **冻结参数值**（`capture_size_ratio` / 世界尺寸 / Hz / 步数 / 种群数） | ① `configs/default_arena.yaml`（**唯一事实来源**）；② `src/evogenesis/arena/config.py` 默认值；③ `../../../docs/参数总表.json`；④ `tests/test_arena.py::test_population_counts_match_frozen_defaults`（种群数）；⑤ 本文档 §2；⑥ 报告中的参数表快照 |
| **标定占位 / play-test 旋钮**（`prey_area_gain`、`collision_penalty`、`prey_regrowth_steps`、`escape_hold_steps`、`predator_max_chase_steps`、`capture_cone_degrees`、`world.boundary`、`sensing.looming_norm`、`energy.*` 4 项、`growth` 余项、`actors` 余项） | ① `configs/default_arena.yaml`（**唯一事实来源**；`actors:` 段与全部新键已就位）；② `config.py` 默认值；③ 本文档 §2/§16；④ `../../../docs/参数总表.json`（**2026-09-26 已全部登记**）；⑤ `tests/test_arena_config.py` 的 YAML↔dataclass 漂移守护 |
| ⚠️ **障碍生成方式 / `n_obstacles` / 半径范围 / clearance** | ① `env.py::_spawn_obstacles()` 与 `reset()`（必须保持"先清空、再就地逐个生成"）；② 本文档 §3.2 S9、§5 D2/D5；③ `test_reset_idempotent_on_same_instance`；④ **一切历史冒烟基线作废**（RNG 流全局平移） |
| **12 维感知顺序**（`sensing.DIM_NAMES` / `observe()` 返回顺序） | ① `src/evogenesis/arena/sensing.py`（docstring 与 `DIM_NAMES`）；② `schemas/examples/README.md` 的 12 维语义表；③ `schemas/examples/trajectory_example.jsonl`（观测向量列序）；④ `../core/核心机制与数据流.md` §4.2 的 `observation` 行；⑤ `../connectome/DanioNet设计规范.md` §2；⑥ `../../../docs/参数总表.json` `sensory_dim`；⑦ **顺序冻结是验收清单硬性要求，改动需双方同步** |
| **looming 口径**（`sensing.max_predator_angular_size` + `env.py` 步首/步尾采样、`Fish._looming_rate`） | ① `sensing.py`（角度定义/聚合）与 `env.py`（相位/结算/归一）；② 本文档 §4.1 / S20 / F1 / M13；③ 认领表 A1；④ `tests/test_sensing_looming.py` |
| **`ArenaConfig` 字段增删** | ① `config.py`；② `configs/default_arena.yaml`；③ 本文档 §2；④ `../api/API接口.md` §7.2（`arena_config_path` 一旦真正生效，字段集即成为对外契约） |
| **`per_fish_log()` 键名** | ① `env.py`；② `tests/test_arena.py::test_per_fish_log_completeness` 的 `required` 集合；③ 本文档 §6；④ `Danio_Arena设计与实现说明.md` §13 |

---

### 18.11 冒烟基线
**可复现生成**：`scripts/smoke_arena.py`（12 条 ExpertPolicy 驱动的鱼、默认 `ArenaConfig()`、600 步）：

```bash
uv run python scripts/smoke_arena.py
```

**单 seed 细节（seed 250927）**

| 项 | 值 |
|---|---|
| 猎物捕获 | 17 / 24 初始（`arena.prey_captured` = 17） |
| 存活 | 11 / 12（`arena.fish_captured` = 1） |
| `arena.spawn` | 52（24 初始猎物 + 12 鱼 + 3 捕食者 = 39，另加 13 条再生猎物） |
| 逃生 `arena.escape` | 1 |
| 吞吐 | 约 311 steps/s（单进程、CPU） |

**多 seed 实测（600 步，默认配置）**：

| seed | `arena.prey_captured` | `arena.fish_captured` | `arena.collision` | `arena.escape` | `arena.energy_depleted` | 存活 |
|---|---|---|---|---|---|---|
| 1 | 15 | 1 | 0 | 16 | 0 | 11 |
| 7 | 14 | 2 | 0 | 6 | 0 | 10 |
| 42 | 25 | 2 | **208** | 4 | 0 | 10 |
| 1234 | 17 | 2 | 0 | 6 | 0 | 10 |
| 250927 | 17 | 1 | 0 | 1 | 0 | 11 |

⚠️ **本基线为 2026-09-26 A14 拆分随机流（`arena_spawn`/`arena_dynamics`）后的新基线，与更早基线不可直接对比**。
同日本版还含：D2 composite 捕食分量口径（`capture_rate`）、`growth.capture_success_prob`（默认 1.0）、删除 `avoid_gain`/死分支。
**上一版**（seed 250927：19 捕获 / 1 被捕食 / escape 9 / spawn 57 / 约 154 steps/s）、更早版（12 / 3 / 0 / 39 / 约 327）与最初（9 / 24 / 约 236）**均已作废**。另注：出生流改动会改变同一 seed 的初始世界（§18.5 D5）。

**三条给指标口径的提醒（2026-09-26 更新）**：
① **`arena.escape` 不再零方差**：威胁结局制（A8）使其自发触发（本表 1–16 次/局）。
② **`arena.collision` 多数 seed 为 0，但并非结构不可达**：本表 `seed 42 = 208`（同一步簇发）；仍**不宜作 headline**，需专门「密集障碍」对照场景（§18.7 A7）。
③ **饥饿仍不会发生**（`C_base × 600 = 0.48 < E_max = 1.0`，且有食物补回），默认配置下 `arena.energy_depleted` 观测不到；**死亡全部来自捕食者**。

## 19. 合并后细化与明确清单

本节把合并审查中仍会阻断复现、论文或正式实验的事项列成执行清单。它不替责任人做设计裁决；每项必须在上游契约、配置、代码和测试之间闭环后，才能从“草案待确认”改为“已定稿”。

### P0：冻结前必须闭合

1. ~~**配置单一事实源（B7/M8）**~~ ✅ **已闭合（2026-09-26）**：通用 loader（`core/config.py`，PyYAML+Pydantic v2，优先级 `CLI > env > file > default`）；Arena 侧键名对齐（`live_demo.*` → `population.*`，补 `actors:` 段，由 `tests/test_arena_config.py` 漂移守护）；**调用方接线** —— `experiment/runlayout.py` 加载 Arena 配置并落盘 `arena_config_resolved.json`。参数表与实验配置现已可复现。
2. ~~**12 维 observation（A1）**~~ ✅ **已闭合（2026-09-26）**：`looming_rate` 已改**角尺寸扩张率**（公式/相位/分母/max 聚合/不可见置 0 均写入 §4.1），回归 `tests/test_sensing_looming.py`；仅余 `R_loom` 标定占位。**残留（P1）**：观测输入统计与回归基线尚未补。
3. **世界尺度与捕食几何**：**已闭合**（2026-09-26，方案 B）——wu 不与 BL 固定换算（§2 尺度声明），`capture_radius = 4.61`、`sensing.radius = 18`、`κ = 1.25`（判据含边界 `≥`、耦合约束 `predator_size ≥ κ·max_size`）均已定稿。**余**：~~捕获成功率是否引入随机失败~~ ✅ 已闭合（2026-09-26，见 §8 a：新增 `growth.capture_success_prob`，默认 1.0）。

### P1：正式实验前必须明确

4. **生长语义**：`biomass` 目前只写不读，且演化管线只传 DNA；须明确它是单 episode 展示量，还是要跨 episode/世代传递。若跨代，必须上移到 genome/development/evolution 契约，不能由 Arena 单独决定。
5. **终止与指标**：固定团灭是否提前终止、`survival` 的归一化、`escape` 的成功定义、`collision` 的后果，以及 `energy_efficiency` 的计算口径。默认场景下 collision、escape 和 starvation 几乎不可观测，正式实验前需设计可触发的对照场景。
6. **事件样例闭环**：`schemas/examples/event_log_example.jsonl` 仍需按本文件 §18 的 8 类事件词表重生成，或明确降级为仅示意信封形状；不能继续让样例字段与实现词表分裂。
7. **文献登记**：采纳 Arena lane 的生物学依据时，从 `bibliography.md` 当前编号之后继续登记（不得复用 RGCD 的 #111–#130），再把引用写回合并稿和参数总表。文献只支撑合理性校验或设计依据，不自动变成 Arena 契约。

8. **H3 历史依赖探针（可选增强，§14）**：任务定义已定稿、实现未做；实现前须定 \(D\)、\(r_H\) 并评估是否新增事件类型（若新增，按 §18.10 同步 `KNOWN_EVENTS` / core §5.1 / 事件样例）。

### P2：实现完善

9. 接入 `selected neural activity snapshots`，或从规范 §13 删除该字段并在 DanioNet/API 文档同步降级。
10. ~~删除或接线 `PreyPolicy.avoid_gain`~~ ✅ 已删除（2026-09-26）；余：补 `arena.collision`、活鱼 escape、空种群终止和 `_free_spot` 回退分支的专项测试。
11. 将合并稿中的所有旧文件名引用改为本文件；两个旧路径仅保留兼容入口，不再承载独立契约。
