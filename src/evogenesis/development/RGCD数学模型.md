# RGCD 数学模型规范

> **管辖范围**：RGCD 全部算法与发育产物 `(A,Z,τ,W⁰,M)`、cell type 产出、viability 判据。（层级与归属见 `AGENTS.md`「文档层级与优先级」。）
> 状态：**v1.5 已定稿（冻结 2026-09-26）**。范围外：G2 left/right 标记（`DanioNet §5`）、G3 动作合成（`DanioNet §4`）；\(\theta_N,\theta_H\) 数值为标定任务（见 `docs/参数总表.json`）。

## 1. 输入输出

**输入**

| 记号 | 类型 / 形状 | 定义 | 来源 |
|---|---|---|---|
| \(G\) | 二倍体 genome：2×`ChromosomePair`，每链 128 bp ∈{A,C,G,T} | 个体基因组；RGCD 只消费其派生量 \(\mathbf q(G)\in[0,1]^8\)（genome §6）与位点表达 \(E_A,E_B\in\{0,0.5,1\}\)（genome §3），不直接读碱基 | `genome` |
| \(\Theta_D\) | §13 参数集合（各张量形状见表） | 发育参数（\(W_g,B,P,\mathbf b,U,\mathbf c_{domain},\mathbf w_d,b_d,C,\lambda,\gamma,b_A,\mathbf u,b_w,\mathbf a,b_\tau,\epsilon_p,\epsilon_g\)），由 seed 确定性初始化 | §13 / §2 |
| \(\xi\) | RNG 流（命名空间 `development`） | 发育随机源（分裂 Bernoulli、\(\epsilon_p,\epsilon_g\)）；由 `core` seed manager 派生，**不另立随机源** | `core §3` |

**输出**（active \(N\in[24,48]\)；dtype 统一 `float32`，`core §7`；batch 内 padding 到 48 的约定见 `DanioNet §3`）

| 记号 | 形状 | 含义 |
|---|---|---|
| \(A\) | \(\{0,1\}^{N\times N}\) | 二值邻接；无 self-loop；density ∈ [0.10,0.20] |
| \(Z\) | \([0,1]^{N\times6}\) | \(z_i=\mathrm{softmax}(l_i)\)（§6） |
| \(\tau\) | \([1,10]^{N}\) | 时间常数（§11） |
| \(W^{(0)}\) | \(\mathbb R^{N\times N}\) | 初始有效权重，符号由突触前类型定（§10） |
| \(M\) | \(\{0,1\}^N\) | active neuron mask（padding 位为 0） |

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

说明：\(a=1-d_H/|M_k|\) 等价于"每列 one-hot、失配等权"的退化 PWM。标准 motif 表示是 PWM/PSSM（Stormo 2000），本项目采用简化式以提高可解释性与可编辑性，须在报告中声明为简化并配 PWM 对照。出处：`research/reference/design-basis-genome.md`。

> **定义 owner**：\(a(M_k,s)\)、`TopKMean`、\(q^{(h)}\)、\(q(G)\) 的定义归 `genome/生物学与进化遗传学基础.md` §3/§6；本节为**单向引用**，只保留供 RGCD 使用的参数取值。

**参数（定稿）**：
- motif 长度 \(|M_k|=6\) bp；滑窗 \(|s|=6\) bp、步长 1；`TopK` 的 \(K=3\)。
- 8 条 motif 目录由 **`motif_catalog` 命名空间**（`core §3`）在实验 master seed 下一次性抽样固定（各位置在 `alphabet` 上均匀 i.i.d.，不随个体或代变化）；owner 为 genome 侧（`genome/motifs.py`），RGCD 只消费 \(\mathbf q(G)\)、不直接读目录。
- 扫描范围：每个 haplotype 有 **2 条染色体**（各 `bp_per_haplotype_chromosome`=128 bp，合计 haploid 256 bp）；窗口在**各染色体内**滑动、**不跨染色体边界**，`TopKMean` 在两条染色体的**窗口并集**上取 top-\(K\)。实现侧须按 2 条染色体存储（不塌成单串）。
- 依据与定位：长度 6 bp 落在真实 TF motif 6–12 bp 区间下沿，属 A-life 尺度（`docs/设计依据审计.md` R5：Stormo 2000；Lambert et al. 2018）；\(K=3\) 与 motif 条数为**设计选择**（无外部依据，登记 `docs/参数总表.json`）。

## 3. Developmental domains
初始 precursor：

\[
N_0=24
\]

六个 domains：

\[
D_S,D_P,D_T,D_M,D_I,D_O
\]

分别对应 sensory / prey / threat / integrator_memory / inhibitory / motor。

（`D_M` 的显示名为 Integrator-Memory，机器可读 token 统一为 `integrator_memory`。）

每个 precursor 有位置：

\[
\mathbf p_i=(x_i,y_i)
\]

和 domain bias \(\mathbf d_i\)。

**放置（定稿）**：24 个 precursor 在六个 domain 间**均匀分配**（每域 4 个）。位置取 **domain-blocked 均匀随机**：把归一化发育单位方域 \([0,1]^2\) 划为 \(3\times2=6\) 个 block（尺寸 \(1/3\times1/2\)），domain 按 \([S,P,T,M,I,O]\) 顺序映射到 block；每个 precursor

\[
\mathbf p_i=\mathbf{origin}_{domain(i)}+(u_1/3,\;u_2/2),\qquad u\sim U[0,1]^2 .
\]

位置空间为**归一化发育单位方域**（非 Arena 坐标）；§8 的距离项 \(\lambda\) 绑定此口径。\(\mathbf d_i=\mathbf c_{domain(i)}\) 为 one-hot 域偏置。

依据与限定：随机放置足以复现特异功能连接（Hill et al. 2012 *PNAS* `[bib#123]`）；domain-blocked 为**工程选择**——给 \(-\lambda d_{ij}\) 非平凡空间结构，避免位置-命运硬耦合。

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

**形状（定稿）**：\(\mathbf g_i\in\mathbb R^8\)（`grn.dim=8`）、\(\mathbf q(G)\in\mathbb R^8\)、\(\mathbf p_i\in\mathbb R^2\) 原样输入（不做 embedding）；\(W_g\in\mathbb R^{8\times8}\)、\(B\in\mathbb R^{8\times8}\)、\(P\in\mathbb R^{8\times2}\)、\(\mathbf b\in\mathbb R^8\)。

**初始化（定稿）**：\(W_g\) 取 Glorot/Xavier `[bib#126]` 后重标定谱半径 \(\rho_{\mathrm{spec}}(W_g)=0.9\)；\(B,P\sim\mathcal N(0,(1/\sqrt8)^2)\)；\(\mathbf b\sim\mathcal N(0,0.1^2)\)。全部由 seed manager 派生。

依据与限定："谱半径 \(<1\Rightarrow\) echo-state property"是**经验条件**（Yildiz et al. 2012 `[bib#127]` 给出反例），故按稳定性启发式使用、并记录 \(\rho_{\mathrm{spec}}(W_g)\)；未找到阻尼 sigmoid GRN 的专属初始化惯例，其余尺度为**设计选择**。

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

**参数与初始化（定稿）**：\(\mathbf w_d\in\mathbb R^8\)、\(b_d\in\mathbb R\)；\(\mathbf w_d\sim\mathcal N(0,(1/\sqrt8)^2)\)、\(b_d=0\)（分裂概率约 0.5）。分裂扰动 \(\epsilon_p\in\mathbb R^2\sim\mathcal N(0,0.05^2)\)（单位方域）、\(\epsilon_g\in\mathbb R^8\sim\mathcal N(0,0.1^2)\)；\(\mathbf p_{daughter}\) 裁剪回 \([0,1]^2\)。尺度均为**设计选择**（无外部依据，登记 `docs/参数总表.json`）。

## 6. Cell identity
\[
\mathbf l_i=U\mathbf g_i+\mathbf c_{domain(i)}
\]

\[
\mathbf z_i=softmax(\mathbf l_i),\qquad \mathbf l_i,\ \mathbf z_i\in\mathbb R^6
\]

\[
type_i=\arg\max_k z_{ik}
\]

domain bias 保证六个基础谱系有 developmental competence，DNA/GRN 决定各谱系扩张和属性。

**参数与初始化（定稿）**：\(U\in\mathbb R^{6\times8}\)、\(\mathbf c_{domain}\in\mathbb R^6\)；\(U\sim\mathcal N(0,(1/\sqrt8)^2)\)；\(\mathbf c_{domain}\) 为 one-hot（本域位 \(+1.5\)，余为 0），给六个基础谱系 developmental competence。

**owner**：`type_i` 如何由 GRN **产出**（本式）归本文件；六类**功能语义**与 left/right motor 标记归 `connectome/DanioNet设计规范.md` §1/§5。`argmax` 为离散化理想化（真实 fate 为连续谱 `[bib#75]`），建议同时记录 `z_i` 分布/熵。

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
zero-input（\(x_t\equiv0,\ H_t\equiv0\)）从 \(h^0=\mathbf 0\) 运行 50 steps，\(\phi=\tanh\)。判据与阈值（**定稿**）：
- (i) 无 NaN、无 Inf；
- (ii) \(|h_i^t|<1\) 对所有 \(i,t\) 成立（**解析保证**：更新是 \(h_i^t\) 与 \(\tanh(\cdot)\in(-1,1)\) 的凸组合，权重 \((1-1/\tau_i),\,1/\tau_i\ge0\) 且和为 1，由 \(h^0=0\) 归纳即得——非工程阈值）；
- (iii) 不永久全饱和：尾 10 步（\(t=40..49\)）平均饱和比例 \(<0.9\)，饱和定义为 \(|h_i^t|>1-10^{-3}\)；
- (iv) \(\rho_{\mathrm{spec}}(W_g)<1\)（tanh 稳定性启发式，`[bib#127]`）。

(iii)(iv) 为**工程判据**（设计选择）；(ii) 是模型的数学性质，报告可直接引用。

## 8. Connection probability
\[
\ell_{ij}
=
\mathbf z_i^T C\mathbf z_j
-\lambda d_{ij}
+\gamma R(\mathbf g_i,\mathbf g_j)
+b_A
\]

\[
P(A_{ij}=1)=\sigma(\ell_{ij})
\]

\[
d_{ij}=\|\mathbf p_i-\mathbf p_j\|_2
\]

不允许 self-loop。通过 bias calibration 使平均 density 约 10%–20%。

依据：空间布线代价项 \(-\lambda d_{ij}\) 有充分文献支撑——在 logit 中加入线性距离项等价于指数距离规则 \(P\propto e^{-\lambda d}\)（Ercsey-Ravasz et al. 2013 *Neuron*；Waxman 1988；Kaiser & Hilgetag 2004；综述 Bullmore & Sporns 2012）；cell-type 兼容项 \(z_i^T C z_j\) 对应 `[bib#4]`。注意 \(\lambda\) 有量纲，本项目在**归一化发育单位方域**上取值（见下），不照搬文献的 mm 口径值。出处：`research/reference/design-basis-connectome.md`。

**\(\gamma R(\cdot)\) 形式（定稿）**：取**中心化双线性 / Pearson 相关**。令 \(\bar g,\hat\sigma\) 为本代 \(N\) 个神经元在各分量上的均值与标准差，\(\hat{\mathbf g}_i=(\mathbf g_i-\bar g)\oslash\hat\sigma\)，则

\[
R_{ij}=\frac{1}{8}\sum_{k=1}^{8}\hat g_{ik}\hat g_{jk}\in[-1,1],\qquad K=I\ (\text{零参数}).
\]

中心化**只用于 \(R\) 项**，§4 的 \(\mathbf g\) 语义不变。依据：转录组/细胞类型相似度预测连线的双线性模型（Qiao et al. 2024 *eLife* `[bib#111]`；Kovács et al. 2020 *PNAS* `[bib#112]`；识别分子为异源、\(K\) 可非对角但 \(I\) 为可解释 MVP，Sanes & Zipursky 2020 `[bib#119]`）。**限定**：单用表达相似度预测连线的证据仅 AUC≈0.64（`[bib#111]`；Hayashi et al. 2022 反 Hebbian `[bib#121]`），故 \(R\) 按**弱偏置**使用并须报 \(\gamma=0\) 消融。

**系数（定稿）**：\(\gamma=1.0\) 固定（属 \(\Theta_D\)，不演化；敏感性搜索 \(\{0.5,1,2\}\)）；\(\lambda=2.0\)（单位方域，\(E[d]\approx0.521\Rightarrow\lambda d\approx1.04\)，与 \(z_i^\top Cz_j\in[-2,2]\) 配平）。\(b_A\) 用**二分反解**到实测 off-diagonal density 落在 \([0.10,0.20]\)（目标 0.15）：

\[
b_A=\mathrm{logit}(p_{target})-E[z_i^\top Cz_j]+\lambda E[d]-\gamma E[R].
\]

\(\gamma,\lambda,b_A\) 均为项目标定/设计选择（\(\lambda\) 的量纲由单位方域归一化定义）。出处：`research/reference/rgcd-wiring-and-placement.md`。

## 9. Fixed compatibility prior
| pre \\ post | S | P | T | M | I | O |
|---|---:|---:|---:|---:|---:|---:|
| S | -2.0 | 1.8 | 1.8 | 0.6 | 0.2 | -0.5 |
| P | -2.0 | 0.2 | -0.8 | 1.4 | 0.3 | 1.2 |
| T | -2.0 | -0.8 | 0.2 | 1.2 | 0.8 | 1.5 |
| M | -1.5 | 0.3 | 0.3 | 1.3 | 1.0 | 1.4 |
| I | -2.0 | 0.4 | 0.4 | 0.9 | 0.0 | 1.5 |
| O | -2.0 | -1.5 | -1.5 | -0.5 | -0.5 | -1.0 |

该矩阵是人工 prior，MVP 不学习它。其数值无外部依据，属项目设计选择；仅可引用脑区通路/连接 motif 的符号模式（如 `[bib#14]`）作定性参照，不代表定量测量。

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

依据：Dale's principle（Dale 1935；Eccles, Fatt & Koketsu 1954 形式化），符号由**突触前**神经元类型决定，与突触后无关。建模实现可参见 Parisien et al. 2008、Cornford et al. 2021。注意共释放反例（Saunders 2015）存在，本项目按简化处理。出处：`research/reference/design-basis-neuro.md`。

**参数与初始化（定稿）**：\(\mathbf u\in\mathbb R^{28}\)（\([\mathbf g_i;\mathbf g_j;\mathbf z_i;\mathbf z_j]\) 为 \(8+8+6+6\)）、\(b_w\in\mathbb R\)；\(\mathbf u\sim\mathcal N(0,(1/\sqrt{28})^2)\)，\(b_w=\mathrm{softplus}^{-1}(\bar w)\) 取稳态权重均值 \(\bar w=0.5\)。

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

依据与限定：在 \(hz=20\)（\(\Delta t=50\) ms）下，\(\tau_i\) 步等效于 \(50\text{–}500\) ms 的网络级整合时间常数——与 NMDA / GABA_B 及数百 ms 决策整合同量级，可辩护；但作为单神经元膜时间常数偏大（皮层约 20 ms）。文档须写明此处 \(\tau\) 的语义为"网络级整合"，且 \(\tau=1\) 退化为无记忆。出处：`research/reference/design-basis-neuro.md`。

**参数与初始化（定稿）**：\(\mathbf a\in\mathbb R^8\)、\(b_\tau\in\mathbb R\)；\(\mathbf a\sim\mathcal N(0,(1/\sqrt8)^2)\)、\(b_\tau=0\)（\(\tau\) 均值约 5.5，展布由 \(\mathbf g\) 驱动）。

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

behavior effect（四维向量，不合成标量）：

\[
\Delta \mathbf B_l=
(\Delta Capture,\ \Delta Escape,\ \Delta Survival,\ \Delta Energy)
\]

三个量——\(d_{edge}^{(l)}\)、\(d_{\tau}^{(l)}\)、\(\Delta \mathbf B_l\)——并列展示，不合成单一总分；权重 \(w_1\ldots w_4\) 不使用。

**\(\Delta B_l\) 四分量口径（定稿）**：对每个 locus \(l\)，取 \(K\) 个**匹配块**（同 `environment_id`、同 `episode_seed`，每块一条野生型 \(+\) 一条突变体），分量沿用 fitness 同口径的**原始率**（不做代内 min-max、不除以野生型基线）：

\[
\Delta X_l=\frac1K\sum_{k=1}^{K}\big[x_X(G^{(l)},k)-x_X(G,k)\big],\qquad X\in\{\mathrm{Capture,Escape,Survival,Energy}\}
\]

\[
x_{\text{Survival}}=\frac{\text{survival\_steps}}{600},\quad
x_{\text{Capture}}=\frac{\text{captures}}{\max(\text{capture\_attempts},1)},\quad
x_{\text{Escape}}=\frac{\text{escape\_successes}}{\max(\text{predator\_encounters},1)},\quad
x_{\text{Energy}}=\frac{E(T)-E_{\max}}{T}.
\]

分量各自报告 Hedges \(g_z=J(K-1)\,\Delta X_l/s_{d_X}\)（\(J(m)=1-\frac{3}{4m-1}\)）与配对 CI；**不合成标量**。出处 `research/reference/delta-B-and-penetrance.md`。

## 13. 参数形状与初始化总表（定稿）

| 参数 | 形状 / 取值 | 初始化 / 校准 | 依据或状态 |
|---|---|---|---|
| \(W_g\) | \(\mathbb R^{8\times8}\) | Glorot/Xavier → 谱半径 \(\rho=0.9\) | `[bib#126]`；稳定性启发式 `[bib#127]` |
| \(B\) | \(\mathbb R^{8\times8}\) | \(\mathcal N(0,(1/\sqrt8)^2)\) | 设计选择 |
| \(P\) | \(\mathbb R^{8\times2}\) | \(\mathcal N(0,(1/\sqrt8)^2)\) | \(\mathbf p_i\) 原样输入（不 embedding） |
| \(\mathbf b\) | \(\mathbb R^8\) | \(\mathcal N(0,0.1^2)\) | 设计选择 |
| \(U\) | \(\mathbb R^{6\times8}\) | \(\mathcal N(0,(1/\sqrt8)^2)\) | 设计选择 |
| \(\mathbf c_{domain}\) | \(\mathbb R^6\) | one-hot，本域 \(+1.5\) | 保证六谱系 competence |
| \(\mathbf w_d,b_d\) | \(\mathbb R^8,\mathbb R\) | \(\mathcal N(0,(1/\sqrt8)^2),\,0\) | 分裂率约 0.5 |
| \(C\) | \(\mathbb R^{6\times6}\) | §9 固定 prior | 人工 prior |
| \(\lambda\) | \(2.0\) | 单位方域归一 | 设计选择（量纲随坐标归一） |
| \(\gamma\) | \(1.0\) | 固定（敏感性 {0.5,1,2}） | 弱偏置 `[bib#111]` |
| \(b_A\) | 标量 | 二分反解到 density 0.15 | §8 校准流程 |
| \(\mathbf u,b_w\) | \(\mathbb R^{28},\mathbb R\) | \(\mathcal N(0,(1/\sqrt{28})^2),\,b_w=\mathrm{softplus}^{-1}(0.5)\) | 设计选择 |
| \(\mathbf a,b_\tau\) | \(\mathbb R^8,\mathbb R\) | \(\mathcal N(0,(1/\sqrt8)^2),\,0\) | 设计选择 |
| \(\epsilon_p\) | \(\mathcal N(0,0.05^2)\) | — | 设计选择 |
| \(\epsilon_g\) | \(\mathcal N(0,0.1^2)\) | — | 设计选择 |
| motif 长度 / 窗口 / \(K\) | 6 bp / 6 bp / 3 | — | 审计 R5；\(K\) 为设计选择 |

## 阅读问题（待确认）

> 逐份阅读本文时发现的未定义点；§2–§8、§10–§11 各项已随本文件定稿（见 §13 总表）。

（无遗留：
- G2 left/right 标记归 `connectome/DanioNet设计规范.md` §5、G3 动作合成 \(y_\omega,y_v\) 归其 §4；§7 developmental viability 只**引用**该标记，属**范围外**，待 DanioNet 冻结时闭合。
- \(\theta_N,\theta_H=0.25\)（genome §3，约定值，非标定量）；本文件 §7 只引用其规则。
- bp 口径（已定）：haploid \(=2\times128=256\) bp，motif 窗口逐染色体、不跨界，见 §2。）
