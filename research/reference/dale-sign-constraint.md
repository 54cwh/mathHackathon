# ΔW 是否应受 Dale sign 约束：文献调研与推荐

> 检索时间：2026-09-26　｜　配套机器可读文件：`research/reference/dale-sign-constraint.json`
> 服务对象：`connectome/DanioNet设计规范.md` §3、§6 与 `EvoGenesis项目总纲.md` §4 的开放问题，即行为克隆产生的 ΔW 是否强制 `sign(w_ij)=sign(w⁰_ij)`。
> 核实约定：所有条目均于 2026-09-26 经 OpenAlex DOI 解析或出版方页面确认存在；引用数来自 OpenAlex，star 数来自 GitHub `gh` CLI。DOI 未核实者不收录。分级：`推荐直接用` / `仅作参考` / `不建议`。

---

## 一句话结论

**推荐默认采用硬符号约束：BC 只学习幅度，保持 `sign(w_ij)=sign(w⁰_ij)`。** 生物学上符号由突触前类型决定，学习改变强度而不改变递质身份；工程上硬约束可训练且已有多种追平无约束性能的配方。由于『固定符号的发育 W⁰ + 受约束残差 ΔW』这一确切设定未见专门文献，该结论属相邻设定外推，须由本项目消融实证，当前应标 `草案待确认`。

---

## 一、核心文献（按角色分组）

### 1. 符号约束下的 RNN 训练方法（推荐直接用）

| 文献 | 出处 | 年份 | DOI | 同行评审 | 关键结论 |
|---|---|---|---|---|---|
| Song, Yang & Wang | PLoS Comput Biol 12(2):e1004792 | 2016 | [10.1371/journal.pcbi.1004792](https://doi.org/10.1371/journal.pcbi.1004792) | 是 | 直接训练『E 单元只出正权重、I 单元只出负权重』的网络，受限与无约束网络的 psychometric function 可比 |
| Cornford et al. (DANN) | ICLR 2021 | 2021 | preprint [10.1101/2020.11.02.364968](https://doi.org/10.1101/2020.11.02.364968) | 是（会议论文无 DOI） | 朴素 E/I 分群会损害学习；用初始化 + 基于 Fisher 信息的抑制侧更新缩放可不牺牲性能 |
| Li, Cornford, Ghosh & Richards | NeurIPS 2023 | 2023 | preprint [10.1101/2023.06.28.546924](https://doi.org/10.1101/2023.06.28.546924) | 是 | 从权重谱角度解释：结构正确的 Dale 网络可学得好，甚至更好 |
| Balwani, Wang, Najafi & Choi (Dale's backprop) | Science Advances | 2025 | [10.1126/sciadv.adw4970](https://doi.org/10.1126/sciadv.adw4970) | 是 | 硬加 Dale 符号与稀疏结构约束并给出线性收敛保证，受限模型性能与无约束相当 |
| Parisien, Anderson & Eliasmith | Neural Computation 20(6) | 2008 | [10.1162/neco.2008.07-06-295](https://doi.org/10.1162/neco.2008.07-06-295) | 是 | 构造性变换把含负权重模型转成全同号模型，函数与动力学近似保持 |
| Ingrosso & Abbott | PLoS ONE 14(8):e0220547 | 2019 | [10.1371/journal.pone.0220547](https://doi.org/10.1371/journal.pone.0220547) | 是 | target-based 目标 + 在线约束优化，构建遵守 Dale's law 且 E–I 平衡的网络 |
| Barranca, Bhuiyan, Sundgren & Xing | Front Neurosci | 2022 | [10.3389/fnins.2022.801847](https://doi.org/10.3389/fnins.2022.801847) | 是 | Dale's law 对平衡网络动力学与决策有实质功能影响 |
| Jarne & Caruso | Cognitive Neurodynamics | 2023 | [10.1007/s11571-023-09956-w](https://doi.org/10.1007/s11571-023-09956-w) | 是 | 给出 E/I 约束训练框架并刻画权重谱；指出批量训练循环网络可能不稳定 |

### 2. Dale 原理的生物学依据（推荐直接用）

| 文献 | 出处 | 年份 | DOI | 同行评审 | 关键结论 |
|---|---|---|---|---|---|
| Eccles, Fatt & Koketsu | J Physiol | 1954 | [10.1113/jphysiol.1954.sp005226](https://doi.org/10.1113/jphysiol.1954.sp005226) | 是 | Dale's principle 形式化：同一神经元各轴突分支释放相同递质 |
| Strata & Harvey | Brain Res Bull 50(5-6) | 1999 | [10.1016/S0361-9230(99)00100-8](https://doi.org/10.1016/S0361-9230(99)00100-8) | 是 | 权威短定义，概念引用的标准来源 |
| Eckstein et al. | Cell | 2024 | [10.1016/j.cell.2024.03.016](https://doi.org/10.1016/j.cell.2024.03.016) | 是 | 突触符号由突触前递质决定，EM 图像预测准确率 87%（单突触）/94%（神经元） |
| Saunders, Granger & Sabatini | eLife | 2015 | [10.7554/eLife.06412](https://doi.org/10.7554/eLife.06412) | 是 | 共释放反例：胆碱能神经元同时释放 ACh 与 GABA |
| Svensson et al. | Front Neural Circuits | 2019 | [10.3389/fncir.2018.00117](https://doi.org/10.3389/fncir.2018.00117) | 是 | 神经共传递综述，单一符号假设的边界 |

### 3. E–I 平衡（推荐直接用；用于神经科学侧表述）

| 文献 | 出处 | 年份 | DOI | 同行评审 |
|---|---|---|---|---|
| Wilson & Cowan | Biophys J 12(1) | 1972 | [10.1016/S0006-3495(72)86068-5](https://doi.org/10.1016/S0006-3495(72)86068-5) | 是 |
| van Vreeswijk & Sompolinsky | Science 274(5293) | 1996 | [10.1126/science.274.5293.1724](https://doi.org/10.1126/science.274.5293.1724) | 是 |
| Vogels & Abbott | J Neurosci 25(46) | 2005 | [10.1523/JNEUROSCI.3508-05.2005](https://doi.org/10.1523/JNEUROSCI.3508-05.2005) | 是 |
| Vogels, Sprekeler, Zenke, Clopath & Gerstner | Science 334(6062) | 2011 | [10.1126/science.1211095](https://doi.org/10.1126/science.1211095) | 是 |
| Hennequin, Agnes & Vogels | Annu Rev Neurosci | 2017 | [10.1146/annurev-neuro-072116-031005](https://doi.org/10.1146/annurev-neuro-072116-031005) | 是 |
| Brunel | J Comput Neurosci 8(3) | 2000 | [10.1023/A:1008925309027](https://doi.org/10.1023/A:1008925309027) | 是 |

### 4. 对照与背景（仅作参考 / 不建议作为符号约束依据）

- **Sussillo & Abbott 2009**，*Generating Coherent Patterns of Activity from Chaotic Neural Networks*，Neuron，DOI [10.1016/j.neuron.2009.07.018](https://doi.org/10.1016/j.neuron.2009.07.018)。FORCE 训练随机循环网络，**不施加 E/I 符号约束**。它只能作为『无约束训练』的对照范式，不可用于支持任何符号约束结论。
- **Rajan & Abbott 2006**，PRL 97:188104，DOI [10.1103/PhysRevLett.97.188104](https://doi.org/10.1103/PhysRevLett.97.188104)。E/I 约束下权重矩阵特征值谱与经典随机矩阵结果不同，间接支撑『符号结构决定动力学谱与稳定性』。
- **Kim, Li & Sejnowski 2019**，PNAS 116(45)，DOI [10.1073/pnas.1905926116](https://doi.org/10.1073/pnas.1905926116)。先训练连续 RNN 再构造脉冲 RNN，流程相似但约束加在映射阶段。

### 5. 可运行实现

| 仓库 | 许可 | star（2026-09-26） | 说明 |
|---|---|---|---|
| [gyyang/nn-brain](https://github.com/gyyang/nn-brain) | MIT | 245 | Song 2016 官方实现，含 `EI_RNN.ipynb`；纯 numpy，可离线，与 py/uv 生态兼容 |
| [HChoiLab/biologicalRNNs](https://github.com/HChoiLab/biologicalRNNs) | MIT | 2 | Balwani 2025 Dale's backprop 官方实现；star 少、维护新，仅作方法参考 |

---

## 二、推荐做法（可直接落地）

**推荐：硬约束，BC 只更新幅度、符号固定。**

1. **参数化**：`w_ij = s_ij · softplus(θ_ij)`，其中 `s_ij = sign(w⁰_ij)` 由突触前类型给定，`θ_ij` 为 BC 学习的标量；初始化 `θ_ij = softplus⁻¹(|w⁰_ij|)`，使训练起点严格等于发育权重。该式天然保证 `sign(w_ij)=s_ij`，且 `Δw_ij = w_ij − w⁰_ij` 自动满足符号约束。
2. **备选（改动更小、较差）**：保留加性 ΔW，每次更新后把权重投影到允许半空间，即 `w ← sign(w⁰)·max(|w⁰+ΔW|, 0)`。缺点是不连续、可能把权重压到 0，仅在无法改参数化时使用。
3. **文档状态**：上述两项都应在 connectome / learning 模块文档中标注 `草案待确认`，经消融确认后转 `已定稿`。当前 `DanioNet设计规范.md` §3 与 `EvoGenesis项目总纲.md` §4 均写『待定』，属未认领项，需回写。

**理由**：

- 生物学：Dale's principle 使符号成为突触前细胞类型的属性（Eccles 1954；Strata & Harvey 1999；Eckstein 2024），突触强度可塑性改变量级而非递质身份。W⁰ 的符号已被定义为突触前类型的编码，ΔW 反号等于让学习推翻该结构。
- 工程：『符号约束必然损害学习』是**朴素 E/I 分群**的结论，而非 Dale 约束本身不可避免的结论。Song 2016 在硬约束下即取得可比性能；Cornford 2021、Li 2023、Balwani 2025 给出了使受限网络追平甚至更优的技术路径。
- 项目自身：BC 是在接近解的发育 W⁰ 上做残差学习，解空间损失较小；保持符号可维持 W⁰ 与 ΔW 语义一致，避免『出生时符号由类型决定、学习后变号』的不可解释情形，也便于设置可比 baseline。

---

## 三、对比证据（满足『原模型→改后模型→结果对比』）

必须做两组对照，同数据、同预算、给方差或重复次数：

| 组 | 设定 | 观察量 |
|---|---|---|
| A（默认） | Dale 约束 BC，`sign(w)` 固定 | BC 损失、任务指标（ω/v MSE、逃逸成功率、捕食率）、谱半径、活动饱和率 |
| B（对照） | 无符号约束 BC，ΔW 无界 | 同上，外加 `flip_rate = |{ij: sign(w⁰_ij+Δw_ij) ≠ sign(w⁰_ij)}| / N_syn` |

判据：若 B 相对 A 无显著优势，保持 A，并把 Dale 约束写成设计选择；若 B 显著更优，如实报告并考虑 Cornford 2021 的抑制侧缩放或 Li 2023 的结构化 E/I 方案，不得默认静默切换到无约束。

---

## 四、文献分歧与风险（诚实标注）

- **分歧**：Cornford 2021、Li 2023、Balwani 2025 承认 E/I 符号约束会损害朴素实现，需专门技术才追平；Song 2016 在硬约束下即可获得可比性能。二者不矛盾，差异在实现方式（E/I 比例、初始化、参数化、优化器）。对本项目而言，约束是固定在 W⁰ 上的残差而非从零训练，更接近 Song 2016 的可控情形，故建议先做硬约束 A，仅在其明显不足时才引入缓解技术。
- **风险 1（未覆盖设定）**：未检索到专门研究『固定符号的发育 W⁰ + 受符号约束的残差 ΔW』的文献，结论为相邻设定外推，须由本项目消融实证。
- **风险 2（简化声明）**：Dale's principle 有共释放反例，固定符号规则在论文中必须声明为建模简化并写明失效后果。
- **风险 3（收敛稳定性）**：符号约束对收敛的影响在本项目规模（48 nodes、稀疏）下无直接证据；Jarne & Caruso 2023 指出批量训练循环网络可能不稳定，属需监控项。BC 并非真实突触可塑性，『生物学上符号不能变』是类比，工程理由仍是可解释性与 baseline 可比性。

---

## 五、与项目文献库的交叉核对

任务描述中的『[bib#11] / 神经科学侧对 E–I 平衡』对应关系**不成立**。`research/notes/bibliography.md` 的 [bib#11] 是 Zhao et al. 2026 Nature，*A thalamus-brainstem attractor network drives history-biased decisions*（DOI [10.1038/s41586-026-10623-3](https://doi.org/10.1038/s41586-026-10623-3)，2026-06-10，经 OpenAlex 核实），主题为斑马鱼历史偏倚决策，与 E–I 平衡无关。

当前 bibliography.md **没有任何 E–I 平衡条目**。若论文使用 E–I 平衡表述，需新增 Wilson & Cowan 1972、van Vreeswijk & Sompolinsky 1996、Vogels et al. 2011 作为设计依据条目（依据分级见 `docs/设计依据审计.md`）。

---

## 六、分级结论

- **推荐直接用**：Song 2016 硬约束训练配方与 `gyyang/nn-brain`；Parisien 2008 构造性变换；Cornford 2021 / Li 2023 / Balwani 2025 的约束保持技术；Eccles 1954 + Strata & Harvey 1999 + Eckstein 2024 的 Dale 生物学链；van Vreeswijk & Sompolinsky 1996 + Vogels et al. 2011 的 E–I 平衡。
- **仅作参考**：Rajan & Abbott 2006（谱结论为间接支撑）；Jarne & Caruso 2023（低引用、工程风险提示）；Kim et al. 2019（流程相似、约束阶段不同）；Hennequin et al. 2014/2017（网络级动力学背景）。
- **不建议作为符号约束依据**：Sussillo & Abbott 2009（不含 Dale 约束，只能作无约束对照）；Dale's backprop（Balwani 2025）不可直接套用到残差 BC，其面向全网络从头训练，仅作技术借鉴。
