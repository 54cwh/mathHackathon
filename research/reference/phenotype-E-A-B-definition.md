# phenotype E_A / E_B 定义调研（genome §3 缺口）

> 检索时间：2026-09-26
> 对应 JSON：`research/reference/phenotype-E-A-B-definition.json`（27 条 items：19 paper + 1 textbook/other + 7 repo）
> 只读调研：本文件与同名 JSON 之外未改动任何文件；未登记 `bibliography.md`。
> 关联契约：`genome/生物学与进化遗传学基础.md` §2/§3/§6、`development/RGCD数学模型.md` §2/§4/§11、`evolution/遗传繁殖与演化模型.md` §4、`research/notes/契约决策记录.md`（Mendel 映射）。

## 0. 缺口与结论速览

`genome §3` 只给了阈值判据 `high_N ⟺ E_A>θ_N`、`high_H ⟺ E_B>θ_H`，未给 `E_A`、`E_B` 的计算式。`evolution §4` 与 `契约决策记录.md` 已有一个 tentative 实例化 `E_A=q_0(G), E_B=q_1(G)`（全基因组读出）。本调研把它作为 C1，给出另两个候选 C2、C3，并按三条硬约束（9:3:3:1 独立分配 / 可由 genome 产物计算 / 两轴可独立变化）评估。

| 候选 | 定义要点 | 9:3:3:1 | 两轴独立 | θ 反解 | 分级 |
|---|---|---|---|---|---|
| **C1** 现状 tentative | `E_A=q_{k_A}(G), E_B=q_{k_B}(G)`，q 为全基因组（两染色体对并集） | 基因型级成立，表型级需标定 | **否**（跨位点泄漏） | 仅可标定 | 仅作参考（消融） |
| **C2** 推荐 | **位点限定** motif 子集均值，只扫本位点染色体对 | **结构性成立** | **是** | 半解析可反解 | **推荐直接用** |
| **C3** 解析基线 | `E_A=n_A/2, E_B=n_B/2`（功能等位剂量） | **精确成立**（penetrance=1） | 是 | **解析可反解** | 仅作参考（基线/消融） |

**一句话推荐**：把 `E_A`、`E_B` 的扫描域从"整个 haplotype 的两条染色体"收缩到"该位点自己的染色体对"（C2，MVP 取 `K_A={k_A}`、`K_B={k_B}`）。这是对现状 C1 的最小改动，修掉跨位点背景泄漏，同时保留 `genotype → 表达层 q → GRN → phenotype` 的链条。

## 1. 问题 1：两基因位点 → 数量/阈值性状的标准建模

**可操作形式**（文献支持的一般框架）：

1. **加性 gene action / gene dosage**：每个 allele 给一个效应，基因型值 = 两条 allele 效应之和（或均值）。`AA/Aa/aa → {1, 0.5, 0}` 就是这一编码在半合子平均下的取值。锚点：Fisher 1918（OpenAlex W2303043072，4510 引）的加性分解；Kacser & Burns 1981（W2106962907，1067 引）说明 50% 酶活性通常已在通路饱和区，故杂合子表型近野生型。
2. **liability-threshold**：连续潜变量 `E` 越过阈值 `θ` 才表现为离散类。一位点、一个阈值给 3:1；两位点、每轴一个阈值给 `2×2` 档，四基因型类计数 9:3:3:1。锚点：Falconer 1965（W1997887791，1691 引）；Falconer & Mackay 1996 Ch.18；Curnow 1972（W2335294278，52 引）；Roff 1996（W2064260728，449 引）明确阈值模型适用**多基因**离散形态。
3. **少数位点决定的数量性状 / GP map 单调性**：Gjuvsland et al. 2011（W1889204688）、2013（W2052276988）论证保序（allele 含量增加则表型不降）是加性方差占比高的前提，调控网络设计原则会生成高度单调的 GP map。这支持把 `E` 定义为对 allele 含量的**单调**聚合。
4. **canalization / robustness**：Waddington 1942（W2094902224，3350 引）；Green et al. 2017（W2774097669，124 引）实验操纵 Fgf8 剂量，显示剂量-表型变异是非线性/阈值关系。含义：显性与稳健性可以由下游 sigmoid/饱和非线性产生，不一定要求上游聚合算子硬编码。

**关键结论**：标准框架给的是"连续量 + 阈值 → 离散类"，**不规定**这个连续量怎么从具体 motif 构型算。`E_A/E_B` 的具体算式必然是项目选择，必须显式声明（沿用 `genotype-grn-aggregation.md` 的结论）。

## 2. 问题 2：合成生物学 / GRN 里 motif → expression 落在哪一层

**惯例**：motif/启动子亲和力决定转录因子结合占据，再由占据算转录速率，这是**表达层（cis-regulatory / gene expression）**；把这些"调控者→靶基因"的相互作用连成图、跑动力学，才是**调控网络层（GRN）**。

- Bintu et al. 2005（models，W2022891974，857 引；applications，W2144347639，432 引）：热力学/占据模型，表达强度 = f(TF 浓度, 结合位点亲和力)。这是 `PWM affinity → 表达强度` 的标准映射。
- Kuo, Banzhaf & Leier 2006（W2110436410，93 引）：ARN 用 genome bit string 与 protein 的互补匹配度作为调控强度。Cussat-Blanc et al. 2019（W2912050044，44 引，CC-BY-NC）：GRN 是 genotype 与 phenotype 之间的中介。
- Emmrich et al. 2015（W2155427821，CC-BY）：二倍体 Boolean GRN **不预先合并**，把两条 allele 都放进同一网络；显性定义为同 locus 的 allelomorphic pair 相互作用。

**对 EvoGenesis 的定位**：`q(G)`（RGCD §2）是表达层产物，作为 `B q(G)` 项进入 GRN（RGCD §4）。因此 `E_A/E_B` 应在**表达层**读出（`q` 与位点 allele 状态的函数），不应从网络拓扑读出。注意：`q(G)` 送入 GRN 的契约保持不变；C2 新增的只是"按位点染色体对限制扫描域"的额外读出，不改 `Bq(G)`。

## 3. 候选定义

约定：1 号染色体对承载 A 位点，2 号染色体对承载 B 位点（与 `evolution §4`"A/B 位于不同 chromosome pairs"一致）。haplotype `h` 的 1 号染色体记为 `C_A^h`（128 bp），2 号记为 `C_B^h`。`q_k(C)` 是 RGCD §2 `TopKMean` 在**单条染色体**上的限制（同一算子、限定扫描域、窗口不跨界）。功能等位使该位点 `q_k → 1`，功能丧失 `→ 背景 b`。

### C1（现状 tentative）：全基因组单 motif 读出

**定义式**：`E_A = q_{k_A}(G)`，`E_B = q_{k_B}(G)`，`k_A ≠ k_B`（默认 0, 1）；`q_k(G) = ½[q_k^{(h1)} + q_k^{(h2)}]`，扫描域为每个 haplotype 的**两条染色体窗口并集**。

**理由**：零新增算子，直接复用冻结的 `q(G)`；与 `evolution §4` 定稿一致。

**证据等级**：框架有据（Falconer 1965；Fisher 1918；Kacser & Burns 1981），**但"E_A 由全基因组 q_0 读出"这一具体选择无文献背书**，且不满足"一个位点一个轴"的语义。

**优点**：实现成本为零，不触发文档改动。

**风险**：
- `q_k` 的扫描域是两个染色体对（两个位点）的并集，`E_A` **不是** A 位点 allele 的函数：B 位点上的 motif `k_A` 命中会窜入 `E_A`。
- 背景亲和力使 `aa` 基线 `b>0`、`Aa` 非精确 0.5，`θ` 反解依赖分布校准，penetrance 可能 <1。
- 两轴不独立，`2×2` 可能出现非对角占位。
- 每轴单 motif，是单基因读出。

**判定**：仅作参考（消融/退化基线）。

### C2（推荐）：位点限定 motif 子集均值

**定义式**：motif 目录划分为两位点子集 `K_A, K_B`（不相交），

```
E_A = (1/|K_A|) · Σ_{k∈K_A} ½[ q_k(C_A^{h1}) + q_k(C_A^{h2}) ]
E_B = (1/|K_B|) · Σ_{k∈K_B} ½[ q_k(C_B^{h1}) + q_k(C_B^{h2}) ]
```

MVP 取 `K_A={k_A}`、`K_B={k_B}`。`high_N ⟺ E_A>θ_N`，`high_H ⟺ E_B>θ_H`。

**理由**：
- `E_A` 只依赖 A 位点（1 号染色体对）allele，`E_B` 只依赖 B 位点（2 号染色体对）allele，不同染色体对独立分配 → 两轴**结构性独立**，四基因型类 9:3:3:1，四格各有群体。
- 功能等位使 `q_k→1`、丧失使 `q_k→b`，半合子平均给 `{1, (1+b)/2, b}`；取 `θ∈(b, (1+b)/2)` 即得完全显性（`A_` 全 high）。
- `|K_A|>1` 时在一个位点内产生连续剂量（多 motif 聚合），避免精确退化为单 motif 开关。
- 只用到已定义的 `TopKMean` 与位点 allele 状态；不改变送入 GRN 的全域 `q(G)`，`Bq(G)` 契约不变。
- 对现状 C1 的改动最小（只在扫描域上加"限于本位点染色体对"）。

**证据等级**：定义形式有据（加性/gene dosage：Fisher 1918、Kacser & Burns 1981；单调 GP map：Gjuvsland 2011/2013；阈值：Falconer 1965、Roff 1996；表达层 motif→expression：Bintu 2005；GRN 涌现 dominance：Omholt 2000）。"两位点各绑定一个架构轴 + 具体 `K_A/K_B` 划分"属**项目设计选择**，无文献背书。

**θ 反解**：取校准集上 `aa` 组 `E` 的上尾与 `Aa` 组 `E` 的下尾之间的中点；理想无背景时退化为解析区间 `(0, 0.5)`。数值登记 `docs/参数总表.json`，禁止实现侧自选。

**风险**：
- 实现需按染色体对分别计算 affinity（现 `genome.py` 只按单串 128 bp 校验，属既有实现偏离，需随 C2 一并修正）。
- `K_A/K_B` 划分是设计选择；换 motif 索引不改变统计（motif 可交换标签）。
- 背景 `b` 仍非零，`θ` 需校准并报 penetrance；`b` 随突变/代数漂移，须标明校准代数。
- `|K_A|=1` 时每轴仍由单孟德尔位点控制，论文须声明为演示装置。
- 若 `K_A/K_B` 选到易互相命中的 motif，背景相关会削弱独立性。

**判定**：推荐直接用（MVP 取 `K_A={k_A}`、`K_B={k_B}`）。

### C3（解析基线/消融）：等位基因剂量分

**定义式**：`E_A = n_A/2`，`E_B = n_B/2`，`n_A = x_A^{(h1)} + x_A^{(h2)} ∈ {0,1,2}` 为功能 A 等位计数（`x_A^{(h)}=1` 当且仅当该 haplotype 的 1 号染色体携带 A 位点功能 motif），`n_B` 同理。等价于对功能等位指示做半合子加性平均，是 C2 在 `b→0, |K_A|=1` 下的极限。

**理由**：最简、精确。

**证据等级**：Fisher 1918 的加性分解直接对应；`E_A∈{0,0.5,1}` 的阈值读法属教科书级（Falconer & Mackay 体系）。

**θ 反解**：解析。`θ_N, θ_H ∈ (0, 0.5)`，任意取值均得完全显性；推荐 0.25（到 0 与 0.5 等距，裕度最大）。penetrance 恒为 1。

**风险**：
- genotype 直跳 phenotype，绕过 GRN/表达层：`q(G)`、motif affinity 在 Mendel 演示中沦为装饰，"同一 genotype 不同内部状态"的 phenotype 连续性丧失。
- 无 canalization/噪声，无法体现 liability-threshold 的连续潜变量语义。
- 每轴单基因决定；若被当作最终定义，会弱化"GRN 发育"的项目主线。
- 功能等位定义依赖工程构造，启用真实突变背景后需重新定义。

**判定**：仅作参考（推荐作为解析基线、penetrance=1 对照与单元测试参照）。

## 4. 推荐定义（可直接写进 genome 文档）

> 设 A 位点位于 1 号染色体对、B 位点位于 2 号染色体对；将 8 条 motif 目录划分为两位点子集 `K_A, K_B`（MVP 取 `K_A={k_A}`、`K_B={k_B}`，`k_A≠k_B`）。对每个位点**只在该位点自身染色体对上**计算单链 motif affinity，再在两条同源链上取加性均值：
>
> ```
> E_A(G) = (1/|K_A|) Σ_{k∈K_A} ½[ q_k(C_A^{h1}) + q_k(C_A^{h2}) ]
> E_B(G) = (1/|K_B|) Σ_{k∈K_B} ½[ q_k(C_B^{h1}) + q_k(C_B^{h2}) ]
> ```
>
> 其中 `q_k(C)` 为 RGCD §2 `TopKMean` 在单条 128 bp 染色体上的限制（窗口不跨界）。功能等位使 `q_k→1`，功能丧失使 `q_k→背景 b`。则
>
> ```
> high_N ⟺ E_A > θ_N ,   high_H ⟺ E_B > θ_H ,
> ```
>
> MVP 取 `K_A={k_A}, K_B={k_B}`，`θ_N, θ_H ∈ (b, (1+b)/2)`（标定，登记 `docs/参数总表.json`）；无背景的理想极限下 `θ ∈ (0,0.5)`。确定性消融基线取 `E_A=n_A/2, E_B=n_B/2`。

一句话版本：**`E_A` = 只在 A 位点染色体对上算的 motif 子集平均亲和力（两条同源链做加性平均）；`E_B` 同理；阈值化即得完全显性的 2×2 架构档。**

## 5. 未找到 / 需进一步验证

1. **无现成文献定义**"motif-affinity genome + 两位点 2×2 架构档"的 `E_A/E_B`：只能引通用框架（阈值 + 加性），算式属项目自定义。
2. **arXiv MCP 本次不可用**：所有查询返回 HTTP 406，未取得 arXiv preprint 证据（已用 OpenAlex/DOI 替代）。
3. **无可复用 py/uv diploid motif→expression 实现**：`gh` 命中的 aGRN 仓库为 C++/Julia/停更/无 license（`jdisset/grgen` 3★ LGPL C++；`d9w/AGRN.jl` 3★ Julia；`Sisyphus192/Kern-AGRN` 1★ 无 license；`Mehrshad-Ebadi/With_Mutation` 0★ 无 license）。NCA 类（`PWhiddy` 144★ Apache-2.0；`chenmingxiang110` 255★ MIT；`mspitzna/NCAtorch` 15★ MIT）非 diploid，仅作背景对照。**无"推荐直接用"项**；本项目自包含，无需外部依赖。
4. **`θ_N/θ_H` 数值**：无文献来源，必须标定/反解，禁止编造。
5. **`K_A/K_B` 划分与 `θ` 校准**：须登记 `docs/参数总表.json`；penetrance 与 n=160 "演示非验证"口径沿用 `phenotype-threshold-mendel.md`。
6. **与现有定稿的冲突**：`evolution §4` 已把 C1 标为"定稿，Mendel 演示实例化"。改用 C2 须由用户决定并回写 `evolution §4` / `genome §3`（本调研不修改文档）。

## 6. 依据条目数

- 共 27 条 items：19 篇 paper（含 2 篇既有调研复用）、1 条 textbook/other（Falconer & Mackay 1996）、7 个 GitHub repo。
- 其中 peer_review=true 的 paper 18 篇（Fisher 1918 属历史学会刊，记为 peer_review=true）；Falconer & Mackay 教材与全部 repo 为 peer_review=false。
- 引用数均取自 OpenAlex（2026-09-26）；star/license/last push 取自 `gh repo view`（2026-09-26）。
