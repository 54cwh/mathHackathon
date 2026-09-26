# DanioNet 设计规范

## 1. 六类神经元
- Sensory
- Prey
- Threat
- Integrator-Memory（token: `integrator_memory`）
- Inhibitory
- Motor

六类都属于基础谱系；viable individual 每类至少一个。

依据：六类是**功能抽象**，其划分参照斑马鱼感觉运动回路 `[bib#6][bib#7]` 与全脑连接组组织 `[bib#14]`，不对应特定真实细胞类型（见 `docs/设计依据审计.md` 表 3）。

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

依据：prey/threat 通道对应斑马鱼视觉捕食与威胁回避 `[bib#8]`；hunger/energy 对应内部状态调制决策 `[bib#9][bib#10]`；looming 为逃避触发量。维度顺序冻结，Arena↔DanioNet 的编码规则见 `arena/Danio_Arena设计规范.md`（待闭合）。

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

默认 \(\phi=\tanh\)。

依据：该式是标准漏积分发放（firing-rate）模型的离散形式；\(\tau_i\) 的语义与量级见 `development/RGCD数学模型.md` §11。

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

## 5. 左右竞争
Motor neurons 标记 left/right side。Inhibitory prior 提高 contralateral inhibition，允许左右 motor pools 竞争。

依据：左右转向竞争与 heading-direction 回路 `[bib#6]`；自发探索中的左右交替与 ARTR 群体 `[bib#7]`。marker 规则待定（G2）。

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
- w/o GRN
- homogeneous tau
- w/o spatial wiring cost
- P1：w/o epistasis

## 阅读问题（待确认）

> 逐份阅读本文时发现的未定义点，需与 04 / 07 / 16 对齐后确认。

1. **12 维输入与 Arena 视野的对应未定义**：§2 列出 12 项，但各项如何由 arena/Danio_Arena设计规范.md 的 left/right channel、radius、FOV 计算未写（arena/Danio_Arena设计规范.md 阅读问题 #1 的另一侧）。
2. **`U_i x_t`、`m_i H_t`、`b_i` 的来源未定义**：§3 动力学中这三项是发育得到、固定先验还是可学习未写（关联 G1）。
3. **动作合成未定义（G3）**：§4 的 `y_ω,y_v` 取自哪些 motor 细胞、左右 pool 如何合成 `ω,v` 未写，与 §5“左右竞争”的衔接缺失。
4. **左右 motor 标记规则未定义（G2）**：§5 称“Motor neurons 标记 left/right side”，但标记规则未写。
5. **BC 超参与 Stage 1 专家未定义**：§6 的 `λ_ω,λ_v` 未给；ExpertPolicy 权重 `w_p0,k_H,w_d,w_o`（G4）不在 config。
6. **baseline 参数量“同一数量级”未量化（G9）**：§8 未给容许倍数与对齐口径。
7. **Ablation 实现未定**：§9 的 `w/o GRN`（随机固定结构？）、`homogeneous tau`（取何值）未写；`w/o epistasis` 需先确认 epistasis 已实现。
8. **BC 训练数据与预算未定义**：每条 viable 网络的轨迹条数、K=20 的 batch 定义、是否含 padding/mask 处理未写。
