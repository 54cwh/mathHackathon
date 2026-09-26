# R5 motif 表示与基因组尺度 — 调研摘要

- 检索日期：2026-09-26
- 主题：TF motif 标准表示（PWM/PSSM）vs 简化 Hamming 相似度；真实 motif 数量/长度量级；数字生物与人工调控网络（Avida / Banzhaf ARN）的 genome 长度惯例；对 EvoGenesis（128 bp / haplotype，8 motif，`a = 1 − d_Hamming` 后 TopKMean）的量级参照。
- 完整结构化数据（含每条 URL、DOI、被引数、许可、同行评审状态、notes）：`research/reference/design-basis-genome.json`（23 条 items，4 条 conclusions）。

> 口径说明：被引数与 OA 状态取自 OpenAlex（2026-09-26）；JASPAR 计数取自官方 REST API（curl 于 2026-09-26）；未核实项一律置 `null` 并在 JSON 的 `notes` 说明。重复主题无（`research/reference/` 下此前无同类文件，本次为新建）。

---

## 1. 转录因子结合 motif 的标准表示：PWM / PSSM

| 事实 | 数值 / 结论 | 出处 |
|---|---|---|
| 标准表示 | position weight matrix (PWM) / PSSM，逐位加性 log-odds 打分 | Stormo 2000, *Bioinformatics*, DOI 10.1093/bioinformatics/16.1.16，被引 1558 |
| 物理依据 | 结合自由能近似为各位点独立贡献之和 | Berg & von Hippel 1987, *J. Mol. Biol.*, DOI 10.1016/0022-2836(87)90354-8，被引 775 |
| 已知缺陷 | PWM 假设 motif 各位点独立，通常产生高假阳性 | Bi et al. 2011, *PLoS ONE*, DOI 10.1371/journal.pone.0024210 |
| 反面证据 | PWM 对非规范结合仍具足够预测力 | Boytsov et al. 2022, PMC9237556（同行评审） |

**一句结论**：PWM 是领域标准，Hamming 相似度可视为它的极端退化形式（每列 one-hot、失配等权、无背景校正），因此可作为简化/消融基线，但不能声称与 PWM 等价，也不自带 PWM 的生物学解释力。

---

## 2. 真实 motif 的数量量级与长度量级

| 指标 | 数值 | 出处 |
|---|---|---|
| JASPAR CORE 当前矩阵数 | **2633**（latest 版本；vertebrates 1019；UNVALIDATED 1031） | JASPAR REST API 实测 2026-09-26 |
| JASPAR 增量 | 2026 +306（+12%）；2024 +329（+20%）；2022 +341（+19%）；2020 +245（+18%）；2018 +322（+30%） | JASPAR 2026/2024/2022/2020/2018 论文（NAR，同行评审） |
| CIS-BP 直接测定 | **≈1892 motif / 1878 TF**（CIS-BP 2.0）；原始论文测定 >1000 TF、54 个 DBD 类、131 物种 | footprintDB 聚合页；Weirauch et al. 2014, *Cell*, 被引 2082 |
| 人类 TF 总数 | **1639**，约三分之二有 motif | Lambert et al. 2018, *Cell*, 被引 3744 |
| motif 长度 | **6–12 bp**（典型）；文献另给 6–20 bp 上界 | Genome Research 2022（DOI 待核）；Factorbook 预印本 2021 |

**一句结论**：真实 TF motif 数量为 **10³ 量级**（JASPAR ≈2.6×10³、CIS-BP ≈1.9×10³），长度 **6–12 bp**，单个真核生物约有 10³ 个 TF。8 个 motif 比真实规模低约两个数量级；平均 16 bp/motif 的长度则落在真实区间内。

---

## 3. 数字生物 / 人工调控网络的 genome 长度惯例

| 系统 | genome 表示与长度 | 出处 |
|---|---|---|
| Avida-ED | genome 恒为 **50 条指令**（instruction），指令集 26 | MSU Avida-ED Lab Book / User Manual（官方文档） |
| Avida（研究用） | 祖先 genome 可用 **20 条指令**，跨突变率演化基因组大小 | Sci Rep 2016, DOI 10.1038/srep25786 |
| Avida（形式化） | genome = 线性指令串，虚拟 CPU 逐条执行 | Sci Data 2023, DOI 10.1038/s41597-023-02514-3 |
| Banzhaf ARN | genome 为 bit string / 32-bit 整数序列；promoter=`XYZ01010101`（32 bit），gene=**160 bit**（5×32），protein=32 bit | Cussat-Blanc, Harrington & Banzhaf 2019, *Artificial Life*, DOI 10.1162/artl_a_00267（CC-BY-NC） |
| Banzhaf ARN 长度量级 | 起点随机 **32-bit**，经全基因组复制 Lg = 2¹² × 32 = **131,072 bit**；另例 10 次复制 = 32×2¹⁰ = 32,768 | Kuo, Banzhaf & Leier 2006, *BioSystems*, DOI 10.1016/j.biosystems.2006.01.004；GECCO 2013 PDF（作者待核） |

**一句结论**：数字生物的 genome 尺度是 **10¹–10⁵ 个符号**（Avida 20–100 条指令；Banzhaf ARN 32 bit 起、可达 1.3×10⁵ bit），128 bp/8 motif 与 Avida 同量级、处于 Banzhaf ARN 的最短端，是合理的"数字生物尺度"，但不是真实生物学尺度。

---

## 4. 对 EvoGenesis 设计的两条判定

### 4.1 128 bp / 8 motif 能否找到量级参照？

**能，但仅限数字生物方向。**
- 支持：Avida-ED 固定 50 指令、Avida 研究用祖先 20 指令、Banzhaf ARN 32-bit 种子 —— 均与 128 符号同处 10¹–10² 量级；每个 motif 平均 16 bp 也在真实 motif 长度 6–12 bp 区间内。
- 不支持：真实 TF motif 数（10³）和真核 genome 长度（10⁶–10⁹ bp）都比 128 bp/8 motif 高 2 个数量级以上。
- 建议：论文中把 128 bp/8 motif 明确标注为 **A-life / 数字生物尺度**，引 Avida-ED 50 指令与 Banzhaf ARN 32-bit 种子作先例，不用真实基因组为其数量背书。

### 4.2 Hamming + TopKMean 相对 PWM 的简化是否可辩护？

**可辩护为"极端简化 / 消融基线"，不可辩护为"等价于 PWM"。**
- `a = 1 − d_Hamming(motif, window)` 等价于每列 one-hot、失配等权的退化 PWM；TopKMean 是对窗口匹配度的聚合。相对标准 PWM 丢失：碱基特异权重、背景（GC）校正、位点依赖。
- 标准 PWM 本身也有"位点独立、假阳性高"的问题（PLOS ONE 2011）；可引 Boytsov 2022 说明 PWM 在多数情形仍够用。
- 要求：项目若采用 Hamming+TopKMean，必须在论文中显式声明为简化，并至少给出 **Hamming vs PWM/加权打分** 的对照或消融，否则"生物学合理性"结论无证据支撑。

---

## 三级结论（推荐直接用 / 仅作参考 / 不建议）

1. **推荐直接用**：PWM/PSSM 事实基线与 JASPAR/CIS-BP 数量、6–12 bp 长度区间，作为设计依据的"真实对照"。
2. **仅作参考**：Hamming+TopKMean —— 只能作简化/消融基线，须配对照实验。
3. **不建议**：用真实生物学为 128 bp/8 motif 的规模背书；该规模只有数字生物先例。

### 待核实风险点
- JASPAR 具体 CC 许可版本、Avida-ED / Banzhaf 专著章节 license 未核，再分发前须确认。
- JASPAR 2018 总量 1404 来自非同行评审博客，引用请改引论文或版本统计。
- Genome Research 2022 的 DOI 由 PDF 文件名推断；GECCO 2013 PDF 作者未逐字确认 —— 正式引用前须核对。
- CIS-BP 计数有 1892（直接测定）与 1491/165030（含推断）两种口径，勿混用。
