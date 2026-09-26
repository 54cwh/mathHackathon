# DanioNet 设计依据：神经符号规则与时间常数 / 鱼类能量学

> 检索时间：2026-09-26　｜　配套机器可读文件：`research/reference/design-basis-neuro.json`
> 用途：为 DanioNet 的 Dale-like `sign(w)=−1 iff inhibitory`、τ_i 归一化、Arena 能量式与生长/代谢提供可核实的文献依据。
> 约定：**实测**＝论文一手测量；**汇编**＝常数汇编转述一手测量（未逐字核对原表）；**惯例**＝建模社区通行取值；**推断**＝本调研基于上述的换算。所有 URL/DOI 均在 2026-09-26 核实存在；引用数来自 OpenAlex，除非另注。

---

## 一句话结论

- **R4**：`sign(w)=−1 iff inhibitory` 的标准引用链是 **Dale 1935 → Eccles, Fatt & Koketsu 1954 → Strata & Harvey 1999**；计算模型中固定输出符号的做法有 Parisien et al. 2008 的构造性变换、Cornford et al. 2021 的 ICLR 证据与 Song et al. 2016 的 E/I-RNN 训练框架。该规则是主流近似，存在共释放反例，论文中必须标为建模简化。
- **R7**：多数皮层神经元膜时间常数约 **10–30 ms**（建模惯例取 **20 ms**），突触时间常数从 AMPA 的 ~2 ms 到 NMDA 的 ~100 ms、GABA_B 的 10² ms。项目 `hz=20`（dt=50 ms）下，`τ∈[1,10]` 步对应**物理时间常数 50–500 ms**；这作为“网络级整合时间常数”可辩护，但**不能称为单神经元膜时间常数**。能量式中 `C_base` 对应标准代谢、有依据；`C_move·v²` 若要对应水动力学应为 v³，作为经验活动代价项（b≈2）才成立。

---

## R4　神经符号与 E–I 平衡

### 4.1 Dale's principle 出处链

| 环节 | 文献 | 出处 | 性质 |
|---|---|---|---|
| 思想源头（讲座） | Dale, H. *Pharmacology and Nerve-Endings* (Walter Ernest Dixon Memorial Lecture) | Proc R Soc Med 1935;28(3):319–332．DOI [10.1177/003591573502800330](https://doi.org/10.1177/003591573502800330)，[PMC2205701](https://pmc.ncbi.nlm.nih.gov/articles/PMC2205701) | 讲座发表版 |
| 形式化提出 | Eccles, Fatt & Koketsu. *Cholinergic and inhibitory synapses in a pathway from motor-axon collaterals to motoneurones* | J Physiol 1954．DOI [10.1113/jphysiol.1954.sp005226](https://doi.org/10.1113/jphysiol.1954.sp005226) | 实测论文 |
| 权威短定义 | Strata & Harvey. *Dale's principle* | Brain Res Bull 1999;50(5-6):349–350．DOI [10.1016/S0361-9230(99)00100-8](https://doi.org/10.1016/S0361-9230(99)00100-8) | 短评 |
| 提出史澄清 | Otsuka. *Dale's principle and the one neuron-one transmitter concept* | Folia Pharmacol Jpn 1988．DOI [10.1254/fpj.91.335](https://doi.org/10.1254/fpj.91.335) | 综述 |

Otsuka 1988 原文记载：“Dale's principle was first proposed by Eccles in 1954…”，并给出 Eccles (1976) 定义：**同一神经元所有轴突分支释放相同递质**。注意 Dale 与 Eccles 都没有字面写下“one neuron-one transmitter”，该口号是后人的概括。

**标准引用建议**：概念用 Strata & Harvey 1999；历史提出用 Eccles 1954；若审稿追问原始思想，再引 Dale 1935。

### 4.2 `sign(w)=−1 iff inhibitory` 在计算模型中的依据

| 文献 | 关键内容 | 出处 |
|---|---|---|
| Parisien, Anderson & Eliasmith 2008 | 每个神经元的连接要么全兴奋、要么全抑制；给出前馈与循环网络都适用的**构造性变换**，把含负权重的模型转成同号模型 | Neural Comput 20(6):1473–1494．DOI [10.1162/neco.2008.07-06-295](https://doi.org/10.1162/neco.2008.07-06-295) |
| Cornford et al. 2021（ICLR） | 定义 Dale 约束即“每个神经元输出权重统一符号”；证明遵守后**不牺牲学习性能** | ICLR 2021．[OpenReview eU776ZYxEpz](https://openreview.net/forum?id=eU776ZYxEpz) |
| Barranca et al. 2022 | 直接研究 Dale's law 对 balanced E–I 网络动力学与决策的影响 | Front Neurosci．DOI [10.3389/fnins.2022.801847](https://doi.org/10.3389/fnins.2022.801847) |
| Song, Yang & Wang 2016 | E/I 单元分离的循环网络训练框架，可直接复用 | PLoS Comput Biol 12(2):e1004792．DOI [10.1371/journal.pcbi.1004792](https://doi.org/10.1371/journal.pcbi.1004792) |
| Eckstein et al. 2024 | 突触符号由 presynaptic 释放的递质决定，可从 EM 图像预测（87%/94%/91%） | Cell 2024．DOI [10.1016/j.cell.2024.03.016](https://doi.org/10.1016/j.cell.2024.03.016) |

**关键语义**：`sign(w_ij)` 由 **presynaptic 神经元类型** 决定，与 postsynaptic 类型无关。这正是 `RGCD数学模型.md §10` 规则的依据。

### 4.3 E–I balance

| 侧 | 文献 | 出处 |
|---|---|---|
| 理论 | Wilson & Cowan 1972，E/I 群体模型奠基 | DOI [10.1016/S0006-3495(72)86068-5](https://doi.org/10.1016/S0006-3495(72)86068-5) |
| 理论 | van Vreeswijk & Sompolinsky 1996，稀疏强连接 E–I 网络涌现平衡与混沌 | Science 274(5293):1724．DOI [10.1126/science.274.5293.1724](https://doi.org/10.1126/science.274.5293.1724) |
| 理论 | Vogels & Abbott 2005，稀疏随机 E–I 网络无需外部噪声即可稳定传播 | DOI [10.1523/JNEUROSCI.3508-05.2005](https://doi.org/10.1523/JNEUROSCI.3508-05.2005) |
| 理论 | Vogels et al. 2011，抑制可塑性维持 E–I 平衡 | Science 334(6062):1569．DOI [10.1126/science.1211095](https://doi.org/10.1126/science.1211095) |
| 实验 | Wehr & Zador 2003，听觉皮层 E/I 平衡塑造调谐 | Nature．DOI [10.1038/nature02116](https://doi.org/10.1038/nature02116) |
| 实验 | Haider et al. 2006，在体前额叶 E/I 动态平衡 | DOI [10.1523/JNEUROSCI.5297-05.2006](https://doi.org/10.1523/JNEUROSCI.5297-05.2006) |
| 实验 | Okun & Lampl 2008，单神经元尺度 E/I 瞬时相关 | Nat Neurosci．DOI [10.1038/nn.2105](https://doi.org/10.1038/nn.2105) |

### 4.4 风险

共释放是 Dale's principle 的明确反例：Saunders et al. 2015（DOI [10.7554/eLife.06412](https://doi.org/10.7554/eLife.06412)，胆碱能神经元同时释放 ACh 与 GABA）与 Svensson et al. 2019（DOI [10.3389/fncir.2018.00117](https://doi.org/10.3389/fncir.2018.00117)，共传递综述）。固定符号规则须写成近似，并显式声明失效后果（共释放神经元无法表达）。

---

## R7　时间常数与能量学

### 7.1 膜时间常数 τ_m

| 神经元 | τ_m | 性质 | 出处 |
|---|---|---|---|
| 多数神经元（汇总值） | **约 20 ms** | 汇编 | [UWaterloo CNRGlab](https://compneuro.uwaterloo.ca/research/constants-constraints/membrane-time-constant-tau_rc.html) |
| 新皮层 regular spiking | 20.2 ± 14.6 ms (n=12) | 汇编转实测 | McCormick et al. 1985．DOI [10.1152/jn.1985.54.4.782](https://doi.org/10.1152/jn.1985.54.4.782) |
| 新皮层 bursting | 16.6 ± 5.9 ms (n=9) | 汇编转实测 | 同上 |
| 新皮层 fast spiking | 11.9 ± 6.5 ms (n=15) | 汇编转实测 | 同上 |
| CA3 抑制性中间神经元 | 9.2 ± 3.2 ms (n=12) | 汇编转实测 | Miles 1990．DOI [10.1113/jphysiol.1990.sp018200](https://doi.org/10.1113/jphysiol.1990.sp018200) |
| 篮状细胞（BC） | 8.4 ± 0.7 ms（6.7–10.6） | 汇编转实测 | Geiger et al. 1997．DOI [10.1016/S0896-6273(00)80339-6](https://doi.org/10.1016/S0896-6273(00)80339-6) |
| CA3 锥体细胞 | 112 ms（离群值） | 汇编转实测 | Jonas et al. 1993．DOI [10.1113/jphysiol.1993.sp019965](https://doi.org/10.1113/jphysiol.1993.sp019965) |
| 人新皮层 L2/3 | 10–22 ms（16.5 ± 3.7, n=6） | 实测 | Eyal et al. 2016．[PMC5100995](https://pmc.ncbi.nlm.nih.gov/articles/PMC5100995) |
| **建模惯例** | **τ_m = 20 ms** | 惯例 | Brette et al. 2007．DOI [10.1007/s10827-007-0038-6](https://doi.org/10.1007/s10827-007-0038-6)；Brian 2 CUBA 示例逐行核实 |

**斑马鱼专门数据缺口**：未检索到斑马鱼普通神经元的 τ_m 实测。最接近的是 Mauthner 巨细胞（C-start 逃逸回路关键神经元）：输入电阻 107–210 kΩ、τ = **0.19–0.52 ms**（Machnik et al. 2018，DOI [10.1242/jeb.175588](https://doi.org/10.1242/jeb.175588)，物种为射水鱼；Korn & Faber 2005 综述 DOI [10.1016/j.neuron.2005.05.019](https://doi.org/10.1016/j.neuron.2005.05.019)）。这说明快速逃逸神经元 τ 可达亚毫秒，但**不能**用它代表斑马鱼普通神经元。

### 7.2 突触时间常数

| 受体 | 时间常数 | 性质 | 出处 |
|---|---|---|---|
| AMPA | τ ≈ **2 ms**（范围 ~1–10 ms） | 汇编转实测 | Hestrin et al. 1990．DOI [10.1113/jphysiol.1990.sp017980](https://doi.org/10.1113/jphysiol.1990.sp017980)；[汇编页](https://compneuro.uwaterloo.ca/research/constants-constraints/neurotransmitter-time-constants-pscs.html) |
| GABA_A | 典型 **5–10 ms** | 汇编转实测 | Salin & Prince 1996．DOI [10.1152/jn.1996.75.4.1573](https://doi.org/10.1152/jn.1996.75.4.1573)；Gupta et al. 2000．DOI [10.1126/science.287.5451.273](https://doi.org/10.1126/science.287.5451.273) |
| NMDA | rise ≈ 20 ms，decay τ ≈ **100 ms**（~50–150 ms） | 汇编转实测 | Hestrin et al. 1990；Destexhe et al. 1998 手册章节 |
| GABA_B | 约 **100–200 ms**（待核对） | 待核对 | Destexhe, Mainen & Sejnowski 1998．[章节 PDF](https://papers.cnl.salk.edu/PDFs/Kinetic%20Models%20of%20Synaptic%20Transmission%201998-3229.pdf) |

### 7.3 `τ∈[1,10]` 归一化可参照什么量级

项目更新式（`DanioNet设计规范.md §3`）：

```
h_i^{t+1} = (1 − 1/τ_i)·h_i^t + (1/τ_i)·φ( Σ_j A_ij w_ij h_j^t + U_i x_t + m_i H_t + b_i )
```

这是系数 `α=1/τ` 的离散指数滑动平均，等效时间常数为 **τ 步**。`configs/default_arena.yaml` 取 `hz=20`，故 `dt = 1/20 s = 50 ms`：

```
τ_phys = τ · dt = [1,10] × 50 ms = 50–500 ms
```

对照：

| 解释 | τ 对应的物理量级 | 是否成立 |
|---|---|---|
| 单神经元膜时间常数（皮层 10–30 ms） | 50–500 ms | **偏大**；20 Hz 下皮层 τ_m 只需约 0.2–0.6 步 |
| 网络/突触整合时间常数（NMDA ~100 ms、GABA_B ~100–200 ms、决策整合数百 ms） | 50–500 ms | **量级吻合**，可辩护 |

**建议**：在文档与论文中把 τ_i 明确标注为“网络级整合时间常数（50–500 ms）”，不要写“膜时间常数”。若确需对标膜时间常数，应在 20 Hz 下改用 τ∈[0.2, 0.6] 步，或提高 `sim_hz`。

边界注意：τ=1 时 `(1−1/τ)=0`，更新退化为瞬时无记忆（M_D 决策整合可用 Wong & Wang 2006，DOI [10.1523/JNEUROSCI.3733-05.2006](https://doi.org/10.1523/JNEUROSCI.3733-05.2006) 的数百 ms 作旁证）。

### 7.4 能量式 `E − (C_base + C_move·v²) + R_food`

| 项 | 对应生物学量 | 依据 | 判断 |
|---|---|---|---|
| `C_base` | 标准/维持代谢 | Brett 1964 外推 v=0 得标准代谢，活跃/标准代谢差约 10–12 倍（DOI [10.1139/f64-103](https://doi.org/10.1139/f64-103)）；West et al. 2001 维持项 ∝ m（DOI [10.1038/35098076](https://doi.org/10.1038/35098076)） | **有依据** |
| `C_move·v²` | 活动代价 | 阻力 `F_drag=½ρC_dA·v²`（∝v²）；克服阻力的机械功率 ∝**v³**（标准流体力学）；代谢率随速度的经验幂函数 `M∝v^b, b>1`；单位距离能耗 COT 呈 U 形、在最优速度最小 | **经验标度可辩护，非精确物理** |
| `R_food` | 摄食获得能量 C | 标准能量收支 `C = R + P + F + U`（摄食=呼吸+生长+排泄+排粪） | **有依据** |

关键区分：
- 代码是**每步**扣 `C_move·v²`。若语义是“功率/每步能量”，严格水动力学应为 **v³**；若语义是“单位距离能量”，则 **v²** 恰对应阻力（能量/距离 = 力）。
- 项目 `v` 已归一化到 [0,1]，`C_move·v²` 是无量纲活动代价曲线，因此它本质是**经验标度项**（很多呼吸计量研究拟合 b∈[2,3]）。论文应写明口径（每步 vs 每距离）并做 **v² vs v³ 消融**，不要直接声称水动力学等价。

出处：Brett 1964（同上）；Videler & Nolet 1990（DOI [10.1016/0300-9629(90)90155-L](https://doi.org/10.1016/0300-9629(90)90155-L)，COT U 形）；Schmidt-Nielsen 1972（DOI [10.1126/science.177.4045.222](https://doi.org/10.1126/science.177.4045.222)，COT 概念）；鱼游泳能量综述章节 R7-19（`fish locomotion`，给出“机械功率 ∝ v³、代谢率 y=ax^b, b>1”）。

### 7.5 生长 / biomass 与代谢

| 框架 | 内容 | 出处 |
|---|---|---|
| von Bertalanffy 生长函数（原始） | 生长 = 合成 − 分解 | Human Biology 1938;10(2):181–213．[JSTOR 41447359](https://www.jstor.org/stable/41447359)（无 DOI） |
| 异速生长普适模型 | `dB/dt = a·m^(3/4) − b·m` | West, Brown & Enquist 2001．DOI [10.1038/35098076](https://doi.org/10.1038/35098076) |
| VBGF 的生物能量学等价 | “VBGF is based on a bioenergetic expression of fish growth” | Essington, Kitchell & Walters 2001．DOI [10.1139/f01-151](https://doi.org/10.1139/f01-151) |
| 鱼类能量收支 | `C = R + P + F + U`；105 个模型 / 73 种鱼 | Deslauriers et al. 2017．DOI [10.1080/03632415.2017.1377558](https://doi.org/10.1080/03632415.2017.1377558) |
| 教科书 | 能量分配与参数化 | Jobling 1994, *Fish Bioenergetics*, Chapman & Hall, ISBN 0-412-58090-X |
| DEB 理论 | 摄取能量在维持/生长/成熟间分配的机制规则 | Kooijman, *DEB Theory* (3rd ed.)．DOI [10.1017/CBO9780511805400](https://doi.org/10.1017/CBO9780511805400) |

Arena 的 `R_food → biomass → size 增长` 可写成标准能量收支的特例：摄食增益进 P（生长），`C_base + C_move·v²` 对应 R（代谢支出）。

---

## 缺口与风险（须进一步验证）

1. **斑马鱼普通神经元 τ_m 无直接实测** → 不可声称 τ_i 是“斑马鱼膜时间常数”。现有 Mauthner 细胞数据（射水鱼，0.19–0.52 ms）仅作量级参照。
2. **σ 值未逐字核对原表** → 第 7.1/7.2 节多数 τ 值经 UWaterloo CNRGlab 二次汇编转述（非同行评审）。引用前须回查一手论文表格。建议至少核对 McCormick 1985、Hestrin 1990、Salin & Prince 1996 三篇。
3. **GABA_B 100–200 ms 未逐字核实** → 仅见 PDF 图示 10² ms 时间轴。引用前回查 Destexhe et al. 1998 正文。
4. **`C_move·v²` 的口径未在代码/文档声明** → 必须补“每步 vs 每距离”的声明，并做 v²/v³ 消融。
5. **Tucker 1970 无法解析** → OpenAlex 对该 DOI 报 Not found；COT 早期来源改用 Schmidt-Nielsen 1972。
6. **Dale 规则是近似** → 共释放反例已列，论文须标注失效后果。

## 建议的下一步

1. 在 `DanioNet设计规范.md` 补“τ_i 语义声明”（步长时间常数 ↔ 物理时间常数，τ=1 退化情形）。
2. 设计 `C_move·v²` vs `C_move·v³` 对照实验，报告生存步数与能量轨迹差异（对应赛题“原模型→改后模型→结果对比”）。
3. 用 Song et al. 2016 的 E/I 分离训练配方校验现有符号注入方式。
4. 回查一手表格后，把最终采用的数值写入 `paper/` 参考文献。
