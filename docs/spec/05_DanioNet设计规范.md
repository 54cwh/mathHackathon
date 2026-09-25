# DanioNet 设计规范

## 1. 六类神经元
- Sensory
- Prey
- Threat
- Integrator / Memory
- Inhibitory
- Motor

六类都属于基础谱系；viable individual 每类至少一个。

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

## 8. Baselines
- MLP
- GRU
- Fixed Sparse RNN

要求 trainable parameter count 同一数量级。

## 9. Ablations
- w/o GRN
- homogeneous tau
- w/o spatial wiring cost
- P1：w/o epistasis
