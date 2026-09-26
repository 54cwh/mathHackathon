# 归属与形状契约调研：TF-motif→表达 归属 / ΔW 形状与 dtype / 状态向量 dtype

> 对应机器可读文件：`research/reference/module-ownership-and-shapes.json`
> 搜索时间：2026-09-26 ｜ 范围：公开可核实来源（OpenAlex / 同行评审论文 / 官方工程文档）
> 本文件只做调研与建议，不改动 `research/reference/` 以外任何文件，不登记 `bibliography.md`。

---

## 问题 1（归属）：TF-motif → gene expression 映射算哪一层？

### 推荐（可写进文档）

**唯一 owner 采用 `genome` 层**（`src/evogenesis/genome/生物学与进化遗传学基础.md` §6）。具体条款：

> motif 目录、匹配算子 `a(M_k,s)=1−d_H(M_k,s)/|M_k|`、整序列聚合 `q_k(S)=TopKMean_s a(M_k,s)`、单倍型向量 `q^(h)∈[0,1]^8` 与合并后的 `q(G)∈[0,1]^8`，全部归 `genome` 层定义与拥有。
> `development/RGCD数学模型.md` §2 改为对上述定义的**单向引用**（只消费、不再重复定义），RGCD 保留 §4 `B q(G)` 的消费与下游发育产物 `(A,Z,τ,W⁰,M)` 的 owner。

### 理由

1. **按项目业已声明的产出关系**：genome 文档 §6 已把 `q(G)` 列为其**产出**；AGENTS 规定「产出方 owns」。owner 重叠的根因是 RGCD §2 复制了一份算子的定义，而非 genome 不该拥有。
2. **按函数依赖结构**：`q(G)` 只依赖基因序列 `G` 与固定 motif 目录，**不依赖发育步数、网络状态或历史**。与之相对，凡「表达依赖其他基因产物」的情况才属网络内部动力学（对照 Crombach & Hogeweg 2008）。
3. **文献惯例**：motif/PWM 扫描被规范地定位为**序列层步骤**——PWM/PSSM 表示与位点预测（Stormo 2000）、promoter analysis 是「识别调控网络的前置步骤」（Cartharius et al. 2005）；热力学 cis-regulation 把「位点亲和力 → 表达率」当作 **cis-regulatory input function**（Bintu et al. 2005；Sherman & Cohen 2012），先于网络动力学。
4. **A-life 类比**：smooth binding 模型明确把「site–product 匹配质量 → 绑定概率」建模为基因组调控区的读出函数，再进入网络（Knabe et al. 2008）；Cussat-Blanc et al. 2019 综述把 GRN 定位为「DNA 中的基因型信息」与「表型」之间的中介，即表达读出在 genotype 侧、网络动力学在其后。

### 证据等级

**中。** 同行评审依据充分（Stormo 2000、Bintu 2005、Sherman & Cohen 2012、Cartharius 2005、Knabe 2008、Cussat-Blanc 2019）；但**没有任何文献直接规定「命名为 genome 层」这一模块边界**。A-life ARN（Reil 1999、Banzhaf 2003、Kuo 2006）原文均为 closed access，本次未逐字核对其匹配方程，且这些模型普遍把 genome 与 network 合为一体。因此该 owner 判定是**有据的工程裁决**，不是文献共识。

### 风险

- **改 owner 触达冻结文档**：genome §6 与 RGCD §2 均为 v1.0 已定稿，重构 owner 须用户许可、由文档侧执行；本调研只给建议。
- **motif 目录归属连带变动**：目录现由 `Θ_D`（RGCD 参数）注入。若 owner 移入 genome，须同步决定目录是「genome 层固定只读参数」还是「跨层共享只读输入」，并登记参数总表——否则会出现第二处隐式 owner。
- **措辞风险**：不得把 `a=1−d_H/|M_k|` 当作真实 PWM 生物学结论（RGCD §2 已要求声明为简化并配 PWM 对照）。

---

## 问题 2（定义完备性）：`ΔW` 的形状与 dtype

### 推荐（可写进契约的一句话）

> `ΔW` 是定义在 `W⁰` 支撑（support，由发展期邻接 `A` 给定，训练期冻结）之上的 `N×N` 张量，支撑外恒为 0：`ΔW = M ⊙ Δ`，`M = A`（对角线 0）；dtype 统一 `float32`；Dale 约束下被优化的是同形状、同 dtype 的无约束参数 `θ`（支撑外梯度屏蔽），有效权重 `w = sign(w⁰) ⊙ softplus(θ)`，`sign(w⁰)` 由突触前类型固定、训练期不变。形状在 batch 内以 padding 补齐到 48 时，padding 行列同时从 loss / 梯度 / 更新中排除。

### 理由

1. **固定支撑训练的范式**：LTH 在固定稀疏子网络（固定 mask）上用原始初始化独立训练，只更新存活连接（Frankle & Carbin 2019）——正对应本项目「只改现有连接幅度、不新增连接」。
2. **工程惯例明确 mask 与权重同形状**：PyTorch 官方 pruning 惯例中 `weight_mask` 与 weight 同为 buffer 且同形状，前向 `weight = weight_mask * weight_orig`，`weight_orig` 保持稠密同形状（PyTorch Pruning Tutorial）。
3. **一般形式**：`W = M ⊙ W`、固定 mask vs 动态改 mask 的分类见 Hoefler et al. 2021。
4. **梯度语义**：mask 的意义是只把梯度提供给 masked-in 子集（PyTorch MaskedTensor Overview），而非「置零后照常更新」。
5. **dtype 选 float32**：与问题 3 的全局约定一致；权重参数以 float32 承载更新是混合精度训练的标准（Micikevicius et al. 2018）。

### 证据等级

**中高。** 工程惯例清晰（PyTorch 官方文档）、固定支撑范式有同行评审来源（LTH）；但「具体写成 `(N,N)` + `float32`」是**综合惯例**，没有单篇同行评审直接对本项目给出该契约。

### 风险

- **必须写 frozen support**：文献中 dynamic sparse training / drop-and-grow 允许改变 mask，与本项目不同。只写「masked update」不写「mask 冻结」，会被误读为可长出新连接。
- **Dale sign 与优化变量**：若按 `w ← w − lr·∂L/∂w` 直接更新会破坏符号约束；必须优化 `θ`。这一点当前 DanioNet §3/§6 未写清，是契约缺口。
- **padding 泄漏**：padding 到 48 的行列若未从 loss/梯度/更新中屏蔽，会污染学习。需与 §3 的 neuron mask / adjacency mask 约定对齐。
- **`M` 的取值**：推荐 `M = A`（支撑即发展期邻接），而非另学一个 mask；若用 `A`，须说明 `A` 在 lifetime learning 期间不变。

---

## 问题 3（定义完备性）：状态向量的 dtype 约定

### 推荐（可写进文档的全局约定）

> 模型张量（状态 `h`、权重 `W⁰/ΔW/θ`、输入 `U/m/b`、RGCD 参数）与训练梯度统一 `torch.float32`。
> - 禁止全局 `torch.set_default_dtype(torch.float64)`；
> - 跨框架边界强制显式转换：NumPy 默认 `float64`，`torch.from_numpy` / `torch.tensor(np_float64_array)` 会得到 `float64`，必须 `.to(torch.float32)` 或 `np.asarray(..., dtype=np.float32)`；
> - CPU/GPU 混用不承诺 bitwise 一致：数值比较只用容差（`torch.allclose(..., rtol, atol)`）与统计指标，报告须注明设备；
> - 若未来启用 AMP，保留 float32 master weights，仅前向/矩阵乘降精度。

### 理由

1. **框架默认即 float32**（`torch.set_default_dtype`）；改默认会波及所有依赖框架默认的构造路径。
2. **隐式提升的具体机制**（`Tensor Attributes`）：混合 dtype 的算术按「最小满足 dtype」提升；与 NumPy 不同，PyTorch 不检查标量数值，浮点标量算子的 dtype 取默认 dtype。因此**标量一般安全，混入 float64 张量则整条运算被提升**。
3. **NumPy 默认 float64**（`Array creation`），与本项目后端默认相反，是异构 dtype 风险的主要来源；提升路径还分「按值」（保持 float32）与「按类型」（得 float64）两条（`Data type promotion`）。
4. **CPU/GPU 不 bitwise 一致**：浮点加法不满足结合律，PyTorch 明确不保证数学等价计算 bitwise 相同，CPU 与 GPU 结果可不同（`Numerical accuracy`、`Reproducibility`）。固定种子保证同机可复现，但不保证跨设备一致。
5. **float64 代价高**：GPU 硬件对 FP64 优化有限，社区实测消费级/部分专业卡上 float64 矩阵乘比 float32 慢数十倍（A6000 约 40–50×，非同行评审）。
6. **fp32 master weights 是权威惯例**（Micikevicius et al. 2018）。

### 证据等级

**高。** 四条 PyTorch 官方文档 + 两条 NumPy 官方文档 + 一篇同行评审（ICLR 2018）直接支撑；仅「float64 慢多少倍」的量化属社区数据。

### 风险

- **float32 在长时/混沌 rollout 累积误差**；但本项目 episode 短，且 float64 在 GPU 代价过高。
- **建议做一次性精度对照**：同 seed 下短 episode 的 CPU float64 vs float32，比较 `(ω,v)`/fitness 差异是否在容差内并记录；若显著再考虑**选择性** float64（如仅 RGCD 谱半径校准），而非全局切换。
- **TF32 静默降精度**：Ampere+ 上 matmul 可能默认走 TF32；若需跨机一致，须显式设 `torch.set_float32_matmul_precision` 与 `torch.use_deterministic_algorithms`。

---

## 结论分级与未找到项（同步自 JSON）

- **推荐直接用**：Q3 全局 float32 约定；Q2 `ΔW` 形状 = `N×N` 掩码内增量；Q1 `q(G)` 归 genome 层。
- **仅作参考**：Hoefler et al. 2021（预印本，未核正式出处）；PyTorch 社区 float64 性能数据（非同行评审，仅数量级）。
- **不建议**：把 `ΔW` 定义为会改 mask 的动态稀疏训练；全局切 float64；未声明简化即把退化 PWM 当生物学结论。

未找到项（详见 JSON `meta.missing`）：无同行评审文献把 motif 扫描明确指派给「genome 层」这一命名边界；Reil 1999 / Banzhaf 2003 / Kuo 2006 全文 closed access，未逐字核对匹配方程；Cussat-Blanc 2019 全文抓取失败；无权威来源量化 float64-on-GPU 倍率；Dettmers & Zettlemoyer 2019 元数据本次未取得（未引用）；arXiv MCP 返回 HTTP 406。
