# DanioNet 设计规范

> **管辖范围**：六类功能语义、12 维输入**语义**、神经动力学、连续动作、lifetime learning 与遗传边界、baselines/ablations。产出：activation / 动作 `(ω,v)` / `ΔW`。（层级与归属见 `AGENTS.md`「文档层级与优先级」。）
> 状态：**v1.1 已定稿（冻结 2026-09-26）**。范围外：12 维编码（`Arena §4.1`）、BC 损失权重（`learning`）、ExpertPolicy 权重（`Arena §11`）、BC 数据预算（`learning`）。

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
1. prey_left_signal
2. prey_right_signal
3. threat_left_signal
4. threat_right_signal
5. obstacle_left_signal
6. obstacle_right_signal
7. prey_relative_size
8. predator_relative_size
9. looming_rate
10. current_speed
11. energy
12. hunger

依据：prey/threat 通道对应斑马鱼视觉捕食与威胁回避 `[bib#8]`；hunger/energy 对应内部状态调制决策 `[bib#9][bib#10]`；looming 为逃避触发量。维度顺序与值域冻结（**本文件为 12 维 observation 的语义 owner**）；由视野计算这 12 个数的**编码规则**归 `arena/Danio_Arena设计与实现说明.md` §4.1（Arena 产出满足本契约的向量）。

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

默认 \(\phi=\tanh\)。其中 \(w_{ij}=w^{(0)}_{ij}+\Delta w_{ij}\) 为有效权重（\(\Delta W\) 见 §6）。\(\Delta W\) 遵守 Dale sign 约束：符号由突触前类型固定，只改幅度（\(w_{ij}=sign(w^{(0)}_{ij})\cdot softplus(\theta_{ij})\)）`[bib#29][bib#30][bib#31]`。\(\Delta W\) **形状与 \(W^{(0)}\) 相同**（\(N\times N\)，batch 内 padding 到 48），**仅在既有连接支撑上非零**：\(\Delta W=M\odot\Delta\theta\)，\(M=A\) 且训练期**冻结**（不新增连接），padding 行列恒 0 并从 loss / 梯度 / 更新中排除；被优化的是与 \(W^{(0)}\) 同形状、同 dtype 的 \(\theta\)（支撑外梯度屏蔽），\(sign(w^{(0)})\) 训练期不变。张量与梯度统一 `float32`（`core §7`）。

依据：该式是标准漏积分发放（firing-rate）模型的离散形式；\(\tau_i\) 的语义与量级见 `development/RGCD数学模型.md` §11。

**`U_i,m_i,b_i` 来源（定稿）**：三者按 **cell type** 取固定先验、不学习——`U_i=U_{type_i}`、`m_i=m_{type_i}`、`b_i=b_{type_i}`，其中 `U∈R^{6×12}`、`m,b∈R^6` 由 seed 初始化（`U~N(0,(1/√12)²)`、`m~N(0,0.1²)`、`b~N(0,0.1²)`）。理由：RGCD 输出契约 `(A,Z,τ,W⁰,M)` 保持冻结，感官增益经 cell type 与基因型挂钩；`ΔW` 只改 `w`，与 §7 遗传边界自洽。属**设计选择**（登记 `docs/参数总表.json`）。

所有网络 padding 到 48 nodes，通过 neuron mask / adjacency mask batch。

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
y_\omega=\overline{h}_{M_L}-\overline{h}_{M_R},\qquad y_v=\overline{h}_{M},
\]

其中 \(\overline{h}_{S}=|S|^{-1}\sum_{i\in S}h_i\) 为集合 \(S\) 上的激活均值。left 池主导得 \(\omega>0\)（即 `Arena §5` 的 \(+\theta\) 方向）；\(y_v\) 可为负，经 \(\sigma\) 映射回 \(v\in[0,1]\)。均值对池大小不变、零新参数；属**设计选择**。视觉左右由渲染坐标决定，不在本契约内。

## 5. 左右竞争
Motor neurons 标记 left/right side。Inhibitory prior 提高 contralateral inhibition，允许左右 motor pools 竞争。

**标记规则（定稿，G2）**：把 motor 池按发育坐标 \(x_i\) 的**中位数二分**——\(x_i\) 低于中位者标 left、其余标 right（同值按神经元索引破平）。保证两池非空（满足 `development/RGCD数学模型.md` §7 developmental viability）。说明：位置是**归一化发育方域**坐标、非世界坐标，"left/right"为此轴上的标记约定，世界手性由 §4 的 \(\omega\) 符号约定固定。属**设计选择**。

依据：左右转向竞争与 heading-direction 回路 `[bib#6]`；自发探索中的左右交替与 ARTR 群体 `[bib#7]`。

## 6. Lifetime Learning
Stage 1：透明 ExpertPolicy 产生轨迹。

Stage 2：Behavior Cloning。每条 viable DanioNet 相同学习预算：

\[
K=20
\]

mini-batch updates。

\[
\mathcal L=
\lambda_\omega MSE(\hat\omega,\omega^*)+
\lambda_v MSE(\hat v,v^*)
\]

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
- MLP
- GRU
- Fixed Sparse RNN

要求 trainable parameter count 同一数量级。

依据与量化：发育编码网络的对照基线取 NEAT / HyperNEAT / ES-HyperNEAT（Stanley & Miikkulainen 2002；Stanley et al. 2009；Risi & Stanley 2012）。"同一数量级"建议判据 `|log10(N_base) − log10(N_ours)| ≤ 1`，统一按连接（权重）数比较，并注意不得用 HyperNEAT 的 CPPN 规模冒充 substrate 参数量。出处：`research/reference/design-basis-connectome.md`。

## 9. Ablations
- `w/o GRN`：关闭 GRN 发育步，`A` 改按 `Bernoulli(0.15)` 独立采样（禁 self-loop），保留同 `N`、同 \(\tau\)、同 `W⁰` 幅度与 Dale 符号——只隔离"GRN 发育"变量（同密度、同尺度）
- allele 聚合：加性（mean）vs 完全显性（max）
- homogeneous tau（基线取异质 τ 的均值；另做 τ 网格扫描防选值偏袒）`[bib#27][bib#28]`
- w/o spatial wiring cost（\(\lambda=0\)）
- BC 有 / 无 Dale 符号约束 `[bib#30][bib#31]`
- P1：w/o epistasis

> H3 的“异质 vs 同质 τ”对比以**性能—效率 Pareto 前沿**为判据 `[bib#23]`。

## 阅读问题（待确认）

> 逐份阅读本文时发现的未定义点，需与 04 / 07 / 16 对齐后确认。

（无遗留：
- #2 `U/m/b` → §3（cell-type 固定先验）；#3 动作合成 → §4（均值池化）；#4 左右标记 → §5（x 中位数二分）；#6 `w/o GRN` → §9（同密度随机结构）。
- #1 12 维编码归 `arena/Danio_Arena设计与实现说明.md` §4.1（现 `草案待确认` + 认领表 A1）；本文件 §2 只定义语义/顺序/值域。
- #5 `λ_ω,λ_v` 归 `learning/行为克隆学习.md` §6；ExpertPolicy 权重 `w_p0,k_H,w_d,w_o` 归 `arena/Danio_Arena设计与实现说明.md` §11（G4）。
- #7 BC 轨迹条数/预算/padding 归 `learning` 数据管线（§3 已定 padding 到 48 + mask）。）
