# H1–H5 可证伪量化判据与 RQ↔H↔Experiment 映射调研

> 检索时间：2026-09-26 ｜ 输出：`research/reference/hypothesis-criteria.json`（41 条，所有 DOI/仓库经 OpenAlex 与 GitHub CLI 核实）
> 范围：为 `src/evogenesis/问题定义与研究假设.md` §2/§3 的 RQ1–5 与 H1–5，以及 `src/evogenesis/experiment/实验与评价体系.md` 的 Experiment A–F + Mendelian + Efficiency，给出「度量 + 检验方法 + 判据草案」。**只做信息采集与评估，未修改任何代码或配置。**

---

## 1. 一句话结论

H1–H5 需要的度量**几乎都有权威文献锚点**，可迁移的是「度量定义 + 检验方法 + 零模型基线」；**没有任何文献能给出本项目的具体阈值**，所有阈值必须由 pilot 数据反解，本报告不提供杜撰数值。

方法学组织范式采用 **GQM（Goal→Question→Metric，Basili et al. 1994）**——正是本项目缺失的 RQ↔H↔Experiment 对应表应采用的骨架。

---

## 2. 必须先解决的两个阻断项

1. **n=3 种子的统计分辨率不足**。若把 genome 当处理组做标签置换，3-vs-3 只有 C(6,3)=20 种划分，双侧最小 p≈0.10，**永远达不到 0.05**。
   - 正解（文献支撑）：用 **within-ensemble graph distance**（Hartle et al. 2020）：以「同 genome 跨 seed 的距离分布」或「度序列保持的重连零模型（≥1000 零图）」为基线，判断跨 genome 距离是否超出零分布。
   - **Mantel 检验**（Smouse et al. 1986）针对距离矩阵行置换，p 不受 3-vs-3 限制，适合 H2。
   - 此点必须回写实验与评价体系文档，否则 H1 的显著性无法成立。
2. **H3 的「历史依赖任务」未定义**（Arena 文档无对应任务），H3 目前不可直接检验；须先在 `arena/Danio_Arena设计规范.md` 定义任务（如 delayed-cue / 积分记忆）。`bib#11`（Zhao 2026 历史依赖决策）只提供生物动机，不是任务定义。

另一个缺口：**H2 没有专门的实验项**。A–F 没有「connectome/动力学差异 → 行为差异」的直接检验，需在 A/B/C 数据上补 Mantel / 秩相关分析并回写文档。

---

## 3. H1–H5 判据草案（度量 + 检验 + 阈值状态）

> 标注：`[文献]` 有文献支撑 ｜ `[工程]` 本项目工程口径 ｜ `[待 pilot]` 阈值须由 pilot 数据反解

### H1 不同 genome 在相同 seed 下产生系统性 connectome 差异
- **度量** `[文献]`：边集 Jaccard 距离 `d_J=1-|E1∩E2|/|E1∪E2|`；Laplacian 谱距离（Ipsen-Mikhailov / LaplacianSpectral，Wilson & Zhu 2008）；归一化 Hamming/对称差；度分布 JSD；Δ模块度（Newman 2006，辅助）。
- **工程简化** `[工程]`：DanioNet 固定 48 节点、节点身份稳定，可**直接按 node label 对齐，无需图匹配**。
- **判据草案**：跨 genome 距离均值显著大于同 genome 跨 seed 基线 / 重连零模型（置换 p<0.05，零图数≥1000），且效应量 ≥ θ_H1；逐对报 mean±std（3 seeds）。`[待 pilot]` θ_H1。
- **首选实现**：`netrd`（MIT）；`networkx.graph_edit_distance / laplacian_spectrum`。

### H2 connectome/动力学差异导致行为差异
- **度量**：离散 behavioral state 直方图的 JSD（Marques 2018；Berman 2014）；`(x,y,θ)` 轨迹 DTW（Berndt 1994；FastDTW Salvador & Chan 2007）；标量任务量差。
- **检验**：genome 对为样本的 **Mantel 检验**（Smouse 1986）比较 connectome 距离矩阵 vs behavior 距离矩阵；或 Spearman/Kendall 秩相关 + 置换（`scipy.stats.permutation_test`, `permutation_type='pairings'`）。
- **判据草案**：Mantel r>0 且置换 p<0.05，且跨 genome 行为距离 > 同 genome 跨 seed 噪声基线。`[待 pilot]` r_min。
- **阻断缺口**：需补专门分析（见 §2）。

### H3 异质 τ 在历史依赖任务中的性能—效率权衡
- **度量** `[文献]`：双目标 Pareto 前沿（TaskPerformance, Cost），Cost = `ActiveConnections×Timesteps`（`[工程]`）或 latency/active edges；前沿比较用 hypervolume / 非支配计数（Deb 2002；pymoo）；τ 异质性用 CV(τ) 或分布熵。
- **检验**：Full（异质 τ）vs Experiment D 的 homogeneous-τ，比较 hypervolume 与支配关系，跨 3 seeds 报 mean±std。
- **判据草案**：异质 τ 前沿 hypervolume 高于同质 τ（差值 > seed 波动、方向在 ≥2/3 seeds 一致），或存在同时更优性能与更低成本的 Pareto 点。`[待 pilot]` hypervolume 差阈值。
- **风险**：Shoval et al. 2012 的 Pareto 检验须防 pseudoreplication（Edelaar 2013）——前沿点来自同一演化过程，非独立样本。

### H4 spatial wiring cost 改变局部性、稀疏性与 active-edge efficiency
- **度量** `[文献]`：局部性 = 平均/最大 wiring length（发育 2D 坐标欧氏距离加权）+ 局部聚类系数 C（Watts & Strogatz 1998）+ 局部效率 E_loc；稀疏性 `ρ=2E/(N(N-1))`；图论全局效率 E_glob（Latora & Marchiori 2001）；成本侧 = active edges / latency。
- **命名冲突警示**：图论 efficiency（E_glob/E_loc）与项目 `Efficiency=TaskPerformance/(ActiveConnections×Timesteps)` **同名不同义**，必须在文档中把后者改名为 **active-edge efficiency**。
- **检验**：Experiment D `w/o spatial wiring cost` vs Full，配对（同 seed）比较，回归 wiring cost 系数。
- **判据草案**：去除 spatial cost 后 wire-length / 稀疏性朝随机方向显著移动（方向在 ≥2/3 seeds 一致）且 active-edge efficiency 下降。`[待 pilot]` 位移阈值。方向预期来自 Chklovskii & Stevens 1999、Bullmore & Sporns 2009（其「导线占约 60% 体积」是皮层结论，**不可搬为本项目参数**）。

### H5 fitness 依赖环境，不存在对所有环境都占优的 genotype
- **度量** `[文献]`：reaction norm（Via & Lande 1985；Scheiner 1993；行为层见 Dingemanse 2009）；G×E 交互项；环境间 fitness 秩相关 (Spearman/Kendall)。
- **检验**：混合模型 `fitness ~ G + E + G×E`，或 AMMI / GGE biplot 识别 rank reversal（Malosetti 2013）。
- **判据草案**：「不存在普遍占优」操作化为——各环境 argmax genotype 的集合交集为空，或存在 ≥1 对 crossover 秩反转；且 G×E 交互显著（p<0.05）。`[待 pilot]` 检验功效（3 seeds × 3 环境 × 10–20 代可能不足）。
- **注意**：区分 G×E 交互与 G-E 相关（Plomin 1977）；G×E 是维持多样性的**机制而非噪声**（Gillespie & Turelli 1989），「无普遍占优」应是预期结果。

---

## 4. RQ ↔ H ↔ Experiment 推荐映射表

| 实验 | 名称 | 主要 RQ | 主要 H | 关键度量 |
|---|---|---|---|---|
| A | Genome→Architecture | RQ1 | **H1** | edge density、tau 分布、cell-type 分布、connectome 距离矩阵 |
| B | Single-base Mutation | RQ2 | **H1**（结构突变/连续） | d_edge、d_τ、ΔBehavior、Genome Sensitivity Map |
| C | Baseline | RQ3 | **H2/H3** | survival/capture/escape/energy/latency/active edges/params |
| D | Ablation | RQ3 | **H3/H4** | homogeneous tau、w/o spatial wiring cost、w/o GRN、w/o epistasis |
| E | Robustness | RQ3 | **H3**（鲁棒性） | 删 active edges 5/10/20% 后 degradation |
| F | Environmental Selection | RQ4 | **H5** | allele/phenotype freq、viability、fitness、G×E、τ/edge 统计 |
| Mendelian | AaBb×AaBb 验证 | RQ5 | —（映射架构/行为 segregation） | empirical ratio + χ² |
| Efficiency | 效率报告 | RQ3 | **H3/H4** | `TaskPerformance/(ActiveConnections×Timesteps)` + params/active edges/latency/peak mem |

**缺口**：H2 无专门实验（须补 connectome↔behavior 相关分析）；H3 的历史依赖任务未定义（阻断）；RQ5 的 architectural/behavioral segregation 需由 Mendelian × A 的联合分析补上（现表只覆盖基因型比例）。

---

## 5. 推荐分级

- **推荐直接用**：`netrd`（MIT，图距离全家桶）、`networkx`（GED + Laplacian 谱）、`scipy.stats.permutation_test`（置换检验，已在技术栈内）。
- **仅作参考**：`pymoo`（Pareto/hypervolume，Apache-2.0，活跃）、`graspologic`（两样本图检验，MIT，依赖较重）、`dtaidistance`（DTW，含 C 扩展）、`B-SOiD`（GPL-3.0，注意传染性）、`Bartz-Beielstein 2020`（benchmarking best practice，preprint）。
- **不建议**：MotionMapper（2020 停滞、无 license、MATLAB 栈）、`markjin1990` 的 GED（0 star、无 license、2017 停滞）；不以单一标量（仅 fitness）作为 H1–H5 判据。

---

## 6. 需进一步验证的风险点

1. `netrd` 最近 push 2023-03，须验证与 Python 3.12 / 当前 NetworkX 的兼容性。
2. 精确 GED 为 NP-hard，48 节点应设 `upper_bound` 或用近似/替代度量（Gao 2009；Riesen & Bunke 2008）。
3. `networkx` 与 `dtaidistance` 的 license 在 GitHub API 标为 Other，须核仓库 LICENSE 才能作为比赛依赖。
4. `dtaidistance` 含 C 扩展，离线安装须确认 wheel 可用。
5. 所有「阈值」栏为空，须由 pilot 数据反解并回写 `docs/参数总表.json`（标注 `草案待确认` / `已定稿`），本报告不提供数值。
6. H1 的零模型基线、H2 的专门分析、H3 的任务定义，均需回写对应模块文档后方可进入正式实验。
