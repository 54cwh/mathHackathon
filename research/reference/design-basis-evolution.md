# EvoGenesis 演化参数设计依据（突变率 / 选择 / 交叉）

> 检索时间：2026-09-26 ｜ 对应 JSON：`research/reference/design-basis-evolution.json`
> 范围：只做文献与开源实现的核实，不改动代码。所有数值均附来源；找不到的置 `null` 并说明。
> 项目现状（只读核对）：二倍体 2 对染色体、单倍型 128 bp；`μ=0.001` per base per gamete（每配子期望突变 = 256 bp × μ = 0.256）；`softmax p_i ∝ exp(β F_i)`，β=3；`crossover_probability_per_chromosome=0.5`；`composite_fitness=0.35·survival+0.25·prey_capture+0.20·escape_success+0.20·energy_efficiency`（权重和=1，但代码未显式归一化分量）。

---

## R1 突变率：真实生物量级 vs 数字生物惯例

### R1.1 斑马鱼 / 脊椎动物 germline 碱基替换率（per base per generation）

| 对象 | 数值（/site/generation） | 出处 | 类型/评审 |
|---|---|---|---|
| 鱼类平均 | **5.97×10⁻⁹**（95% CI 4.39×10⁻⁹–7.55×10⁻⁹） | Bergeron et al. 2023, *Nature* 615:285–291，DOI [10.1038/s41586-023-05752-y](https://doi.org/10.1038/s41586-023-05752-y) | paper / peer-reviewed |
| 鱼纲（fish clade root） | **5.55×10⁻⁹** | Wang & Obbard 2023, *Evolution Letters* 7(4):216–226，DOI [10.1093/evlett/qrad027](https://doi.org/10.1093/evlett/qrad027) | paper / peer-reviewed |
| 大西洋鲱鱼（最低值） | **2.0×10⁻⁹** | Feng et al. 2017, *eLife* 6:e23907，DOI [10.7554/eLife.23907](https://doi.org/10.7554/eLife.23907) | paper / peer-reviewed |
| 鲤科银鲫 *C. gibelio*（斑马鱼同科） | **8.88×10⁻⁹** | Wang et al. 2022, *Nature Ecology & Evolution*，DOI [10.1038/s41559-022-01813-z](https://doi.org/10.1038/s41559-022-01813-z) | paper / peer-reviewed |
| 全脊椎动物跨度 | 约 **10⁻¹¹ – 10⁻⁷**，跨 40 倍 | Bergeron et al. 2023（同上） | paper / peer-reviewed |
| 真核生物跨度 | 约 **0.01×10⁻⁹ – 55.58×10⁻⁹**（>5000 倍） | Wang & Obbard 2023（同上） | paper / peer-reviewed |

**斑马鱼（Danio rerio）专属直接估计：未找到（null）。** Wang & Obbard 2023 明确指出鱼类直接估计稀缺（纳入 Bergeron 2023 前仅 4 项鱼类研究），两栖类完全缺失；Bergeron 2023 的 68 个物种主图清单中未见 *Danio rerio*。本报告不杜撰斑马鱼专属数值，改用鲤科近缘 *C. gibelio* 与鱼类均值作为代理。注意 *C. gibelio* 为多倍体，生殖生物学与二倍体斑马鱼不同。

### R1.2 数字生物 / 自复制程序的 per-site 突变率

| 系统 | 默认 per-site 突变率 | 出处 | 类型/评审 |
|---|---|---|---|
| Avida（研究版） | **0.0075**（`COPY_MUT_PROB`，'Substitution rate (per copy)'；另有 indel `DIVIDE_INS_PROB=0.05`、`DIVIDE_DEL_PROB=0.05`） | 源码 [devosoft/avida `cAvidaConfig.h`](https://github.com/devosoft/avida/blob/master/avida-core/source/main/cAvidaConfig.h) / [默认配置](https://github.com/devosoft/avida/blob/master/avida-core/support/config/avida.cfg)；stars=669 | repo / 非同行评审（LGPL-3.0） |
| Avida-ED（教学） | **0.02（2.0%）**，部分版本 0.03 | [Avida-ED Lab Book](https://avida-ed.msu.edu/files/curricula/LabBook/Avida-ED_LabBook.pdf)，官网 | other / 非同行评审 |

### R1.3 结论：μ=0.001 是否合理？

- **相对真实生物值**：μ=0.001 比鱼类真实 per-base per-generation 率高 **约 1.1×10⁵ – 5×10⁵ 倍**：
  - 0.001 / 5.97×10⁻⁹ ≈ **1.7×10⁵**
  - 0.001 / 5.55×10⁻⁹ ≈ **1.8×10⁵**
  - 0.001 / 8.88×10⁻⁹ ≈ **1.1×10⁵**
  - 0.001 / 2.0×10⁻⁹ = **5×10⁵**
- **作为计算速率**：属常见惯例。De Jong 1975 的 GA 变异率 **pm=0.001** 与本值完全相同；Avida 默认 0.0075（同量级，高约 7.5 倍），Avida-ED 默认 2%（高约 20 倍）。
- **判定**：作为“生物参数”**不建议**；作为“计算速率”**推荐直接用**，但必须在文档中标注为抽象参数而非生物事实。若追求生物可信，可将每碱基率改到约 **5×10⁻⁹**（鱼均值）。
- 口径提醒：本项目 μ 是 per base per gamete，每配子 256 bp 的期望突变为 **0.256 个**；描述时不要与“每条染色体/每个个体”的突变概率混淆。

---

## R2 选择强度与交叉概率

### R2.1 三类选择方案的比较

| 方案 | 选择压力由什么决定 | 是否依赖适应度尺度 | 关键出处 |
|---|---|---|---|
| **softmax / 玻尔兹曼** `p_i ∝ exp(β F_i)` | 温度 β 与适应度分布共同决定 | **依赖**：`F→cF` 等价于 `β→cβ`；Goldberg 1990 的伪代码用 `logistic(Δf/temperature)`，温度直接与适应度差值比较 | Goldberg 1990, *Complex Systems* 4(4):445–460，[存档 PDF](https://content.wolfram.com/sites/13/2018/02/04-4-5.pdf) |
| **排名选择**（rank） | 排名顺序，选择压力由排名分布设定 | **不依赖**线性缩放（单调变换不变） | Whitley 1989, ICGA；Blickle & Thiele 1996, *Evolutionary Computation* 4(4):361–394，DOI [10.1162/evco.1996.4.4.361](https://doi.org/10.1162/evco.1996.4.4.361) |
| **锦标赛选择**（tournament） | 锦标赛规模 k（k 越大压力越高） | **不依赖**适应度尺度 | Miller & Goldberg 1995, *Complex Systems* 9(3):193–212；Blickle & Thiele 1996（二元锦标赛 ≈ 线性排名） |

补充：比例/softmax 型选择对适应度方差敏感，Goldberg & Deb 1991 因此提出 **sigma scaling** 等适应度缩放方法来控制选择压力、避免早熟收敛（DOI [10.1016/b978-0-08-050684-5.50008-2](https://doi.org/10.1016/b978-0-08-050684-5.50008-2)）。Eiben & Smith《Introduction to Evolutionary Computing》(2015, DOI [10.1007/978-3-662-44874-8](https://doi.org/10.1007/978-3-662-44874-8)) 将“选择压力需相对适应度尺度定义”写入教科书。

**结论：β=3 在适应度未归一化时没有确定意义。**
- 本项目 `composite_fitness` 是四分量加权和（权重和=1），但 `metrics.py` 与 `evolution.py` 均未显式归一化各分量。
- **若**各分量∈[0,1]，则 F∈[0,1]、βF∈[0,3]，最优/最差选择比 ≤ e³ ≈ **20:1**，属温和、可用的选择压力。
- **若**分量未归一化（如 counts、能量绝对量），β=3 的实际压力不可预测，可能过强（接近贪心）或过弱（接近均匀）。
- 判定：**仅作参考 / 需进一步验证**。建议任选其一：①在 `composite_fitness` 内显式归一化每个分量到 [0,1]；②改用排名/锦标赛选择（对尺度不敏感）；③用种群内 z-score/min-max 标准化后再 softmax，并把 β 解释为“标准化适应度的温度”。

### R2.2 交叉概率推荐值

| 出处 | 推荐 / 常见值 | 类型/评审 |
|---|---|---|
| Srinivas & Patnaik 1994, *IEEE TSMC* 24(4):656–667，DOI [10.1109/21.286385](https://doi.org/10.1109/21.286385) | 原文：**"Typical values of pc are in the range 0.5–1.0"** | paper / peer-reviewed（一手） |
| De Jong 1975（博士论文）| 种群 50、**单点交叉 pc=0.60**、pm=0.001、精英保留 | other / 学位论文，经二手来源交叉印证（[Georgia Tech EISLab](https://www.eislab.gatech.edu/people/scholand/gapara.htm)、[NIST 文档](https://www.nist.gov/document/p992-singlepdf)） |
| Grefenstette 1986, *IEEE TSMC* 16(1):122–128，DOI [10.1109/tsmc.1986.289288](https://doi.org/10.1109/tsmc.1986.289288) | 种群 30、**两点交叉 pc=0.9**、pm=0.01 | paper / peer-reviewed；0.9/0.01 数值来自二手来源（EISLab、Hassanat 2019），原论文表格未直接核验 |
| Hassanat et al. 2019, *Information* 10(12):390，DOI [10.3390/info10120390](https://doi.org/10.3390/info10120390) | 多数文献交叉率 **0.5–0.9**；部分建议高交叉 **80–95%** 配低变异 0.1–1% | paper / peer-reviewed 综述（二次） |

**结论：crossover=0.5/染色体 不算偏离惯例，但需澄清口径。**
- 0.5 恰好落在 Srinivas & Patnaik 给出的典型区间 **0.5–1.0** 的下端；De Jong 用 0.6、Grefenstette 用 0.9，故 0.5 偏保守（更低破坏率），但完全可接受。
- 关键口径：本项目是“**每染色体**”0.5。2 条染色体时，每配子至少发生一次交叉的概率 = 1 − 0.5² = **0.75**，落在常见区间内。
- **风险点**：若染色体数增加（例如模拟斑马鱼 25 对染色体），每配子至少一次交叉概率 = 1 − 0.5²⁵ ≈ 1，交叉将接近必然发生。建议把参数语义统一为“每配子/每个体交叉概率”或在文档中显式声明“每染色体”口径。
- 判定：**推荐直接用（但须说明口径）**。

---

## 未找到 / 待人工复核

1. **未找到**斑马鱼（*Danio rerio*）专属的 pedigree per-base germline 突变率直接估计；用同科鲤科 *C. gibelio* 8.88×10⁻⁹ 与鱼类均值代理，已注明。
2. **待复核**：Grefenstette 1986 的 pc=0.9/pm=0.01 与 De Jong 1975 的 pc=0.60/pm=0.001 均来自二手来源交叉印证，原论文/学位论文正文表格未在本轮直接核验；引用时建议标注“经二手汇总”。
3. **待验证**：`composite_fitness` 四个分量的实际取值范围未在代码中约束；这是判断 β=3 是否合适的先决条件。

## 一句话总纲

- **μ=0.001**：作为生物突变率高了约 10⁵–5×10⁵ 倍，但作为数字生物/GA 的计算速率属常见惯例 → 保留但标注为抽象。
- **β=3**：softmax 温度与适应度尺度绑定；只有归一化后 β=3 才有确定含义（若 F∈[0,1] 则选择比约 20:1，温和可用）。
- **crossover=0.5/染色体**：落在典型 0.5–1.0 下端，2 条染色体下每配子交叉概率 0.75，可用；需统一“每染色体 vs 每配子”口径。
