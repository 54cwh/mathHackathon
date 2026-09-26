# RGCD 数学模型规范

> **管辖范围**：RGCD 全部算法与发育产物 `(A,Z,τ,W⁰,M)`、cell type 产出、viability 判据。（层级与归属见 `AGENTS.md`「文档层级与优先级」。）
> 状态：**v1.8 已定稿（冻结 2026-09-26）**。范围外：G2 left/right 标记（`DanioNet §5`）、G3 动作合成（`DanioNet §4`）；\(\theta_N,\theta_H=0.25\) 已定稿（`genome §3`；`docs/参数总表.json` confirmed）。

## 1. 输入输出

**输入**

| 记号 | 类型 / 形状 | 定义 | 来源 |
|---|---|---|---|
| \(\mathbf q(G)\) | NumPy `float32`，形状 \((8,)\)，值域 \([0,1]\) | genome 派生量（genome §6；\(G\) 本身不进入本模块）。位点表达 \(E_A,E_B\)（genome §3）属**报告层**读出（penetrance 用），**不是本模块输入** | `genome` |
| \(\Theta_D\) | §13 参数集合（各张量形状见表） | 发育参数（\(W_g,B,P,\mathbf b,U,\mathbf c_{domain},\mathbf w_d,b_d,C,\lambda,\gamma,b_A,\mathbf u,b_w,\mathbf a,b_\tau,\epsilon_p,\epsilon_g\)），由 seed 确定性初始化 | §13 / §2 |
| \(\xi\) | RNG 流（命名空间 `development`） | 发育随机源（分裂 Bernoulli、\(\epsilon_p,\epsilon_g\)）；由 `core` seed manager 派生，**不另立随机源** | `core §3` |

**跨框架转换（定稿）**：`genome` 侧的 \(\mathbf q(G)\) 为 NumPy `float32`；本模块入口 `develop(q, ...)` 接受 NumPy 数组并在边界经 `core/tensors.py::to_float32_tensor` 转为 `torch.float32`，**模块内部只持有 torch 张量**（`core §7`）。\(E_A,E_B\) 不在本模块边界内（报告层读出，见上）。

**输出**（active \(N\in[24,48]\)；batch 内 padding 到 48 的约定见 `DanioNet §3`）

产出为运行期对象 `ConnectomePhenotype`（本节点为 **owner**；`connectome` / `pipeline` 只引用字段、不改名）。各字段的数学记号 / 运行期字段名 / 形状 / dtype / 值域如下：

| 记号 | 运行期字段 | 形状 | dtype | 值域 / 含义 |
|---|---|---|---|---|
| \(A\) | `adjacency` | \((N,N)\) | `float32`（0/1） | 二值邻接；无 self-loop；density ∈ [0.10,0.20] |
| \(Z\) | `z` | \((N,6)\) | `float32` | \([0,1]\)，\(z_i=\mathrm{softmax}(l_i)\)（§6） |
| \(\tau\) | `tau` | \((N,)\) | `float32` | \([1,10]\)（§11） |
| \(W^{(0)}\) | `weights0` | \((N,N)\) | `float32` | 初始有效权重，符号由突触前类型定（§10） |
| \(M\) | `active_mask` | \((N,)\) | `bool` | active neuron mask（padding 位为 `False`） |
| — | `cell_type` | \((N,)\) | `int64` | \(z_i\) 的 argmax（六类 fate，§6） |
| — | `positions` | \((N,2)\) | `float32` | 神经元在发育空间的位置（`DanioNet §5` 取用） |
| — | `viable` | 标量 | `bool` | 是否通过 §7 全部 viability 判据 |
| — | `viability_reason` | `str` | — | 判因词表见 §7；viable 时为 `"ok"` |

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

**放置（定稿）**：24 个 precursor 在六个 domain 间**均匀分配**（每域 4 个）。位置取 **domain-blocked 均匀随机**：把归一化发育单位方域 \([0,1]^2\) 划为 \(3\times2=6\) 个 block（尺寸 \(1/3\times1/2\)），block 网格为 **2 行 \(\times\) 3 列**（x 方向 3 列、步长 \(1/3\)；y 方向 2 行、步长 \(1/2\)），domain 按 \([S,P,T,M,I,O]\) 顺序**行优先**填入；每个 precursor

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

报告、代码、可视化均使用这一式。**初始态（定稿）**：\(\mathbf g_i^{0}=\mathbf 0\)（echo-state 惯例；与 §7 零输入动力学的 \(h^0=\mathbf 0\) 一致）。

**形状（定稿）**：\(\mathbf g_i\in\mathbb R^8\)（`grn.dim=8`）、\(\mathbf q(G)\in\mathbb R^8\)、\(\mathbf p_i\in\mathbb R^2\) 原样输入（不做 embedding）；\(W_g\in\mathbb R^{8\times8}\)、\(B\in\mathbb R^{8\times8}\)、\(P\in\mathbb R^{8\times2}\)、\(\mathbf b\in\mathbb R^8\)。

**初始化（定稿）**：\(W_g\) 取 **Xavier uniform**（Glorot & Bengio 2010，`[bib#126]`）后重标定谱半径 \(\rho_{\mathrm{spec}}(W_g)=0.9\)；\(B,P\sim\mathcal N(0,(1/\sqrt8)^2)\)；\(\mathbf b\sim\mathcal N(0,0.1^2)\)。全部由 seed manager 派生。

依据与限定："谱半径 \(<1\Rightarrow\) echo-state property"是**经验条件**（Yildiz et al. 2012 `[bib#127]` 给出反例），故按稳定性启发式使用、并记录 \(\rho_{\mathrm{spec}}(W_g)\)；未找到阻尼 sigmoid GRN 的专属初始化惯例，其余尺度为**设计选择**。

> **实现注记（`W_g` 存储为转置）**：上式按 \(W_g\mathbf g\)；代码 `grn.py` 以列向量右乘存储等价形式（`einsum("...nd,de->...ne")`，即 \(W_g^{\top}\mathbf g\)）。因 \(W_g\) 随机初始化且谱半径对转置不变，两者分布等价；\(W_g\) 仅在 §4 内部使用、不出现在输出契约中。

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

**§5 扩展：分裂读数的两个设计增益（2026-09-26）**

读数可加两个**默认关闭**的设计增益 \(\alpha\)（`development.division_drive_gain`）与
\(\beta\)（`development.division_locus_gain`）；关闭时（\(\alpha=1,\beta=0\)）与上式**逐位一致**：

\[
p_i^{divide}=\sigma\!\left(\alpha\left(\mathbf w_d^T\mathbf g_i^{12}+b_d-\overline{\mathbf w_d^T\mathbf g^{12}}\right)+\beta\,c_i\right),
\qquad
c_i=\overline{q_A^{(i)}}-\overline{q^{(i)}}
\]

其中横线在**该个体**的 24 个 precursor 上取均值；\(c_i\) 为**基因组通道** = A 位点 motif 亲和均值 −
全 motif 亲和均值，索引的单一来源是 `genome.motif_subset_A`（不另立常数）。**逐个体中心化是先决条件**：
\(\mathbf g\in[0,1]^8\) 若原样相加等于给全体前体一个正偏置 ⇒ sigmoid 整体饱和 ⇒ \(N\equiv48\)、区分力归零。

**两条已实测结论（关键）**

1. **\(\beta\) 是单位规范（gauge），不是校准值，也不可校准。** 下游读数经**秩统计量**（AUC、外显率阈分类）
   读取，而秩统计量对 \(\beta>0\) 的任何单调尺度**不变**。实测 \(\alpha\in[0.5,16]\times\beta\in[0.05,2]\)
   的**全平面同值**（AUC / 两档间隙 / 外显率皆不变）⇒ 取 1.0 与取 0.05 等价。
2. **\(\alpha\) 在线性区一阶惰性。** 逐个体中心化使 \(\sum_i(\mathbf w_d^T\mathbf g_i^{12}-\overline{\cdot})=0\)，
   故线性区该通道对 \(\sum_i p_i\) 的一阶贡献**恒为 0**；仅当 \(\alpha\,\sigma_u\gtrsim0.3\) 才起作用，
   而该区已进入饱和。实测 \(\alpha\in[0.5,16]\) 对秩统计量无影响。

**机制价值与边界**：\(\beta\) 由 0 翻 1.0 后 N 轴由 `separable=false` 转为 `separable=true`（官方校准集实测
AUC 0.4775 → 0.6284、\(p=3.4\times10^{-19}\)、min-misclassification 0.500 → 0.408、
\(\theta_N^{obs}\) 由退化贴顶转为区间内部 35.5 / 36.5）。但该改动会改动 3 处**已冻结锚**
（含论文 `02-method.tex` 的 \(N\) 中位 36.5 / 195 边 / 0.149）并须重跑 Exp C/D/E/F；且 §7 判据无
**效应下限**（AUC 0.628 属弱效应）⇒ **翻默认待用户裁决**，当前出货默认仍 \(\alpha=1,\beta=0\)（= 原式）。
依据见 `research/notes/契约决策记录.md` 2026-09-26 条目。

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

**参数与初始化（定稿）**：\(U\in\mathbb R^{6\times8}\)、\(\mathbf c_{domain}\in\mathbb R^6\)（实现存为 \(6\times6\) 的 \(1.5\cdot I\)，按域取行）；\(U\sim\mathcal N(0,(1/\sqrt8)^2)\)；\(\mathbf c_{domain}\) 为 one-hot（本域位 \(+1.5\)，余为 0），给六个基础谱系 developmental competence。

**跨域散布收口（定稿，2026-09-26）**：\(U\) 抽样后按**解析上界确定性收紧**其中心化部分的跨域散布——取 \(\tilde U=U-\bar U\)，若 \(\max_{j,k}\|\tilde U_j-\tilde U_k\|_2>c_{\mathrm{domain}}/\sqrt8\) 则按该比值线性缩小（逐行均值不变、**只收紧不放大**、不吃随机数）。理由：§7 的 \(missing_fate\) 要求「域 k 至少一个细胞」，而 §6 的 \(\argmax\) 允许改判；改判的充要条件是 \(\max_{j\ne k}\,g\cdot(U_j-U_k)\ge c_{domain}\)。又 \(g\) 是 sigmoid 输出的凸组合（§4）、逐分量严格落在 \((0,1)\)，故 \(\|g\|_2<\sqrt8\) 对一切可达 \(g\) 成立，于是上述上界是「改判永不发生」的**解析充分条件**（同 §7 判据 (ii) 的解析保证性质）。实测：收口前 20 个 seed 中 **5 个（25%）**使某域被整种子系统性改判（该 seed 下 33%–67% 个体 \(missing_fate\) 不可育）；收口后 **20/20 seed 全部 120/120 可育**。**代价（明示）**：默认配置下 \(\argmax\,z\) 恒等于谱系域，\(missing_fate\) 不再触发；该 token 仍保留在 §7 判因词表（非默认配置或更大的 \(U\) 仍需它上报）。

**owner**：`type_i` 如何由 GRN **产出**（本式）归本文件；六类**功能语义**与 left/right motor 标记归 `connectome/DanioNet设计规范.md` §1/§5。`argmax` 为离散化理想化（真实 fate 为连续谱 `[bib#75]`），建议同时记录 `z_i` 分布/熵。

## 7. Viability
所有判据在 **active subset**（`M` 为真者）上计算：非活跃神经元不参与 fate 计数/路径/动力学判定（与 `DanioNet §3` 的最终复核口径一致）。
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
- (ii) \(|h_i^t|<1\) 对所有 \(i,t\) 成立（**解析保证**：更新是 \(h_i^t\) 与 \(\tanh(\cdot)\in(-1,1)\) 的凸组合，权重 \((1-1/\tau_i),\,1/\tau_i\ge0\) 且和为 1，由 \(h^0=0\) 归纳即得——非工程阈值。**float32 下 \(\tanh\) 饱和可恰取 \(1.0\)，实现按 \(|h|\le1\) 判定，属舍入而非动力学发散**）；
- (iii) 不永久全饱和：尾 10 步（\(t=40..49\)）平均饱和比例 \(<0.9\)，饱和定义为 \(|h_i^t|>1-10^{-3}\)；
- (iv) \(\rho_{\mathrm{spec}}(W^{(0)})<1\)（有效权重矩阵的 tanh 稳定性启发式，`[bib#127]`；注意对象是 **connectome 权重 \(W^{(0)}\)**，非 §4 的 GRN 矩阵 \(W_g\)）。

(iii)(iv) 为**工程判据**（设计选择）；(ii) 是模型的数学性质，报告可直接引用。

**判因词表（owner：本节点；运行期字段 `ConnectomePhenotype.viability_reason`）**：多因以 `;` 连接；通过全部判据时为 `"ok"`。

| token | 触发判据 | 下游消费 |
|---|---|---|
| `no_active_neurons` | active mask \(M\) 无任何 true（\(\sum M=0\)，无神经元可评） | `evolution` 记 `failure_reason`；`make_fig_viability` |
| `missing_fate:<六类之一>`（多类逗号分隔） | Developmental viability：某基础 fate \(N_k<1\) | `evolution` 记 `failure_reason`；`make_fig_viability` |
| `motor_side_empty` | Developmental viability：motor 无 left/right 关联输出神经元 | 同上 |
| `no_sensory_to_motor_path` | Functional viability：无 \(Sensory\rightsquigarrow Motor\) 有向路径 | 同上 |
| `nonfinite_activation` | Dynamical (i)：出现 NaN/Inf | 同上 |
| `activation_bound_violated` | Dynamical (ii)：\(|h_i^t|>1\)（float32 舍入容差内） | 同上 |
| `persistent_saturation` | Dynamical (iii)：尾 10 步平均饱和比例 ≥0.9 | 同上 |
| `weight_spectral_radius_not_contractive` | Dynamical (iv)：\(\rho_{\mathrm{spec}}(W^{(0)})\ge1\) | 同上 |
| `ok` | 全部通过 | viable=True |

**实测工作点（2026-09-26 复核，可复现）**：在**随机 \(q\sim U[0,1]^8\) 下（\(q\) 直抽、非 \(q(G)\)），
seed 1103 / 2207 / 42 各跑 1000 次发育：**通过率 1000/1000 = 100.000%**
（Wilson 95% 区间 [99.6%, 100.0%]）—— **八条判据一条也没有触发**。

> **⚠️ 本节旧版数字作废**（旧版：通过率 7.1%、判据 (iv) 占 89.8%、\(missing_fate\) 4.3%–6.9%）。成因是两处
> Θ_D 校准失配，均已修复，见下。

两处失配与修法：

1. **判据 (iv) 的对象 \(W^{(0)}\) 未按项目自身惯例重定谱半径**。旧版 89.8% 的尝试因 \(\rho\ge1\) 被拒、
   活跃子矩阵 \(\rho\) 中位数 1.63\)，而 §10 的 \(\bar w=0.5\) 在默认密度下天然给出 \(\rho\approx2.7\)——
   即该判据从未按「设计工作点」校准。修法：仿 §4 对 \(W_g\) 的做法，把 \(W^{(0)}\) 的谱半径**确定性重定**
   到 `connectome.rho_w0_target`（默认 0.9）。§7 自述 (iii)(iv) 为**工程判据（设计选择）**，故以确定性重定
   取代自由抽样属口径内修法。
2. **\(missing_fate\) 是「每-seed 抽签型门禁」**。Θ_D 改为每 seed 一套（§1/§13）后，\(U\) 的跨域散布变成
   每 seed 一次的自由抽签：实测 20 个 seed 中 5 个（25%）使某域被整种子系统性改判。修法见 §6「跨域散布收口」。

**⚠️ 由此产生的口径后果（写入报告时必须一并给出）**：默认配置下 (i)(ii)(iii)(iv) 与 \(missing_fate\) 全部成为
**松弛判据**，§7 的发育期 viability 筛选在当前默认配置下**不再淘汰任何个体**。因此

- `paper/报告-骨架.md` §2.1 的 **F6 / 「2/14」已失效**（现为 14/14）。报告面数字须由 paper lane 重算，
  **不得**由本次修复自行改写；调和的正确方向仍是「小样本读法」（n=14 的 Wilson 区间 [78.5%, 100.0%]）。
- \(n\_{\mathrm{danio}}\) 口径下 viable 数由约 10% 变为约 100%：`evolution` 的 `failure_reason` 分支
  在当前默认配置下不再产生样本。
- 此后 §7 的筛选功能只在下游 DanioNet 复核（\(b_{type_i}\)，见下）与非默认配置下生效。若需要保留一个
  **有约束力**的发育期筛选，须重新标定默认配置（属 `configs/` owner 的取值决策 + `docs/参数总表.json`
  的依据同步），**不在**本次修复范围内。

复现：`python scripts/make_fig_viability.py`（图为 `paper/报告-骨架.md` 的 F6），
底层数据见 `results/figs/dev_viability/data/fig_viability.xlsx` 的 `_manifest`。

复现：`python scripts/make_fig_viability.py`（图为 `paper/报告-骨架.md` 的 F6），
底层数据见 `results/figs/dev_viability/data/fig_viability.xlsx` 的 `_manifest`。

**\(b_i\) 的处理（定稿）**：零输入更新式含 per-neuron bias \(b_i\)，其 owner 为 `connectome/DanioNet设计规范.md` §3（\(b_i=b_{type_i}\)，seed 初始化；RGCD 输出契约 \((A,Z,\tau,W^{(0)},M)\) 不含它）。故本节动力学检查**接受调用方传入的 \(b_i\)**；发育阶段默认 \(b_i=0\)（**无偏置近似**），最终 viability 由 DanioNet 用其 \(b_{type_i}\) 复核。

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

**轨迹外露（2026-09-27；`API接口.md` §2.3）**：`connectome` 阶段的 trace 采样点额外给出
`probs`，即上式 \(P(A_{ij}=1)\) 的**模型真值矩阵**（\(N\times N\)，行主序，`float32`，
值域 \([0,1]\)；`allow_self_loops=False` 时对角线为 0）。前端据此把连接组画成**两幕真值**：
先 \(p\)（概率场），再 \(A\)（一次采样得到的邻接）。两幕都是模型真值，**不逐步长边**。

依据：空间布线代价项 \(-\lambda d_{ij}\) 有充分文献支撑——在 logit 中加入线性距离项等价于指数距离规则 \(P\propto e^{-\lambda d}\)（Ercsey-Ravasz et al. 2013 *Neuron*；Waxman 1988；Kaiser & Hilgetag 2004；综述 Bullmore & Sporns 2012）；cell-type 兼容项 \(z_i^T C z_j\) 对应 `[bib#4]`。注意 \(\lambda\) 有量纲，本项目在**归一化发育单位方域**上取值（见下），不照搬文献的 mm 口径值。出处：`research/reference/design-basis-connectome.md`。

**\(\gamma R(\cdot)\) 形式（定稿）**：取**逐分量标准化后的双线性（弱偏置）**。令 \(\bar g,\hat\sigma\) 为本代 \(N\) 个神经元在各分量上的均值与**总体标准差（ddof=0）**，\(\hat{\mathbf g}_i=(\mathbf g_i-\bar g)\oslash\hat\sigma\)（**若某分量 \(\hat\sigma_k=0\)，该分量取 \(\hat g_{ik}=0\)，即该项贡献 0**），则

\[
R_{ij}=\frac{1}{8}\sum_{k=1}^{8}\hat g_{ik}\hat g_{jk},\qquad K=I\ (\text{零参数}).
\]

\(R_{ij}\) 为标准化内积，**不声明其落在 \([-1,1]\)**（对角线亦不为 1：标准化用的是本代种群矩）；其量级由 \(b_A\) 的二分校准吸收。

中心化**只用于 \(R\) 项**，§4 的 \(\mathbf g\) 语义不变。依据：转录组/细胞类型相似度预测连线的双线性模型（Qiao et al. 2024 *eLife* `[bib#111]`；Kovács et al. 2020 *PNAS* `[bib#112]`；识别分子为异源、\(K\) 可非对角但 \(I\) 为可解释 MVP，Sanes & Zipursky 2020 `[bib#119]`）。**限定**：单用表达相似度预测连线的证据仅 AUC≈0.64（`[bib#111]`；Hayashi et al. 2022 反 Hebbian `[bib#121]`），故 \(R\) 按**弱偏置**使用并须报 \(\gamma=0\) 消融。

**系数（定稿）**：\(\gamma=1.0\) 固定（属 \(\Theta_D\)，不演化；敏感性搜索 \(\{0.5,1,2\}\)）；\(\lambda=2.0\)（单位方域，\(E[d]\approx0.521\Rightarrow\lambda d\approx1.04\)，与 \(z_i^\top Cz_j\in[-2,2]\) 配平）。\(b_A\) 用**二分反解**使**期望** off-diagonal density \(=0.15\)（实测密度由 Bernoulli 抽样波动，落在 \([0.10,0.20]\)，由 `tests/test_rgcd.py` 守护）。下式为**一阶近似**，仅用于解释 \(b_A\) 的量级；因 \(E[\sigma(\ell)]\neq\sigma(E[\ell])\)，实现**以二分反解为准**：

\[
b_A\approx\mathrm{logit}(p_{target})-E[z_i^\top Cz_j]+\lambda E[d]-\gamma E[R].
\]

\(\gamma,\lambda,b_A\) 均为项目标定/设计选择（\(\lambda\) 的量纲由单位方域归一化定义）。出处：`research/reference/rgcd-wiring-and-placement.md`。

> **实现注记（`b_A` 反解收敛口径）**：§8 的 `b_A` 由 `solve_bias_for_density` 二分反解，取容差 `tol=1e-8`、最大迭代 `200`、初始界 `±60`（`rgcd.py`）；这些是数值求解细节，不改 §8 的语义（目标密度区间 [0.10,0.20]）。

**消融（w/o GRN，`connectome §9`）**：当 `connectome.ablation_w_grn = true` 时，§8 的连线概率不再由 GRN/几何决定，改为**独立同分布**抽样

\[
A_{ij}\sim\mathrm{Bernoulli}(p)\ (i\neq j),\qquad A_{ii}=0\ (\text{禁 self-loop}),
\]

其中 \(p\) = `connectome.ablation_random_density`（默认 0.15）。神经元数 \(N\)、\(\tau_i\)、\(|w^{(0)}_{ij}|\) 幅度、Dale 符号与 §7 viability 判据**全部保持**，故该臂只隔离「GRN 布线」变量（同密度、同尺度）。默认 `false`，不改变既有行为。

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

**谱半径重定（定稿，2026-09-26）**：\(W^{(0)}\) 按上式与 Dale 符号抽样后，再以其谱半径 \(\rho_{\mathrm{spec}}\) 确定性
重定为 `connectome.rho_w0_target`（默认 0.9）：做法与 §4 对 \(W_g\) 的谱半径重定一致（正标量缩放，不改支撑、不改
Dale 符号，不吃随机数）。修因与口径后果见 §7「实测工作点」。

## 11. Time constant
\[
\tau_i
=
\tau_{\min}
+
(\tau_{\max}-\tau_{\min})\cdot
\sigma(
\mathbf a^T\mathbf g_i+b_\tau
)
\]

其中 \(\tau_{\min}=1,\ \tau_{\max}=10\) 取自 `configs/default_model.yaml → connectome.tau_min/tau_max`（`core §7`：数值以 config 为准）。所以：

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

> **参数分层（定稿）**：\(\Theta_D\) 中 \(b_A\) **不是** seed 初始化张量——它由 §8 的 `solve_bias_for_density` 按目标密度**确定性反解**（不消耗随机数）；\(\epsilon_p,\epsilon_g\) 是 §2/§4 的噪声**尺度**，取 `config` 的 `split_noise` / `gene_noise`，由 `development` 命名空间随机流产生实际噪声。其余张量按本表由 seed 初始化。

## 13. 参数形状与初始化总表（定稿）

| 参数 | 形状 / 取值 | 初始化 / 校准 | 依据或状态 |
|---|---|---|---|
| \(W_g\) | \(\mathbb R^{8\times8}\) | Xavier uniform → 谱半径 \(\rho=0.9\) | `[bib#126]`；稳定性启发式 `[bib#127]` |
| \(B\) | \(\mathbb R^{8\times8}\) | \(\mathcal N(0,(1/\sqrt8)^2)\) | 设计选择 |
| \(P\) | \(\mathbb R^{8\times2}\) | \(\mathcal N(0,(1/\sqrt8)^2)\) | \(\mathbf p_i\) 原样输入（不 embedding） |
| \(\mathbf b\) | \(\mathbb R^8\) | \(\mathcal N(0,0.1^2)\) | 设计选择 |
| \(U\) | \(\mathbb R^{6\times8}\) | \(\mathcal N(0,(1/\sqrt8)^2)\) 抽样后按 §6 收口：中心化跨域散布 \(\le c_{\mathrm{domain}}/\sqrt8\) | 设计选择；收口见 §6 |
| \(\mathbf c_{domain}\) | \(\mathbb R^6\)（存为 \(6\times6\) 的 \(1.5\cdot I\)） | one-hot，本域 \(+1.5\) | 保证六谱系 competence |
| \(\mathbf w_d,b_d\) | \(\mathbb R^8,\mathbb R\) | \(\mathcal N(0,(1/\sqrt8)^2),\,0\) | 分裂率约 0.5 |
| \(C\) | \(\mathbb R^{6\times6}\) | §9 固定 prior | 人工 prior |
| \(\lambda\) | \(2.0\) | 单位方域归一 | 设计选择（量纲随坐标归一） |
| \(\gamma\) | \(1.0\) | 固定（敏感性 {0.5,1,2}） | 弱偏置 `[bib#111]` |
| \(b_A\) | 标量 | 二分反解到 density 0.15 | §8 校准流程 |
| \(\mathbf u,b_w\) | \(\mathbb R^{28},\mathbb R\) | \(\mathcal N(0,(1/\sqrt{28})^2),\,b_w=\mathrm{softplus}^{-1}(0.5)\) | 设计选择 |
| \(\mathbf a,b_\tau\) | \(\mathbb R^8,\mathbb R\) | \(\mathcal N(0,(1/\sqrt8)^2),\,0\) | 设计选择 |
| \(\epsilon_p\) | \(\mathcal N(0,0.05^2)\) | — | 设计选择 |
| \(\epsilon_g\) | \(\mathcal N(0,0.1^2)\) | — | 设计选择 |
| \(\alpha,\beta\) | \(\mathbb R_{\ge0}\)（配置标量） | 默认 \(1.0,0.0\)（= 原式）；\(\beta\) 单位规范、\(\alpha\) 线性区惰性 | §5 扩展（2026-09-26）；翻 \(\beta=1.0\) 待用户裁决（`docs/参数总表.json` `changes_pending`） |
| motif 长度 / 窗口 / \(K\) | 6 bp / 6 bp / 3 | — | 审计 R5；\(K\) 为设计选择 |

## 阅读问题（待确认）

> 逐份阅读本文时发现的未定义点；§2–§8、§10–§11 各项已随本文件定稿（见 §13 总表）。

（无遗留：
- G2 left/right 标记归 `connectome/DanioNet设计规范.md` §5、G3 动作合成 \(y_\omega,y_v\) 归其 §4；§7 developmental viability 只**引用**该标记，属**范围外**，待 DanioNet 冻结时闭合。
- \(\theta_N,\theta_H=0.25\)（genome §3，约定值，非标定量）；本文件 §7 只引用其规则。
- bp 口径（已定）：haploid \(=2\times128=256\) bp，motif 窗口逐染色体、不跨界，见 §2。）
