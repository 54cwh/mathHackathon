# RGCD 数学模型规范

## 1. 输入输出
RGCD 输入：

\[
G,\Theta_D,\xi
\]

输出：

\[
(A,Z,\tau,W^{(0)},M)
\]

其中 \(M\) 为 active neuron mask。

## 2. Motif affinity
对于 motif \(M_k\) 与窗口 \(s\)：

\[
a(M_k,s)=1-\frac{d_H(M_k,s)}{|M_k|}
\]

整条序列：

\[
q_k(S)=TopKMean_{s\subset S}a(M_k,s)
\]

形成：

\[
\mathbf q(G)\in[0,1]^8
\]

## 3. Developmental domains
初始 precursor：

\[
N_0=24
\]

六个 domains：

\[
D_S,D_P,D_T,D_M,D_I,D_O
\]

分别对应 sensory / prey / threat / integrator-memory / inhibitory / motor。

每个 precursor 有位置：

\[
\mathbf p_i=(x_i,y_i)
\]

和 domain bias \(\mathbf d_i\)。

## 4. 唯一正式离散 GRN
\[
\boxed{
\mathbf g_i^{r+1}
=
(1-\rho)\mathbf g_i^r
+
\rho\,\sigma
(
W_g\mathbf g_i^r+
B\mathbf q(G)+
P\mathbf p_i+
\mathbf b
)
}
\]

默认：
- steps = 12
- \(\rho=0.35\)
- sigmoid

报告、代码、可视化均使用这一式。

## 5. Proliferation
\[
p_i^{divide}
=
\sigma(\mathbf w_d^T\mathbf g_i^{12}+b_d)
\]

每个 precursor 最多分裂一次。

daughter：

\[
\mathbf p_{daughter}=\mathbf p_i+\epsilon_p
\]

\[
\mathbf g_{daughter}=\mathbf g_i+\epsilon_g
\]

最终：

\[
24\le N\le48
\]

## 6. Cell identity
\[
\mathbf l_i=U\mathbf g_i+\mathbf c_{domain(i)}
\]

\[
\mathbf z_i=softmax(\mathbf l_i)
\]

\[
type_i=\arg\max_k z_{ik}
\]

domain bias 保证六个基础谱系有 developmental competence，DNA/GRN 决定各谱系扩张和属性。

## 7. Viability
### Developmental viability
每种基础 fate：

\[
N_k\ge1
\]

Motor 至少有一个 left-associated 与一个 right-associated output neuron。

### Functional viability
存在：

\[
Sensory\rightsquigarrow Motor
\]

有向路径。

### Dynamical viability
zero-input 运行 50 steps：
- 无 NaN
- 无 Inf
- state norm 不爆炸
- 不永久全饱和

## 8. Connection probability
\[
\ell_{ij}
=
\mathbf z_i^T C\mathbf z_j
-\lambda d_{ij}
+\gamma R(\mathbf g_i,\mathbf g_j,\mathbf p_i,\mathbf p_j)
+b_A
\]

\[
P(A_{ij}=1)=\sigma(\ell_{ij})
\]

\[
d_{ij}=\|\mathbf p_i-\mathbf p_j\|_2
\]

不允许 self-loop。通过 bias calibration 使平均 density 约 10%–20%。

## 9. Fixed compatibility prior
| pre \\ post | S | P | T | M | I | O |
|---|---:|---:|---:|---:|---:|---:|
| S | -2.0 | 1.8 | 1.8 | 0.6 | 0.2 | -0.5 |
| P | -2.0 | 0.2 | -0.8 | 1.4 | 0.3 | 1.2 |
| T | -2.0 | -0.8 | 0.2 | 1.2 | 0.8 | 1.5 |
| M | -1.5 | 0.3 | 0.3 | 1.3 | 1.0 | 1.4 |
| I | -2.0 | 0.4 | 0.4 | 0.9 | 0.0 | 1.5 |
| O | -2.0 | -1.5 | -1.5 | -0.5 | -0.5 | -1.0 |

该矩阵是人工 prior，MVP 不学习它。

## 10. Initial weight
\[
|w_{ij}^{(0)}|
=
softplus(
\mathbf u^T[\mathbf g_i;\mathbf g_j;\mathbf z_i;\mathbf z_j]+b_w
)
\]

Dale-like sign：

\[
sign(w_{ij})=
\begin{cases}
-1,& type_i=Inhibitory\\
+1,& otherwise
\end{cases}
\]

## 11. Time constant
\[
\tau_i
=
1+9\cdot
\sigma(
\mathbf a^T\mathbf g_i+b_\tau
)
\]

所以：

\[
\tau_i\in[1,10]
\]

## 12. Genome Sensitivity
单 base mutation：

\[
G\rightarrow G^{(l)}
\]

edge distance：

\[
d_{edge}^{(l)}
=
\frac{\|A(G)-A(G^{(l)})\|_1}{N^2}
\]

time constant distance：

\[
d_{\tau}^{(l)}
=
\frac{1}{N}
\sum_i|\tau_i(G)-\tau_i(G^{(l)})|
\]

behavior effect：

\[
\Delta B_l=
w_1\Delta Capture+
w_2\Delta Escape+
w_3\Delta Survival+
w_4\Delta Energy
\]

三个量并列展示，不强行混成单一总分。
