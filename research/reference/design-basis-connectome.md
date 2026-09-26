# 设计依据：空间布线代价与神经演化基线

> 检索日期：2026-09-26　|　对应 JSON：`research/reference/design-basis-connectome.json`
> 检索范围：R3 空间布线/连接代价；R6 NEAT/HyperNEAT/ES-HyperNEAT 基线与连续二维多智能体环境尺度。
> 核实方式：OpenAlex 逐条核验 DOI/作者/引用数并抽取原文 PDF（Ercsey-Ravasz 2013）；GitHub CLI 核验仓库 star/许可证并读取 MPE2 源码。
> 引用纪律：每条附 URL/DOI 与同行评审状态；未核实或非同行评审处已标注。

---

## R3 空间布线 / 连接代价

### 核心问题

RGCD 的连接概率为

```
l_ij = z_i^T C z_j - lambda * d_ij + gamma R(...) + b_A
P(A_ij = 1) = sigma(l_ij),   d_ij = ||p_i - p_j||_2
```

问：`-lambda * d_ij` 是否有文献支撑？典型函数形式与参数是什么？

### 结论（一句话）

**有充分支撑。** 在 logit 中加入 `-lambda*d_ij`，对距离维度等价于连接概率随距离指数衰减 `P ∝ exp(-lambda*d)`；这是神经科学中距离依赖连接最强的实证规律，函数形式以指数衰减为准，典型参数为猕猴皮层 `lambda = 0.188 mm^-1`。

### 证据链

| 依据 | 出处 | 类型/评审 | 关键数值或结论 |
|---|---|---|---|
| 布线优化奠基 | Chklovskii, Schikorski & Stevens 2002, *Neuron*；DOI 10.1016/S0896-6273(02)00679-7 | peer-reviewed；引用 516 | 皮层回路布线受体积/线长最小化约束 |
| 最优布局求解 | Chen, Hall & Chklovskii 2006, *PNAS*；DOI 10.1073/pnas.0506806103 | peer-reviewed；引用 683 | C. elegans 279 神经元最优布局接近真实位置 |
| 经济性综述 | Bullmore & Sporns 2012, *Nat Rev Neurosci*；DOI 10.1038/nrn3214 | peer-reviewed 综述；引用 3472 | 拓扑效率与布线成本（wiring cost）的权衡 |
| 距离依赖生长（函数式） | Kaiser & Hilgetag 2004, *Phys Rev E* 69:036103；DOI 10.1103/PhysRevE.69.036103 | peer-reviewed；引用 204 | `P(u,v)=beta*exp(-alpha*d(u,v))`，alpha 控制长程连接 |
| 总布线长度量化 | Kaiser & Hilgetag 2006, *PLoS Comput Biol*；DOI 10.1371/journal.pcbi.0020095 | peer-reviewed gold OA；引用 667 | 重排节点可降总布线长度（最高约 64%），长距离连接换取更短路径 |
| 分布式网络原始模型 | Waxman 1988, *IEEE JSAC* 6(9):1617-1622；DOI 10.1109/49.12889 | peer-reviewed；引用 2895 | `P(u,v)=beta*exp(-d/(L*alpha))`，长程连接高成本 |
| 皮层连接组实证 | Ercsey-Ravasz et al. 2013, *Neuron* 80(1):184-197；DOI 10.1016/j.neuron.2013.07.036 | peer-reviewed；引用 561；原文 PDF 已抽取 | `p(d)=c*exp(-lambda*d)`，**lambda=0.188 mm^-1**；二值密度约 66% |
| 跨物种复现 | Horvát et al. 2016, *PLoS Biol*；DOI 10.1371/journal.pbio.1002512 | peer-reviewed gold OA；引用 241 | 指数距离规则（EDR）+皮层几何约束小鼠/猕猴网络布局 |
| 规模-连接权衡 | Ringo 1991, *Brain Behav Evol* 38(1):1-6；DOI 10.1159/000114375 | peer-reviewed；引用 389 | 脑增大时直接连接比例下降（传导延迟与体积代价） |
| 生成式建模范式 | Betzel et al. 2015, *NeuroImage*；DOI 10.1016/j.neuroimage.2015.09.041 | peer-reviewed；引用 347 | 以几何距离为自变量的生成模型解释连接组拓扑 |
| 演化基线上的连接代价 | Huizinga, Mouret & Clune 2014, *GECCO*；DOI 10.1145/2576768.2598232 | peer-reviewed conference；引用 43 | 把 connection cost 技术引入 HyperNEAT，以距离惩罚塑造模块化网络 |

### 典型函数形式

1. **指数衰减（推荐）**：`P ∝ exp(-alpha*d)`。Waxman 1988 的原始形式；Kaiser & Hilgetag 空间生长模型；Ercsey-Ravasz 2013 由猕猴数据直接拟合。
2. **Gaussian（不建议默认）**：`P ∝ exp(-d^2/(2*sigma^2))`。Kaiser 2005 技术报告明确指出，用距离的平方会给近邻相对更高概率，与指数衰减相悖。
3. **等价说明**：`sigma(z^T C z_j - lambda*d_ij + b)` 中，距离项使连接概率随 `d` 近似指数下降；故 `-lambda*d_ij` 是指数距离规则在 logit 参数化下的标准写法。

### 需要进一步验证的风险点

- **lambda 的量纲**：`0.188 mm^-1` 是猕猴脑组织距离尺度。本项目 Arena 为 100x60 的无量纲坐标，`lambda` 必须按本项目距离尺度重新标定，不能照搬。
- **密度校准**：EDR 网络二值密度很高（猕猴约 66%），而本项目目标密度仅 10%–20%；`lambda` 与 `b_A` 需联合标定才能同时满足“距离依赖”与“目标密度”。
- **长程连接并非错误**：Kaiser & Hilgetag 2006 表明长距离连接具有缩短处理路径的功能价值；惩罚项应设为概率偏置，不应硬性截断长程连接。

---

## R6 基线集合与环境尺度

### 核心问题

- 发育编码网络的合理 neuroevolution 基线有哪些？
- “参数量同一数量级”如何量化？
- 连续二维多智能体环境的尺度、episode 长度、更新频率惯例是什么？

### 结论（一句话）

**基线集合**：NEAT（变拓扑）+ HyperNEAT（CPPN 间接编码）+ ES-HyperNEAT（自适应 substrate），与项目既有的 MLP/GRU/Fixed Sparse RNN 固定拓扑基线互补。
**参数量口径**：无单篇文献定义容许倍数，建议按“一个数量级=10 倍”取 `|log10(N_base) - log10(N_ours)| <= 1`，并统一按网络连接（权重）数比较。
**环境惯例**：连续二维多智能体环境无统一世界尺寸，尺度依任务而定；MPE 是“小尺度、约 2 单位、10 Hz、25 步”的惯例，POSGGym 网格为 5x5–20x20、连续版本为 unicycle 2D；Arena 100x60 / 20 Hz / 600 步属自定尺度，需显式声明。

### Neuroevolution 基线原文

| 基线 | 出处 | 类型/评审 | 引用数 | 作用 |
|---|---|---|---|---|
| NEAT | Stanley & Miikkulainen 2002, *Evol Comput* 10(2):99-127；DOI 10.1162/106365602320169811 | peer-reviewed | 3315 | 演化拓扑+权重 |
| HyperNEAT | Stanley, D'Ambrosio & Gauci 2009, *Artif Life* 15(2):185-212；DOI 10.1162/artl.2009.15.2.15202 | peer-reviewed | 795 | CPPN 间接编码几何权重 |
| ES-HyperNEAT | Risi & Stanley 2012, *Artif Life* 18(4):331-355；DOI 10.1162/artl_a_00071 | peer-reviewed | 68 | 自适应位置/密度/连接 |

### 可运行实现（GitHub 核验）

| 仓库 | 星数 | 许可证 | 最近更新 | 备注 |
|---|---:|---|---|---|
| CodeReclaimers/neat-python | 1578 | BSD-3-Clause | 2026-09-22 | 纯 Python，NEAT 参考实现 |
| ukuleleplayer/pureples | 121 | MIT | 2026-07-03 | HyperNEAT + ES-HyperNEAT 纯 Python |
| EMI-Group/tensorneat | 400 | GPL-3.0 | 2026-09-11 | GPU 加速；GPL 需评估许可证兼容 |

### 参数量“同一数量级”的可量化口径

- **无文献直接定义容许倍数**，此为本项目操作性约定。科学惯例“一个数量级=10 倍”，建议判据 `|log10(N_base) - log10(N_ours)| <= 1`，即 0.1x–10x；更严可取 0.5（约 3x）。
- **比较单位必须声明**：统一按 substrate/网络的连接（权重）数，同时报告总参数与活跃参数（密度缩放后）。
- **HyperNEAT 口径陷阱**：其可演化对象是 CPPN（参数量小），被生成的 substrate 连接数可很大；不得用 CPPN 大小冒充网络参数量。
- **本项目参考量级**：DanioNet 固定 padding 到 48 nodes（DanioNet 设计规范 §3），连接密度 10%–20%（RGCD §8），可训练权重约 10^2–10^3 条连接量级。

### 连续二维多智能体环境尺度（源码/文档核验）

| 环境 | 空间尺度 | 更新频率 / episode | 出处 |
|---|---|---|---|
| PettingZoo MPE（MPE2 源码） | dim_p=2；simple_spread 实体初始位置 uniform(-1,+1)、agent.size=0.15；无硬边界，有效尺度约 2 单位 | dt=0.1 s（10 Hz）；simple_spread max_cycles=25（约 2.5 s / 25 步） | Farama-Foundation/MPE2，MIT，788 stars；core.py / simple_spread.py |
| POSGGym 网格 | Predator-Prey 默认 10x10，可选 5x5/15x15/20x20 | 离散回合制 | Schwartz et al. 2025, DOI 10.1007/s10458-025-09716-6；repo MIT，34 stars |
| POSGGym 连续 | Driving / Predator-Prey / Pursuit-Evasion 三个 2D 连续 unicycle 场景 | 连续控制 | 同上 |
| PettingZoo（框架） | 含 MPE 等环境族 | 由具体环境决定 | Terry et al. 2021, NeurIPS 34:15032-15043；repo MIT，3523 stars |

### 结论与风险点

- **Arena 100x60、20 Hz、30 s=600 steps 显著大于 MPE 尺度**，与 POSGGym 小规模场景同属“可完全仿真”范畴。论文中应声明 Arena 为自定尺度，并引用上述来源说明“该领域无统一世界尺寸”，不要声称遵循某个标准。
- **不建议直接套用 MPE 的 10 Hz / 2.5 s**。Arena 更新频率与 episode 长度更接近斑马鱼实验时长，需在本项目内自洽论证。
- **不要用低质结果充数**：本次未找到“连续二维多智能体环境世界尺寸=100x60”的先例；“同尺度先例”缺失，已在 JSON 中如实记录为 null/未找到。

---

## 分级结论速览

| 主题 | 推荐直接用 | 仅作参考 | 不建议 |
|---|---|---|---|
| R3 函数形式 | 指数衰减 `exp(-lambda*d)`（Waxman 1988；Kaiser & Hilgetag 2004；Ercsey-Ravasz 2013） | Ringo 1991；Betzel 2015；Kaiser 2005 技术报告 | 纯幂律；未标定的 Gaussian 核 |
| R3 参数 | 猕猴 lambda=0.188 mm^-1（须按本项目尺度重标定） | 其他物种 decay rate | 照搬 0.188 mm^-1 |
| R6 基线 | NEAT / HyperNEAT / ES-HyperNEAT 原文 + neat-python / pureples | tensorneat（GPL 许可待评估） | 无原始论文出处的不明实现 |
| R6 参数量 | `|log10(N_base)-log10(N_ours)|<=1`（自定口径） | 更严 0.5（约 3x） | 用 CPPN 大小冒充网络参数量 |
| R6 环境尺度 | MPE2 / POSGGym 作为惯例来源（仅参考其惯例，不套用其数值） | MPE 原始 MADDPG 环境 | 声称 Arena 尺度遵循某个标准 |
