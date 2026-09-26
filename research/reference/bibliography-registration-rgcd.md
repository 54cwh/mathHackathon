# 文献登记记录：RGCD 布线/放置/初始化

- **执行日期**：2026-09-26
- **来源文件**：`research/reference/rgcd-wiring-and-placement.json`
- **目标文件**：`research/notes/bibliography.md`（现到 #110，本次从 #111 起顺延）
- **写入方式**：只追加；既有 #1–#110 未改动
- **核验方式**：OpenAlex 标题/DOI 全量核验（`batch_resolve_references` + `biblio` 字段）；Glorot 页码经 PMLR 官方页面核验；Weaver 页码经 PSB 1999 原文 PDF 页眉核验（非 41–52，41–52 属 D'Haeseleer et al. 1999）
- **新增条目数**：20（#111–#130）
- **本次搜索时间**：2026-09-26

## 一、新增条目（#111–#130，20 条）

| 编号 | 作者/年份 | 标题 | 期刊 | 类型 |
|---|---|---|---|---|
| 111 | Qiao 2024 | Deciphering the genetic code of neuronal type connectivity through bilinear modeling | eLife 12, e91532 | peer-reviewed |
| 112 | Kovács et al. 2020 | Uncovering the genetic blueprint of the C. elegans nervous system | PNAS 117(52) | peer-reviewed |
| 113 | Kurmangaliyev et al. 2019 | Modular transcriptional programs separately define axon and dendrite connectivity | eLife 8, e50822 | peer-reviewed |
| 114 | Arnatkevičiūtė et al. 2018 | Hub connectivity, neuronal diversity, and gene expression in the C. elegans connectome | PLoS Comput Biol 14(2) | peer-reviewed |
| 115 | Patiño et al. 2024 | Transcriptomic cell-type specificity of local cortical circuits | Neuron 112(23) | peer-reviewed |
| 116 | Gamlin et al. 2025 | Connectomics of predicted Sst transcriptomic types in mouse visual cortex | Nature 640(8058) | peer-reviewed |
| 117 | Tasic et al. 2018 | Shared and distinct transcriptomic cell types across neocortical areas | Nature 563(7729) | peer-reviewed |
| 118 | Sperry 1963 | Chemoaffinity in the orderly growth of nerve fiber patterns and connections | PNAS 50(4) | peer-reviewed |
| 119 | Sanes & Zipursky 2020 | Synaptic Specificity, Recognition Molecules, and Assembly of Neural Circuits | Cell 181(3) | peer-reviewed |
| 120 | Caron et al. 2013 | Random convergence of olfactory inputs in the Drosophila mushroom body | Nature 497(7447) | peer-reviewed |
| 121 | Hayashi et al. 2022 | Mushroom body input connections form independently of sensory activity in Drosophila melanogaster | Current Biology 32(18) | peer-reviewed |
| 122 | Rosenbaum et al. 2016 | The spatial structure of correlated neuronal variability | Nature Neuroscience 20(1) | peer-reviewed |
| 123 | Hill et al. 2012 | Statistical connectivity provides a sufficient foundation for specific functional connectivity in neocortical neural microcircuits | PNAS 109(42) | peer-reviewed |
| 124 | Risi & Stanley 2012 | An Enhanced Hypercube-Based Encoding for Evolving the Placement, Density, and Connectivity of Neurons（ES-HyperNEAT） | Artificial Life 18(4) | peer-reviewed |
| 125 | Ercsey-Ravasz et al. 2013 | A Predictive Network Model of Cerebral Cortical Connectivity Based on a Distance Rule | Neuron 80(1) | peer-reviewed |
| 126 | Glorot & Bengio 2010 | Understanding the difficulty of training deep feedforward neural networks | AISTATS, PMLR 9 | peer-reviewed |
| 127 | Yildiz, Jaeger & Kiebel 2012 | Re-visiting the echo state property | Neural Networks 35 | peer-reviewed |
| 128 | Bertschinger & Natschläger 2004 | Real-Time Computation at the Edge of Chaos in Recurrent Neural Networks | Neural Computation 16(7) | peer-reviewed |
| 129 | Saxe, McClelland & Ganguli 2014 | Exact solutions to the nonlinear dynamics of learning in deep linear neural networks | arXiv / ICLR 2014 | **preprint** |
| 130 | Weaver, Workman & Stormo 1999 | Modeling Regulatory Networks with Weight Matrices | PSB 4 | peer-reviewed |

> 任务点名清单（14 篇）全部包含：Qiao 2024、Kovács 2020、Caron 2013、Hayashi 2022、Sanes & Zipursky 2020、Tasic 2018、Patiño 2024、Hill 2012、Rosenbaum 2016、Glorot & Bengio 2010、Yildiz et al. 2012、Bertschinger & Natschläger 2004、Sperry 1963、Ercsey-Ravasz et al. 2013。
> 额外登记 6 篇（#113、#114、#116、#124、#129、#130）：均为 JSON 中作为 RGCD §2/§3/§8/§10 证据出现、且带可核实 DOI/稳定链接的正式文献。

## 二、已存在（不重复登记）

| JSON 条目 | 已存在编号 | 说明 |
|---|---|---|
| Wolpert 1969, Positional information... | **#70** | 先按标题/DOI（10.1016/S0022-5193(69)80016-0）去重命中 |
| Kicheva & Briscoe 2023, Control of Tissue Development by Morphogens | **#105** | JSON `metrics` 自述已登记 #105，核对一致 |
| Simsek & Özbudak 2022, Patterning principles of morphogen gradients | **#106** | JSON `metrics` 自述已登记 #106，核对一致 |

> 关于 Ercsey-Ravasz 2013：任务提示「可能已登记」。按 DOI（10.1016/j.neuron.2013.07.036）与标题在 `bibliography.md` 全文检索，**未命中任何既有条目**（Waxman / Kaiser & Hilgetag / Ercsey-Ravasz / 0.188 / 距离衰减 均无），故按新增登记为 **#125**，不属「已存在」。

## 三、未登记（附原因）

| JSON 条目 | 原因 |
|---|---|
| Waxman 1988（指数距离规则） | JSON 未提供该文独立 DOI/链接（条目 `url` 指向 Ercsey-Ravasz 的 Neuron DOI）；无独立链接不登记。距离规则证据由 #125 承载，证据表见 `design-basis-connectome.md` R3 |
| Kaiser & Hilgetag 2004（指数距离规则） | 同上，JSON 未提供独立 DOI/链接，无法核实 |
| HyperNEAT（Stanley, D'Ambrosio & Gauci 2009） | JSON 条目 `url` 仅指向 ES-HyperNEAT（10.1162/artl_a_00071），未提供 2009 原文链接；ES-HyperNEAT 已登记 #124 |
| Jaeger 2001, Short-term memory in echo state networks（GMD Report 148） | 技术报告，非同行评审；JSON `source_url` 为 Scholarpedia 综述页而非原文稳定直链。ESP 的期刊锚点已由 #127（Yildiz et al. 2012）承载 |
| `muqiao0626/Bilinear_Model`（GitHub repo） | 代码而非文献（`type=repo`），按本文件「文献事实单一来源」定位不登记；Qiao 2024 论文已登记 #111 |

## 四、风险与待验证

1. **#111 Qiao 2024 年份**：OpenAlex `publication_year=2023`（eLife reviewed preprint 版），JSON 记电子正式版 2024-06-10。正文引用时须统一年份口径（建议以 eLife VOR 2024 为准，并在 BibTeX 注明）。
2. **#123 Hill 2012 末页**：OpenAlex `last_page="94"` 为截断值；E2894 依 PNAS 页面推断，正式 BibTeX 前须复核。
3. **#126 Glorot 无 DOI**：以 PMLR 稳定链接登记；页码 249–256 已由 PMLR 页面核验。
4. **#129 Saxe 评审状态**：JSON 标 `peer-reviewed conference (ICLR 2014)`，OpenAlex 类型为 `preprint`（ICLR 2014 无正式 proceedings）；本文件按 `preprint` 登记，只可作相关工作，不得作设计依据。
5. **#116、#129 使用边界**：#116 为类型层级关联证据；#129 为备选初始化方案。两者均不得在论文中作为强因果/强预测断言。
6. 全部条目 DOI/链接均取自 JSON 或经 OpenAlex/PMLR/PSB 原文核验，无编造。

## 五、本文件 `meta.owns` 与上游一致性

- 本记录为**过程证据**（Tier 6），不构成契约；文献事实以 `research/notes/bibliography.md` 为唯一来源。
- 参数取值/γ/λ 等本项目标定量不在本文件，归 `configs/` 与 `docs/参数总表.json`。
