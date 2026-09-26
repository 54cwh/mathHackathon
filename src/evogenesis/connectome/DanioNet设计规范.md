# DanioNet 设计规范

> **管辖范围**：六类功能语义、12 维输入**语义**、神经动力学、连续动作、lifetime learning 与遗传边界、baselines/ablations。产出：activation / 动作 `(ω,v)` / `ΔW`。（层级与归属见 `AGENTS.md`「文档层级与优先级」。）
> 状态：**v1.8 已定稿（冻结 2026-09-26）**。范围外：12 维编码（`Arena §4.1`）、BC 损失权重（`learning`）、ExpertPolicy 权重（`Arena §11`）、BC 数据预算（`learning`）。

## 1. 六类神经元
- Sensory
- Prey
- Threat
- Integrator-Memory（token: `integrator_memory`）
- Inhibitory
- Motor

六类都属于基础谱系；viable individual 每类至少一个。

依据：六类是**功能抽象**，其划分参照斑马鱼感觉运动回路 `[bib#6][bib#7]` 与全脑连接组组织 `[bib#14]`，不对应特定真实细胞类型（真实类型远超 6 类 `[bib#84]`；见 `docs/设计依据审计.md` 表 3）。

**owner**：六类**功能语义**归本文件；`type_i` 如何由 GRN **产出**归 `development/RGCD数学模型.md` §6。⚠️ `argmax` 是离散化理想化（真实 fate 为连续谱 `[bib#75]`），实现宜同时记录 `z_i` 分布/熵。

## 2. 12 维输入

**语义 / 顺序 / 值域由本文件冻结**（网络输入契约）；由视野计算这 12 个数的**编码规则**归 `arena/Danio_Arena设计与实现说明.md` §4.1（Arena 侧任何编码都必须产出满足本契约的向量）。

| # | 名称 | 语义 | 值域 | dtype |
|---|---|---|---|---|
| 0 | `prey_left_signal` | 左视场猎物种群强度 | `[0,1]` | `float32` |
| 1 | `prey_right_signal` | 右视场猎物种群强度 | `[0,1]` | `float32` |
| 2 | `threat_left_signal` | 左视场天敌种群强度 | `[0,1]` | `float32` |
| 3 | `threat_right_signal` | 右视场天敌种群强度 | `[0,1]` | `float32` |
| 4 | `obstacle_left_signal` | 左视场障碍强度 | `[0,1]` | `float32` |
| 5 | `obstacle_right_signal` | 右视场障碍强度 | `[0,1]` | `float32` |
| 6 | `prey_relative_size` | 最近可见猎物相对自身体型 | `[0,1]` | `float32` |
| 7 | `predator_relative_size` | 最近可见天敌相对自身体型 | `[0,1]` | `float32` |
| 8 | `looming_rate` | 天敌视角扩张率（逼近速度） | `[0,1]` | `float32` |
| 9 | `current_speed` | 上一步推进 \(v_{t-1}\)（\(v\in[0,1]\)） | `[0,1]` | `float32` |
| 10 | `energy` | 归一化能量 \(E_t/E_{\max}\) | `[0,1]` | `float32` |
| 11 | `hunger` | \(1-E_t/E_{\max}\) | `[0,1]` | `float32` |

**值域约束（定稿）**：12 维一律为 `[0,1]` 的 `float32`；Arena 侧无论用线性距离核、相对尺寸还是角扩张率，都必须截断/归一化到该区间。其中 `energy` 与 `hunger` 互补（和恒为 1）；前 8 维与 `looming_rate` 为非负强度量。

依据：prey/threat 通道对应斑马鱼视觉捕食与威胁回避 `[bib#8]`；hunger/energy 对应内部状态调制决策 `[bib#9][bib#10]`；looming 为逃避触发量。

**消费方式（定稿）**：DanioNet 按此契约直接消费，**不重复校验值域**（12 维落在 `[0,1]` 由 Arena 编码保证，§4.1）；§3 动力学的 \(H_t\) 即第 11 维 `hunger`（\(H_t=x_t[11]\)）。

✅ **已修复（2026-09-26）**：`looming_rate` 由 Arena 侧改为**角尺寸扩张率**（`θ=2·arctan((size/2)/r)`，步首/步尾采样、max 聚合、按 `sensing.looming_norm` 归一），不再恒 0（见 `arena §4.1` 与 `tests/test_sensing_looming.py`）。值域 `[0,1]` 契约不变。

## 3. 神经动力学
\[
h_i^{t+1}
=
\left(1-\frac1{\tau_i}\right)h_i^t
+
\frac1{\tau_i}
\phi
\left(
\sum_j A_{ij}w_{ij}h_j^t
+
U_ix_t
+
m_iH_t
+b_i
\right)
\]

默认 \(\phi=\tanh\)。其中 \(w_{ij}=w^{(0)}_{ij}+\Delta w_{ij}\) 为有效权重（\(\Delta W\) 见 §6）。\(\Delta W\) 遵守 Dale sign 约束：符号由突触前类型固定，只改幅度（\(w_{ij}=sign(w^{(0)}_{ij})\cdot softplus(\theta_{ij})\)）`[bib#29][bib#30][bib#31]`。\(\Delta W\) **形状与 \(W^{(0)}\) 相同**（\(N\times N\)，batch 内 padding 到 48），**仅在既有连接支撑上非零**：有效权重 \(W=A\odot\big(\mathrm{sign}(W^{(0)})\odot \mathrm{softplus}(\Theta)\big)\)（逐元素），初值 \(\Theta=\mathrm{softplus}^{-1}(|W^{(0)}|)\)（`EvoGenesis项目总纲.md` §4；约定 \(\mathrm{softplus}^{-1}(0):=0\)，支撑外 \(W^{(0)}=0\)），故 \(\Delta W=W-W^{(0)}\)。支撑 \(A\) 训练期**冻结**（不新增连接），padding 行列恒 0 并从 loss / 梯度 / 更新中排除；初始 \(\Delta W=0\) 在 `float32` round-trip 下容差 \(\lesssim 10^{-7}\)（`softplus∘softplus⁻¹` 舍入，非精确 0）；\(\tau\ge 1\)（RGCD §11 `tau_min`）为本模块前提，\(\tau<1\) 被拒（\(1/\tau>1\) 会放大）；被优化的是与 \(W^{(0)}\) 同形状、同 dtype 的 \(\Theta\)（支撑外梯度屏蔽），\(\mathrm{sign}(W^{(0)})\) 训练期不变。张量与梯度统一 `float32`（`core §7`）。

> **数值保护（实现细节）**：`softplus⁻¹` 在 `|W⁰|` 较大时改用等价渐近式，切换阈值 `_SOFTPLUS_INVERSE_SWITCH = 40.0`（float32 下避免 `expm1` 溢出为 inf）；不改上式语义。
> **构造参数 `priors`（实现扩展）**：`DanioNet(..., priors=NetworkPriors|None)` 允许注入全局先验表 `U/m/b`（缺省由 `master_seed` 派生），供测试与复现对照；不影响默认行为。

依据：该式是标准漏积分发放（firing-rate）模型的离散形式；\(\tau_i\) 的语义与量级见 `development/RGCD数学模型.md` §11。

**`U_i,m_i,b_i` 来源（定稿）**：三者按 **cell type** 取固定先验、不学习——`U_i=U_{type_i}`、`m_i=m_{type_i}`、`b_i=b_{type_i}`，其中 `U∈R^{6×12}`、`m,b∈R^6` 由 seed 初始化（`U~N(0,(1/√12)²)`、`m~N(0,0.1²)`、`b~N(0,0.1²)`）。理由：RGCD 输出契约 `(A,Z,τ,W⁰,M)` 保持冻结，感官增益经 cell type 与基因型挂钩；`ΔW` 只改 `w`，与 §7 遗传边界自洽。属**设计选择**（登记 `docs/参数总表.json`）。

**与发育期 viability 的关系**：`development/RGCD数学模型.md` §7 的零输入动力学检查在发育期以 \(b_i=0\) 近似（该处不产出 \(b_i\)）；本模块用它自己的 \(b_{type_i}\) 对同一组 §7 判据复核，作为最终判定；复核沿用发育期结构 \(W^{(0)}\)（\(\Delta W\) 不遗传，§7，故不参与 viability 判定）。

**符号约束消融开关（已实现，2026-09-26）**：为支撑 `learning §4` 的「有约束 vs 无约束」消融，`DanioNet` 提供 `sign_constrained: bool`（默认 `True`）——`False` 时参数**直接作为有效权重** `W = A ⊙ Θ`（不经 `sign(W⁰)·softplus(Θ)`，符号自由可翻转），两路径初值同为 `W⁰`（初始 `ΔW=0`）、支撑/非活跃屏蔽相同，供消融对照；**默认路径仍是约束版**。训练侧（`learning`）的 `sign_constrained` 须与网络构造一致（不一致即 `ValueError`）。

**初始化与 padding（定稿）**：本模块接收的 \(M\) 亦用于屏蔽 \(W^{(0)}\) 的非活跃行列（使 \(\Delta W\) 在非活跃处恒 0）。初始激活 \(h_i^{0}=0\)（`float32`，形状 `(N,)`，batch 内 padding）。padding 宽度取 `development.max_neurons`（`configs/default_model.yaml`，现 48），不在此硬编码。`U/m/b` 为按 cell type 的**全局单表**（全体个体取值相同），由 master seed 在 `network_init` 命名空间（`core §3`，id=5，`index=0`）**确定性派生**（构造时计算；因确定性，各实例等价，实现无跨实例缓存）；其标准差取 `network.input_weight_std` / `network.hunger_gain_std` / `network.neuron_bias_std`（现 0.289 / 0.1 / 0.1；文档式 `U~N(0,(1/√12)²)` 的 σ=0.28868，config 取整为 0.289）。

所有网络 padding 到 `development.max_neurons` nodes，通过 neuron mask / adjacency mask batch：**neuron mask 即 RGCD 输出的 \(M\)（active neuron mask，padding 位为 0）**，adjacency mask 即支撑 \(A\)；二者共同界定参与动力学与动作池的神经元（非活跃神经元的行/列恒 0，\(h\) 保持 0，不进入 motor 池与 viability 复核）。

## 4. 连续动作
\[
\omega_t=\tanh(y_\omega)
\]

\[
v_t=\sigma(y_v)
\]

其中：

\[
\omega_t\in[-1,1],\quad v_t\in[0,1]
\]

“Escape”不是离散标签，而是高威胁状态下的大转向 + 高推进。

**合成规则（定稿，G3）**：设 \(M_L,M_R\) 为 left/right motor 池（划分见 §5），取**均值池化**：

\[
y_\omega=\overline{h}_{M_L}-\overline{h}_{M_R},\qquad y_v=\overline{h}_{M_{\mathrm{motor}}},
\]

其中 \(M_{\mathrm{motor}}=M_L\cup M_R\) 为**全 motor 池**（与 RGCD 产出的 active neuron mask \(M\) 不同名），\(\overline{h}_{S}=|S|^{-1}\sum_{i\in S}h_i\) 为集合 \(S\) 上的激活均值。left 池主导得 \(\omega>0\)（即 `Arena §5` 的 \(+\theta\) 方向）；\(y_v\) 可为负，经 \(\sigma\) 映射回 \(v\in[0,1]\)。均值对池大小不变、零新参数；属**设计选择**。视觉左右由渲染坐标决定，不在本契约内。

## 5. 左右竞争
Motor neurons 标记 left/right side。Inhibitory prior 提高 contralateral inhibition，允许左右 motor pools 竞争。

**标记规则（定稿，G2）**：把 motor 池按发育坐标 \(x_i\) 的**中位数二分**——\(x_i\) 低于中位者标 left、其余标 right（同值按神经元索引破平）。保证两池非空（满足 `development/RGCD数学模型.md` §7 developmental viability）。说明：位置是**归一化发育方域**坐标、非世界坐标，"left/right"为此轴上的标记约定，世界手性由 §4 的 \(\omega\) 符号约定固定。属**设计选择**。实现说明：本规则的**语义 owner 是本节**；因数据流方向为 `development → connectome`，`development` 侧 viability 复核保留一份**等价**实现（`rgcd._motor_sides`）以避免反向依赖成环，两份须保持一致并由测试守护：**两侧均在按 \(M\) 过滤后的 motor 集上做中位二分**（非活跃 motor 不入池）。

依据：左右转向竞争与 heading-direction 回路 `[bib#6]`；自发探索中的左右交替与 ARTR 群体 `[bib#7]`。

## 6. Lifetime Learning
Stage 1：透明 ExpertPolicy 产生轨迹。

Stage 2：Behavior Cloning。训练契约（预算、采样与标准化、损失与权重、优化器）归 `learning/行为克隆学习.md` §3（单一 owner）。本文件只固定两件事：被训练的对象是 §3/§4 的 DanioNet（权重 `W = W⁰ + ΔW`），以及 §4 的有界动作映射 \(\hat\omega=\tanh(y_\omega)\)、\(\hat v=\sigma(y_v)\)（标准化只改损失尺度，不改该映射）。

Stage 3：PPO/SAC 仅作为 P2，可完全不做。

## 7. 遗传边界
训练后的 \(\Delta W\) 不遗传。

每代：

\[
DNA\rightarrow Development\rightarrow W^{(0)}
\rightarrow Lifetime\ Learning
\]

依据：以 genome 编码先天结构、后天学习不遗传，是 genomic bottleneck 的核心主张 `[bib#1][bib#3]`。

## 8. Baselines

> 实现状态（2026-09-26）：**已实现**（`src/evogenesis/connectome/baselines.py`，`tests/test_baselines.py`）；§9（消融）仍属实验层待实现。
>
> **接线状态（2026-09-26）**：Experiment C 横向对照**已接**——编排 `experiment/baseline_run.py`、薄 CLI `scripts/run_baselines.py`（消费 `build_baselines` 与各 `complexity()`，§3.3）。
- MLP
- GRU
- Fixed Sparse RNN

**公平性判据（定稿）**：`|log10(N_base) − log10(N_ours)| ≤ 1`，统一按**连接（权重）数**比较（不计 bias），不得用 HyperNEAT 的 CPPN 规模冒充 substrate 参数量。对照基准取本规范实例 `N_ours = E_A = 190`（支撑边数，`seed 250927` / `initial_population` 的 `index 12`；2026-09-27 更正：原记 `index 6` 实测为 162，无 viable 个体，190 出现在 `index 12`）。

**尺寸反解（定稿；按「连接数最接近 190 且满足判据」求解）**：

| baseline | 连接数公式（权重） | 解 | 连接数 | `|log10 差|` |
|---|---|---|---|
| MLP | \(14H\)（\(12H + 2H\)） | \(H = 14\) | 196 | 0.013 |
| GRU | \(3H^2 + 38H\)（\(3H\cdot12 + 3H\cdot H + 2H\)） | \(H = 4\) | 200 | 0.022 |
| Fixed Sparse RNN | \(\lvert\text{mask}\rvert + 14H\)（见下） | \(H = 12\)，递归密度 \(\rho = 0.15\) | ≈190（实测 mask 决定） | ≈0 |

- **Fixed Sparse RNN**：递归矩阵 \(W_{rec}\) 为**固定稀疏**（mask 于初始化时按 \(\mathrm{Bernoulli}(0.15)\) 抽样后**冻结**，与 §9 `w/o GRN` 同密度；禁 self-loop 不加限制），输入/读出为稠密；\(\rho\) 属**设计选择（D）**，无外部依据。
- **符号约束**：三个 baseline **均不施加 Dale 符号约束**（等价 `sign_constrained=False`）；DanioNet 的 Dale 约束视作其归纳偏置计入对比，§9 另设「BC 有/无 Dale」消融单独隔离该变量。
- **初始化**：权重由 `core §3` 的 `baseline_init` 命名空间（id = 10）派生，实体 `t` 取该个体在种群内的 `index`；与 DanioNet 的 `network_init`（全局单表）分离。`Fixed Sparse RNN` 的递归**支撑 mask 走独立命名空间 `baseline_support`（id = 13）**，同 `t` 语义——支撑与初始权重分属两条独立随机流，避免支撑与幅度同源相关（若同源，被 `mask` 选中的递归权重会系统性偏负，使该臂被人为削弱）。`float32`。

**接口契约（与 DanioNet 同构，保证同一套 BC 训练与测量可用）**：`n_neurons`（list，长度 = batch，元素 = H）、`active_counts`、`theta`（**唯一** `nn.Parameter`，供 `learning::train_bc` 的 Adam 更新）、`sign_constrained=False`、`reset()`、`step(observations) -> (ω, v)`、`complexity()`（返回 `parameter_count` / `active_edges` / `macs_implemented` / `macs_theoretical` / `flops_*`）。基线按 **batch=1** 规格化——内部状态 `h` 为单条轨迹；Experiment C 与 BC 均以 1 agent/seed 使用，故 `n_neurons` 长度恒为 1（DanioNet 支持 batch，基线不承诺多 batch 状态语义）。
> **`support` 不在基线契约内**：DanioNet 的 `support`（bool mask，支撑 \(A\)）是 DanioNet 专有缓冲，`MLPPolicy` / `GRUPolicy` 无此属性（仅 `FixedSparseRNNPolicy` 有 `support`）；`experiment/measure.py::network_complexity` 只适用于 DanioNet。基线的结构量一律经自身 `complexity()` 自报，不共用 DanioNet 的支撑缓冲。
> **动作映射与 DanioNet 一致（定稿，2026-09-26）**：基线 `step()` 的 `(ω, v)` 与 `§4` 同映射——\(\omega=\tanh(y_\omega)\)、\(v=\sigma(y_v)\)，故 \(v\in[0,1]\)，与 DanioNet 完全相同。此前基线对两维同用 `tanh`（\(v\in[-1,1]\)），与 `Arena` 把 \(v\) 截到 \([0,1]\) 的读出口径冲突、使基线约一半速度被削为 0，已修正为 `σ` 读出（统一口径，`experiment §3.3`）。

**FLOPs 口径（单步前向，含 bias 不计入 MACs）**：\(\text{MACs}_{impl}\) 按**稠密**权重数计（含被 mask 的位置），\(\text{MACs}_{theo}\) 按**实际连接数**计（Sparse RNN 二者不等）；\(\text{FLOPs} = 2 \times \text{MACs}\)；不含 \(\tanh\) 等非线性（与 `实验与评价体系.md` §2.4 同约定）。

依据与量化：发育编码网络的对照基线取 NEAT / HyperNEAT / ES-HyperNEAT（Stanley & Miikkulainen 2002；Stanley et al. 2009；Risi & Stanley 2012）。出处：`research/reference/design-basis-connectome.md`。

## 9. Ablations
实现口径（定稿 2026-09-26；三臂经 `--override` 零代码可跑）：

- **homogeneous τ**：令 `connectome.tau_min = connectome.tau_max = τ*`，`RGCD §11` 的 `τ_i = τ_min + (τ_max−τ_min)·σ(·)` 退化为常数 `τ*`；τ* 网格 `{τ_min, (τ_min+τ_max)/2, τ_max}`（由 config 派生）。**校验口径**：`DanioNet` 对 **τ 的下限只校验活跃神经元**（`M=True`）——padding 槽位 `τ` 恒为构造初值 `1.0`、与动力学无关，否则 `τ* > 1` 的臂会被 padding 误报越界（2026-09-26 修正）。
- **w/o spatial wiring cost**：`connectome.distance_lambda = 0`（`RGCD §8` 的 `−λd_ij` 项消失）。
- **BC 有 / 无 Dale 符号约束**：`DanioNet(sign_constrained=False)`（§3 开关；无约束路径 `W = A ⊙ Θ`），由 `scripts/run_bc.py --no-sign-constrained` 驱动 `[bib#30][bib#31]`。
- `w/o GRN`：**已实现**（2026-09-26）——`connectome.ablation_w_grn = true` 时 `A ~ Bernoulli(ablation_random_density)` 独立采样（禁 self-loop），`N / τ / W⁰ 幅度 / Dale / viability` 全保留（数学口径见 `RGCD §8` 消融段）；默认 `false`。运行：`run_chain.py --override connectome.ablation_w_grn=true`。
- allele 聚合：加性（mean）vs 完全显性（max）
- P1：w/o epistasis（未实现）

> H3 的“异质 vs 同质 τ”对比以**性能—效率 Pareto 前沿**为判据 `[bib#23]`。臂清单与命令见 `experiment/实验与评价体系.md` §3.4。

## 阅读问题（待确认）

> 逐份阅读本文时发现的未定义点，需与 04 / 07 / 16 对齐后确认。

（无遗留：
- #2 `U/m/b` → §3（cell-type 固定先验）；#3 动作合成 → §4（均值池化）；#4 左右标记 → §5（x 中位数二分）；#6 `w/o GRN` → §9（同密度随机结构）。
- #1 12 维编码归 `arena/Danio_Arena设计与实现说明.md` §4.1（现 `草案待确认` + 认领表 A1）；本文件 §2 只定义语义/顺序/值域。
- #5 `λ_ω,λ_v` 归 `learning/行为克隆学习.md` §6；ExpertPolicy 权重 `w_p0,k_H,w_d,w_o` 归 `arena/Danio_Arena设计与实现说明.md` §11（G4）。
- #7 BC 轨迹条数/预算归 `learning/行为克隆学习.md` §3；padding 到 48 + mask 见本文件 §3。）
