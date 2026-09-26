# EvoGenesis 项目总交接稿

## 1. 项目目标
EvoGenesis 建立一个统一的数学—计算系统，使一段可编辑、可遗传的人工 DNA 真正进入神经网络生成过程，并沿以下链路影响行为：

\[
DNA \rightarrow Regulation \rightarrow Development \rightarrow Connectome \rightarrow Dynamics \rightarrow Behavior
\]

个体行为进一步决定：

\[
Behavior \rightarrow Fitness \rightarrow Reproduction \rightarrow DNA'
\]

项目以斑马鱼为生物学参考模型，提取捕食、威胁检测、左右运动竞争、时间积分和内部饥饿状态调制等计算原则，但不做真实斑马鱼大脑的逐神经元复刻。

## 2. 核心研究问题
**一个紧凑、可编辑、可遗传的人工 regulatory genome，能否通过统一的发育规则生成具有异质连接结构和异质神经动力学的网络，并在不同生态环境中形成可遗传、可选择的行为差异？**

必须通过实验验证三条命题：

\[
Different\ DNA \Rightarrow Different\ Neural\ Architecture
\]

\[
Different\ Neural\ Architecture \Rightarrow Different\ Behavior
\]

\[
Different\ Environment \Rightarrow Different\ Evolutionary\ Outcome
\]

## 3. 系统层级
- **EvoGenesis**：总体项目与演化发育计算框架。
- **RGCD**：Regulatory Genome-to-Connectome Decoder，核心算法。
- **DanioNet**：RGCD 发育产生的异质、稀疏、循环神经网络。
- **DNA2Brain Lab**：人工 DNA 编辑、motif、GRN、发育和 mutation causal chain 的交互实验台。
- **Danio Arena**：二维捕食—逃逸—能量—成长生态环境。

## 4. 核心区别
人工 DNA 不直接存储最终神经连接矩阵：

\[
Genome \neq Connectome
\]

而是：

\[
Genome \xrightarrow{Development} Connectome
\]

最终权重分为：

\[
W = W^{(0)}(Development) + \Delta W(Lifetime\ Learning)
\]

后天学习产生的 \(\Delta W\) 不遗传。

后代继承的是 DNA：

\[
DNA_{parents}
\rightarrow Gametes
\rightarrow DNA_{offspring}
\rightarrow Development
\rightarrow DanioNet_{offspring}
\]

## 5. 生物学层次
遗传层：二倍体、allele、segregation、independent assortment、crossover、SNP mutation、dominance-like phenotype、optional epistasis。

发育层：precursor domains、regulatory motif、GRN、proliferation、cell differentiation、spatial wiring cost、cell-type compatibility。

神经层：cell-type heterogeneity、Dale-like output sign、recurrent integration、inhibitory competition、heterogeneous time constants、bilateral sensorimotor channels。

生理层：energy、hunger、body size。

生态层：prey、predator、obstacle、Food Rich / Predator Rich / Resource Scarce。

演化层：fitness-dependent reproduction、finite-population sampling、genetic drift、mutation、recombination、generation replacement。

## 6. 当前默认规模
- 2 对同源染色体
- 128 bp / chromosome haplotype
- 256 bp haploid
- 512 bp diploid
- 8 motifs
- 8 GRN variables
- 12 GRN development steps
- 24 initial precursors
- 6 developmental domains × 4
- max one division / precursor
- max 48 neurons
- 6 neural fates
- target connectivity density 10%–20%
- no self loops
- \(\tau_i \in [1,10]\)
- 12-d sensory input
- 2-d continuous motor output
- 20 Hz
- 30 s / episode = 600 steps
- Live Demo：12 fish / 24 prey / 3 predators / 6 obstacles
- Fast Evolution：N=48
- \(\mu=10^{-3}\) / base / gamete
- \(\beta=3\)
- Mendel Mode：160 offspring
- 正式实验至少 3 个随机种子

## 7. 现场交互闭环
### Mutation
选鱼 → DNA → 改一个 base → Re-develop → Before/After → Release → 比较行为。

### Breeding
Parent A → Parent B → meiosis/recombination → offspring → development → DanioNet。

### Evolution
切换环境 → Evolve 1/5/10/20 Generations → allele / phenotype / fitness trajectory。

### Mendel Mode
AaBb × AaBb → gametes → theoretical 9:3:3:1 → empirical finite-sample ratio → 四类 neural phenotype。

## 8. MVP 成功标准
1. genome 能稳定解析。
2. DNA 改变通过真实调控链改变发育结果。
3. DanioNet 控制鱼连续转向和推进。
4. Arena 产生可观察捕食和逃逸行为。
5. 两个亲本生成遗传合理的 offspring。
6. 多代仿真更新 allele/genotype/phenotype/fitness。
7. 同 seed 可复现。
8. research seeds 与 demo seed 分离。
9. 现场完全离线。
10. 数据图来自真实运行结果。

## 9. 最终叙事
EvoGenesis 不是把遗传算法套在一个现成神经网络外面，而是把遗传信息放到神经网络结构形成之前；网络的细胞组成、连接结构和时间尺度由同一套可遗传 developmental program 生成，生态任务再选择这些结构。

## 阅读问题（待确认）

> 逐份阅读本文时发现的未定义点，需与 04 / 05 / 07 / 16 对齐后确认。

1. **W 的合成方式与 connectome/DanioNet设计规范.md 动力学未对齐**：§4 写 `W = W^(0) + ΔW`（加性），但 connectome/DanioNet设计规范.md §3 动力学使用 `A_ij w_ij`，未说明 ΔW 以加性还是其他方式进入、是否受 Dale sign 约束。
2. **“四类 neural phenotype”未定义**：§7 Mendel Mode 输出“四类 neural phenotype”，但四类指什么、如何由 genotype 判定未写（G12）。
3. **epistasis 的实现状态需明确**：§5 将 epistasis 列为“optional”，而 connectome/DanioNet设计规范.md §9 已有 `w/o epistasis` 消融项；需确认 MVP 是否实现该机制，否则该消融无对象。
4. **MVP 第 5 条判据未定义**：§8“两个亲本生成遗传合理的 offspring”中“遗传合理”如何判定（例如 9:3:3:1 验证）未写。
5. **connectivity density 目标值未定**：§6 给范围 10%–20%，docs/参数总表.json / config 为单值 0.15，`b_A` 校准对齐到哪个目标未写（关联 G1）。
