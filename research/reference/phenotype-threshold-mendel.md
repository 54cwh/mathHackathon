# phenotype-threshold-mendel 调研摘要

> 配套数据：`research/reference/phenotype-threshold-mendel.json`。本文件为只读调研产物，**不修改任何上游文档或代码**。
> 检索时间：2026-09-26。目标：为 `genome/生物学与进化遗传学基础.md` §3/§6 的 G12（#2 dominance 阈值、#3 四类 neural phenotype）与 `EvoGenesis项目总纲.md` §8 MVP 判据 5（"遗传合理"）提供外部依据。

## 1. 结论速览

| 问题 | 结论 |
|---|---|
| "聚合表达 → 离散 phenotype" 有无依据 | **有**。liability-threshold 模型（Falconer 1965，1691 引）+ 定量遗传学教材（Falconer & Mackay 1996 Ch.18，明确支持多阈值→多表型类）+ 发育侧阈值范式（Kicheva & Briscoe 2023；Simsek & Özbudak 2022）|
| 四类 = 9:3:3:1 的四类 | **成立**，前提是"每基因完全显性 + 一个 functional allele 即越阈"。若不完全显性则不成立。|
| 四类绑定哪个架构参数 | **项目自定义**（无文献可背书）。推荐 N（neuron 数档）× H（τ 异质性档）的 2×2。|
| 阈值数值 | **无文献来源，待反解/需校准**，禁止编造。|
| 160 例能否算"验证" | **不能，只能算"演示"**。精确 χ² 检验 size=0.0491；对温和偏离功效仅 0.17–0.39；80% 功效对应 Cohen's w≈0.261。|

## 2. 推荐定义：四类 neural phenotype

**第一层（有文献支撑）**：四类首先是 9:3:3:1 的四个基因型类 `A_B_ / A_bb / aaB_ / aabb`，概率 `9/16, 3/16, 3/16, 1/16`。依据是独立分配加每基因完全显性的标准孟德尔结果（教科书级）。

**第二层（项目自定义）**：每类映射到一个架构档 = `(N 档, τ 异质档)`：

| 基因型类 | 理论概率 | 架构档 | 机器可读建议 token |
|---|---|---|---|
| `A_B_`  | 9/16 | 高 N × 高 τ 异质 | `rich_heterogeneous` |
| `A_bb`  | 3/16 | 高 N × 低 τ 异质 | `rich_homogeneous` |
| `aaB_`  | 3/16 | 低 N × 高 τ 异质 | `sparse_heterogeneous` |
| `aabb`  | 1/16 | 低 N × 低 τ 异质 | `sparse_homogeneous` |

其中 `N = |M|`（RGCD 产物 `(A,Z,τ,W⁰,M)` 的 active neuron mask，24–48），`τ ∈ [1,10]` 的异质性（如 `Var(τ)` 或 `max−min`）。

**判定规则（建议写入文档）**：

1. `E_A` = A 位点相关 motif 聚合表达（进入 GRN 后的标量），`E_B` 同理。
2. `high_N ⟺ E_A > θ_N`；`high_H ⟺ E_B > θ_H`。
3. `θ` 的取法：在校准集（如 ≥1000 个 offspring）上取 `A_` 与 `aa`（`B_` 与 `bb`）两类 liability 中位数的中点，或取使错分率最小的分位点。**数值待反解**。
4. 必须同时报告 **penetrance**：每个基因型类被分到目标架构档的比例。若噪声跨阈导致 penetrance < 1，则经验表型比例会偏离 9:3:3:1；此时把"基因型比例"与"表型穿透率"分开报告。

**文献支撑 vs 项目自定义**：
- 有支撑：连续潜变量经阈值产生离散类（Falconer 1965；Falconer & Mackay 1996 Ch.18 含三表型类/双阈值示例；Gianola & Foulley 1983）；连续 signaling/表达经阈值成为离散 cell fate（Kicheva & Briscoe 2023；Simsek & Özbudak 2022）；两位点独立 → 9:3:3:1（标准孟德尔）。
- 项目自定义（须声明为演示装置）：绑定 `N` 与 `τ` 这两个架构参数、具体阈值、四个 token 命名。

## 3. MVP"遗传合理"判据

建议预注册、两级合取：

1. **基因型级**：4 类计数对 9:3:3:1 做 χ² 拟合检验（`df=3`, `α=0.05`, 临界 `7.8147`），**不拒绝** → 判为"与 9:3:3:1 相容"。可加两个单位点 3:1 检验（`df=1`, 临界 `3.8415`）。
2. **架构级**：每基因型类映射到目标架构档的 penetrance ≥ 预注册下界（数值待校准后冻结）。
3. **措辞纪律**：160 例写"演示 / 与理论比例相容"，**不写"验证"**。要称"验证"须改用等价检验（TOST）并预先声明容忍界（所需 n 待反解），或增大 n。

## 4. n=160 的功效：是"演示"不是"验证"

口径：非中心 χ²，`1-β = Pr[χ²(df, ncp=n·w²) > χ²(1-α, df)]`（Abdul Rahman et al. 2025）。以下为本报告用 scipy 对 n=160 的**自算结果**（精确枚举 + Monte Carlo 复核），非文献直接数字。

4 类检验（H0=(9,3,3,1)/16, df=3, 临界 7.8147）：实际 size **0.0491**；80% 功效对应 **Cohen's w=0.261**、λ=10.90。

| 备择比例 | 精确功效 | 达 80% 功效所需 n |
|---|---|---|
| `10:2:3:1` | 0.385 | ≈393 |
| `9.5:3:3:0.5` | 0.192 | ≈628 |
| `p=(0.60,0.20,0.15,0.05)` | 0.172 | ≈818 |
| `11:3:1:1` | 0.992 | ≈98 |
| `2:1:1:0`（aabb 缺失） | 0.957（非中心近似） | ≈98 |

单位点 3:1（df=1, 临界 3.8415, 精确 size=0.0546）：vs `0.70:0.30` 功效 0.330；vs `2:1` 功效 0.682；vs `0.65:0.35` 功效 0.819；w80=0.221。

95% 置信区间半宽（正态近似）：`9/16 ± 0.077`（[0.486, 0.639]）、`3/16 ± 0.061`、`1/16 ± 0.038`（[0.025, 0.100]）。

**含义**：160 例能看出"缺一类/强偏离"，但对 `w≈0.11–0.17` 的温和偏离功效只有 0.17–0.39。因此 160 例是**演示规模**，"不拒绝"是很弱的证据，不能当作"验证了 9:3:3:1"。

## 5. 推荐分级

- **【推荐直接用】**
  - Falconer 1965 + Falconer & Mackay 1996 Ch.18 作为"连续 liability → 阈值 → 离散表型"的锚点。
  - Abdul Rahman et al. 2025 的非中心 χ² 口径 + `statsmodels.GofChisquarePower` 实现功效检查。
  - 把四类定义为 `A_B_/A_bb/aaB_/aabb`，每类映射一个 `(N 档, τ 异质档)` 架构档。
- **【仅作参考】**
  - OpenStax / TRU 开放教材（完全显性、dihybrid 9:3:3:1）：标准结论可引，但非同行评审。
  - Lee et al. 2025（现代 liability-threshold 应用）：旁证框架仍活跃，非 seminal。
  - `bvilhjal/ltpred`（GitHub）：概念参照，1 star、成熟度不足，不建议依赖。
- **【不建议】**
  - 任何未经校准就写死的阈值数值；任何把 160 例称为"验证"的表述。

## 6. 待反解 / 需进一步验证

1. `θ_N`、`θ_H` 的数值：无文献来源，须校准并标 `待反解`。
2. "绑定 N 与 τ"属项目设计选择，论文须声明为孟德尔演示装置。
3. Falconer & Mackay 第 18 章页码/版次：正式 BibTeX 前核对（本次依据 Internet Archive 第4版扫描）。
4. Simsek & Özbudak 2022 的 CC 具体版本未核。
5. 1/16 类期望计数仅 10（接近 χ² 的 ≥5 经验下限），正式报告建议同时给精确检验。
6. 本报告功效数值为自算，写入论文须标注口径并附脚本与随机种子。

## 7. 来源清单（含 DOI）

1. Falconer 1965 — `10.1111/j.1469-1809.1965.tb00500.x`（Annals of Human Genetics，peer-reviewed）。
2. Falconer & Mackay 1996 — *Introduction to Quantitative Genetics*, 4th ed, Ch.18 "Threshold characters", ISBN 9780582243026（教材）。
3. Gianola & Foulley 1983 — `10.1186/1297-9686-15-2-201`（Genetics Selection Evolution，OA）。
4. Kicheva & Briscoe 2023 — `10.1146/annurev-cellbio-020823-011522`（Annual Review of Cell and Developmental Biology）。
5. Simsek & Özbudak 2022 — `10.1098/rsob.220224`（Open Biology，OA）。
6. Abdul Rahman et al. 2025 — `10.1186/s12874-025-02584-4`（BMC Medical Research Methodology，CC BY-NC-ND）。
7. Lee et al. 2025 — `10.1038/s41588-025-02370-4`（Nature Genetics）。
8. OpenStax Biology 2e / TRU *Introduction to Genetics*（开放教材）。
9. `statsmodels.stats.power.GofChisquarePower`（库文档，BSD-3-Clause）。
10. `bvilhjal/ltpred`（GitHub，MIT，1 star）。
