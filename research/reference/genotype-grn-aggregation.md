# genotype → GRN：两条 homolog 的聚合算子（调研摘要）

> 检索时间：2026-09-26
> 对应 JSON：`research/reference/genotype-grn-aggregation.json`
> 关联文档：`genome/生物学与进化遗传学基础.md` §6、`development/RGCD数学模型.md` §2/§4、`genome` 阅读问题 #1、RGCD 阅读问题 #5/#6
> 只读调研：本文件与 JSON 之外未改动任何文件。

## 0. 一句话结论

文献**没有**给出唯一的"allele 聚合算子"；聚合方式等价于显式声明基因作用模式，必须由项目选为设计参数。有据的口径只有两条：两条 homolog 的 motif-affinity 分别计算后**取均值（加性 / gene dosage）**或**取 max（逐分量完全显性）**；其中**加性 + 下游 sigmoid 阈值**更贴近主线理论（Omholt 2000、Kacser & Burns 1981），建议作默主模型，max 作必做消融。

## 1. 问题 #1：二倍体基因型 → 表达量的聚合

| 口径 | 文献依据 | 关键内容 |
|---|---|---|
| 加性 additive | Fisher 1918 的加性分解（PMC3817948 复述）；定量遗传标准编码 | 每个 allele 给一个效应 C(·)，基因型值 `G(A_i,A_j)=C(A_i)+C(A_j)`，即两条效应**相加** |
| 完全显性 complete dominance | Iowa State 开放教科书 Chapter 5；Falconer & Mackay 体系 | `d=0` 为完全加性；`d=+a` 或 `d=-a` 为完全显性（杂合子 genotypic value 等于一个纯合子） |
| 部分显性 / overdominance | Agrawal & Whitlock 2010 | 显性系数是连续谱，酵母 knockout 平均 dominance coefficient ≈ 0.2，介于加性 0 与完全显性 1 之间 |

关于"min/max 等价于完全显性"：**该说法在形式层面成立，但我没有找到一篇同行评审文献明确写出这个算子对应**。可核实的是它的**行为定义**：当两条 allele 的效应是标量 e∈{0,1}、基因型值取 `max(e1,e2)` 时，杂合子值与携带功能 allele 的纯合子相同，这正好满足 `d=+a` 的完全显性定义（隐性方向用 `min`，对应 `d=-a`）。因此**算子本身应标注为工程选择，其所产生表型有 d=±a 的文献定义作口径**。

## 2. 问题 #2：GRN 模型的输入编码（是否有"两个 homolog 各算一次再合并"）

- **Omholt et al. 2000（Genetics，cited 178）**：这是本主题最强的理论锚点。它证明在简单的 **diploid GRN** 中，additivity、dominance、overdominance、epistasis 都是"两条 allele 各自的 gene dosage / 表达 / 蛋白活性"加下游非线性调控的**涌现性质**；摘要明确把 reduced/increased gene dosage 与 haploinsufficiency 列为 dominance 来源。它把合并放在网络内部，而不是先定一个聚合算子。
  - 限制：全文仅 PMC PDF，本次解析失败，其**具体 allele 合并方程未逐字核实**；结论基于摘要与二手复述。
- **Banzhaf 2003 ARN / Kuo et al. 2006**：genome 为 bit string，protein 与 promoter 做 XOR 互补匹配，匹配度作为调控强度参数。这是与"motif affinity → 调控输入"最同构的人工 GRN 编码，但 **ARN 是单倍体**，不含两条 homolog 聚合。
- **Emmrich et al. 2015（BMC Evol Biol）**：diploid Boolean GRN，个体网络**同时包含双亲的全部 allele**（G1,G1',G2,G2'），显性被定义为同一 locus 的 allelomorphic pair 之间的相互作用，通过移除/同源化个别 allele 来估计。也就是说，**有的 diploid GRN 不预先合并，而是把两条 allele 都放进同一网络**。
- **Growing NCA（Mordvintsev 2020）**：人工发育系统，但"基因型"是训练得到的网络权重，非可解释序列，也无 homolog 聚合，**仅作背景对照**。

## 3. 问题 #3：dominance-like 的阈值建模

- **Kacser & Burns 1981（cited 1067）**：酶网络的饱和非线性使一个 functional allele 的活性通常已接近通路饱和，因此杂合子表型接近野生型纯合子。**显性来自下游非线性，聚合算子不必是 max**。
- **Veitia et al. 2017 / Billiard et al. 2021**：显性源于 genotypic value 与 phenotypic value 的**非线性映射**；haploinsufficiency、dominant negative 都可在"剂量 + 阈值"框架下产生显性。Billiard 2021 把 Fisher 与 Wright 两派统一为"diploid genotype 与 phenotype 之间非线性映射的产物"。
- **阈值模型**：`Curnow 1972`（cited 52）形式化 Falconer 的 liability-threshold 模型——表型取决于一个连续潜在量 x，越过阈值才表现。这与 genome §6 的 phenotype threshold 直接相关（文档已声明"相关但不等同"）。
- **Green et al. 2017**：实验操纵 Fgf8 基因剂量，显示剂量与表型变异间存在非线性/阈值型响应，为"一个 functional allele 足够"提供实验证据。

## 4. 问题 #4：motif affinity（PWM/PSSM）对两条 homolog 的打分合并

**结论：allele-specific binding 文献的通行做法不是合并，而是分别打分后报告差异。**

- **Yan et al. 2021（Nature, SNP-SELEX）**：对 reference 与 alternative 两条 allele **分别计算 PWM 打分**，再用 `ΔPWM = score(ref) − score(alt)` 表示变异效应。
- **Abramov et al. 2021（Nat Commun, ASB）**：对每个 allele 的 motif hit 分别打分，用两条 allele PWM hit 的 P 值 log ratio 作为 affinity fold change。
- **Boytsov et al. 2022（F1000Research）**：评估并支持 PWM 对两条 allele 差异结合的预测能力。

因此："两条 homolog 各算一次 affinity"**有据**；"把两者合并成单一 q"**没有既定惯例**，属 GRN 建模选择，本项目须显式声明。

## 5. 推荐：给 EvoGenesis 的聚合算子

RGCD §2 已定义单条序列的 `q_k(S)=TopKMean_s a(M_k,s)`。建议对其逐 haplotype 计算：

```
q^(h1) = q(G_h1),  q^(h2) = q(G_h2)      # 各 ∈ [0,1]^8，沿用 RGCD §2
```

| 优先级 | 算子 | 对应基因作用 | 依据 |
|---|---|---|---|
| **主模型（推荐）** | `q = (q^(h1) + q^(h2)) / 2` | 加性 / gene dosage | Fisher 1918 加性分解；Omholt 2000（gene dosage + 非线性涌现 dominance） |
| **必做消融** | `q = max(q^(h1), q^(h2))` | 逐分量完全显性 | 完全显性定义 `d=+a`（Iowa State 教科书） |
| **对照** | `q = q^(h1)`（单倍型） | 单 allele | 单倍体基线 |
| **不建议** | `q = q^(h1) + q^(h2)` 不重标定 B | —— | q 被推到 [0,2]^8，σ 提前饱和，丢失阈值语义 |

### 该算子如何产生 RGCD §4 所需的 `q`

RGCD §4 的唯一正式式为：

```
g_i^{r+1} = (1-ρ) g_i^r + ρ σ( W_g g_i^r + B q(G) + P p_i + b )
```

它只要求一个 `q(G)∈[0,1]^8`。把两条 homolog 的 affinity 先合并成单一 q，再送入 `B q(G)`，即可满足该契约：

- **加性路径（默认）**：`mean` 给出归一化到 [0,1] 的 q，保持值域与 B 的尺度语义；dominance-like 由 σ 与 phenotype threshold **涌现**（单个 functional allele 已使 σ 饱和时即表现为完全显性）。
- **显性路径（消融）**：`max` 在聚合处直接实现逐分量完全显性，绕过下游饱和，可用于对照"显性由上游硬编码 vs 由下游涌现"的结构差异。
- 合并后 `q` 的维度与值域仍与 §4 契约一致；`B` 的形状仍待 G1 定义，本调研不改变该缺口。

### 明确区分

- **文献有据**：加性 = 效应相加 / 取均值（Fisher 1918、PMC3817948、Omholt 2000）；完全显性 = `d=±a` 的行为定义（Iowa State 教科书、Falconer & Mackay 体系）；dominance 可由下游非线性涌现（Kacser & Burns 1981、Veitia 2017、Billiard 2021）；两条 allele 各算一次 affinity（Yan 2021、Abramov 2021）。
- **工程选择**：把 `max`/`mean` 作为算子落实到向量 q；默认选加性、消融选 max；q 的归一化与 B 尺度绑定。这些**没有**现成文献条款，须在 genome §6 与论文中显式声明为设计选择。

## 6. 没找到的部分（不用低质结果充数）

1. **没有**任何同行评审文献明确写出"两条 homolog 的 motif-affinity 取 max = 完全显性 / 取均值 = 加性"。该对应是我基于 `d=0` 与 `d=±a` 定义做的形式推导。
2. **没有**已确立的"把两条 homolog 的 PWM/PSSM 打分合并成单一 affinity"惯例；ASB 领域的标准是分别打分后报告差值/比值。
3. **没有**可直接复用的 py/uv 生态的 diploid-genotype → GRN 聚合实现。现有 GRN 仓库多为单倍体，或为 C++/Julia（见下）。
4. **Omholt 2000 的具体 allele 合并方程未取得**（PDF 解析失败）。

## 7. 开源实现评估（GitHub，`gh api` 核实于 2026-09-26）

| 仓库 | 语言 | star | 许可 | 最近 push | 结论 |
|---|---|---:|---|---|---|
| `chenmingxiang110/Growing-Neural-Cellular-Automata` | Python | 255 | MIT | 2023-07 | 仅作参考（NCA，非 diploid） |
| `PWhiddy/Growing-Neural-Cellular-Automata-Pytorch` | Jupyter | 144 | Apache-2.0 | 2025-09 | 仅作参考 |
| `distillpub/post--growing-ca` | HTML | 106 | CC-BY-4.0 | 2022-08 | 仅作参考（NCA 官方） |
| `mspitzna/NCAtorch` | Python | 15 | MIT | 2026-09 | 仅作参考（轻量 NCA） |
| `antoncrombach/gene-network-evolvability` | C++ | 1 | 无 | 2016-12 | 不建议（无 license、非 Python） |
| `d9w/AGRN.jl` | Julia | 3 | Apache-2.0 | 2018-09 | 不建议（Julia） |
| `heavywatal/gerene` | C++ | 0 | MIT | 2025-11 | 不建议（非 Python） |

**结论**：无"推荐直接用"的现成实现；上述均为"仅作参考"。本项目的聚合算子需要自研，规模很小（每个 haplotype 一次 TopKMean 后逐分量 mean/max），无需外部依赖。

## 8. 风险点（需进一步验证）

1. **Omholt 2000 原文方程未逐字核实**——正式引用前必须核对原文（其 allele 合并式是本主题最关键的证据）。
2. **逐分量 max ≠ 单基因座完全显性**：不同 motif 的显性方向可能不一致，论文须声明为"逐 motif 完全显性投影"。
3. **跨层类比**：文献的 diploid GRN 多为每 locus 一个标量表达量，本项目是每 locus 两条 homolog 的 8 维 motif-affinity 向量，须声明。
4. **阈值数值未定（G12）**：dominance-like 的可计算性依赖 phenotype threshold。
5. **引用待补**：Falconer 1965 原始阈值论文未取得可核实 DOI（本文件以 Curnow 1972 替代）；PMC3817948 与 Boytsov 2022 的 DOI/期刊信息未核。

## 9. 主要来源索引

- Omholt et al. 2000, *Genetics* 155:969 — https://doi.org/10.1093/genetics/155.2.969 （PMC1461103）
- Kacser & Burns 1981, *Genetics* 97:639 — https://doi.org/10.1093/genetics/97.3-4.639
- Gjuvsland et al. 2006, *Genetics* 175:411 — https://doi.org/10.1534/genetics.106.058859
- Banzhaf 2003, *GP Theory and Practice* ch.4 — https://doi.org/10.1007/978-1-4419-8983-3_4
- Kuo, Banzhaf & Leier 2006, *BioSystems* — https://doi.org/10.1016/j.biosystems.2006.01.004
- Cussat-Blanc et al. 2019, *Artificial Life* — https://doi.org/10.1162/artl_a_00267
- Emmrich et al. 2015, *BMC Evol Biol* — https://doi.org/10.1186/s12862-015-0298-0
- Yan et al. 2021, *Nature* (SNP-SELEX) — https://doi.org/10.1038/s41586-021-03211-0
- Abramov et al. 2021, *Nat Commun* (ASB) — https://doi.org/10.1038/s41467-021-23007-0
- Veitia et al. 2017, *Clin Genet* — https://doi.org/10.1111/cge.13107
- Billiard et al. 2021, *Biol Rev* — https://doi.org/10.1111/brv.12786
- Agrawal & Whitlock 2010, *Genetics* 187:553 — https://doi.org/10.1534/genetics.110.124560
- Curnow 1972, *Biometrics* — https://doi.org/10.2307/2528630
- Iowa State 开放教科书, *Quantitative Genetics for Plant Breeding*, Ch.5 — https://iastate.pressbooks.pub/quantitativegenetics/chapter/gene-effects

（完整字段、metrics、peer_review 标注见同名 JSON。）
