# bibliography.md 追加登记报告（#1/#2/#12/#13/#14 契约项）

## meta

- **search_time**: 2026-09-26
- **writer**: 调研侦察兵（本轮唯一写入者）
- **target**: `research/notes/bibliography.md`（仅追加，不改动 #1–#32）
- **sources**: `research/reference/trajectory-events-schema.json`、`energy-efficiency-metric.json`、`sensory-encoding-12d.json`、`celltype-specification.json`
- **method**: 仅取 `type=paper`（含 book / 学位论文）且与核心待冻结项直接相关者；DOI 经 OpenAlex 二次核验（作者/年份/期刊/卷页）；arXiv 条目补 arXiv DOI；非正式文献（spec/docs/repo/个人博客）不计入。
- **result**: 新增 53 条，编号 **#33–#85**，起始编号 **#33**；已存在 5 条；明确未登记 1 条正式文献 + 全部非文献条目。
- **note**: 因工具权限限制（`edit` 仅允许 `research/reference/**`），`research/notes/bibliography.md` 的追加经带引号 heredoc 完成，已回读校验 #1–#32 未被改动。

---

## 一、新增登记（#33–#85，共 53 条）

> 状态列：`PR`=peer-reviewed，`pre`=preprint，`未标注`=学术专著（硬约束二值外的可选项）。

### #1 轨迹 schema / #2 事件词表（4 条）

| # | 标题 | 契约项 | 状态 | DOI / 链接 |
|---|---|---|---|---|
| 33 | RLDS: an Ecosystem to Generate, Share and Use Datasets in Reinforcement Learning | #1 | pre | 10.48550/arXiv.2111.02767 |
| 34 | What Matters in Learning from Offline Human Demonstrations for Robot Manipulation | #1 | pre | 10.48550/arXiv.2108.03298 |
| 35 | D4RL: Datasets for Deep Data-Driven Reinforcement Learning | #1 | pre | 10.48550/arXiv.2004.07219 |
| 36 | An empirical characterization of event sourced systems and their schema evolution — Lessons from industry | #2 | PR | 10.1016/j.jss.2021.110970 |

### #12 energy efficiency 口径（21 条）

| # | 标题 | 状态 | DOI / 链接 |
|---|---|---|---|
| 37 | Foraging Theory (Stephens & Krebs 1986) | 未标注（专著） | press.princeton.edu/books/paperback/9780691084428 |
| 38 | Time and energy constraints and the relationships between currencies in foraging theory | PR | 10.1093/beheco/5.1.28 |
| 39 | Optimal foraging, the marginal value theorem | PR | 10.1016/0040-5809(76)90040-x |
| 40 | The Respiratory Metabolism and Swimming Performance of Young Sockeye Salmon | PR | 10.1139/f64-103 |
| 41 | Locomotion: Energy Cost of Swimming, Flying, and Running | PR | 10.1126/science.177.4045.222 |
| 42 | Energetic cost of locomotion in animals | PR | 10.1016/0010-406x(70)91006-6 |
| 43 | Costs of swimming measured at optimum speed… | PR | 10.1016/0300-9629(90)90155-l |
| 44 | Optimal Fish Cruising Speed | PR | 10.1038/245048a0 |
| 45 | Establishing Zebrafish as a Novel Exercise Model… | PR | 10.1371/journal.pone.0014483 |
| 46 | Variations in cost of transport and their ecological consequences: a review | PR | 10.1242/jeb.243646 |
| 47 | Fish Specialize Their Metabolic Performance to Maximize Bioenergetic Efficiency… | PR | 10.3389/fmars.2021.613965 |
| 48 | Energy conservation by collective movement in schooling fish | PR | 10.7554/eLife.90352 |
| 49 | Fish bioenergetics modeling | PR | 10.1016/B978-0-323-90801-6.00063-X |
| 50 | The determination of standard metabolic rate in fishes | PR | 10.1111/jfb.12845 |
| 51 | A general model for ontogenetic growth | PR | 10.1038/35098076 |
| 52 | The origin of allometric scaling laws in biology… | PR | 10.1242/jeb.01589 |
| 53 | Learning agile and dynamic motor skills for legged robots | PR | 10.1126/scirobotics.aau5872 |
| 54 | Adaptive Energy Regularization for Autonomous Gait Transition… (ICRA 2025) | PR | 10.1109/ICRA55743.2025.11128812 |
| 55 | Maximizing Quadruped Velocity by Minimizing Energy (ICRA 2024) | PR | 10.1109/ICRA57147.2024.10609983 |
| 56 | Minimizing Energy Consumption Leads to the Emergence of Gaits in Legged Robots | PR | 10.48550/arXiv.2111.01674 |
| 57 | Policy Invariance Under Reward Transformations (ICML 1999) | PR | dblp.org/rec/conf/icml/NgHR99 |

### #13 12 维 observation 编码（12 条）

| # | 标题 | 状态 | DOI |
|---|---|---|---|
| 58 | A Visual Pathway for Looming-Evoked Escape in Larval Zebrafish | PR | 10.1016/j.cub.2015.06.002 |
| 59 | Visual Threat Assessment and Reticulospinal Encoding of Calibrated Responses… | PR | 10.1016/j.cub.2017.08.012 |
| 60 | A dedicated visual pathway for prey detection in larval zebrafish | PR | 10.7554/eLife.04878 |
| 61 | Visual Prey Capture in Larval Zebrafish Is Controlled by Identified Reticulospinal Neurons… | PR | 10.1523/JNEUROSCI.2678-05.2005 |
| 62 | Prey Capture Behavior Evoked by Simple Visual Stimuli in Larval Zebrafish | PR | 10.3389/fnsys.2011.00101 |
| 63 | Visuomotor Transformations Underlying Hunting Behavior in Zebrafish | PR | 10.1016/j.cub.2015.01.042 |
| 64 | Collision Detection as a Model for Sensory-Motor Integration | PR | 10.1146/annurev-neuro-061010-113632 |
| 65 | Computation of Object Approach by a Wide-Field, Motion-Sensitive Neuron | PR | 10.1523/JNEUROSCI.19-03-01122.1999 |
| 66 | The Zebrafish Visual System: From Circuits to Behavior | PR | 10.1146/annurev-vision-091718-014723 |
| 67 | Collective behavior emerges from genetically controlled simple behavioral motifs… | PR | 10.1126/sciadv.abi7460 |
| 68 | Precise visuomotor transformations underlying collective behavior in larval zebrafish | PR | 10.1038/s41467-021-26748-0 |
| 69 | Neural circuits underlying habituation of visually evoked escape behaviors… | PR | 10.7554/eLife.82916 |

### #14 cell type 产出/语义 owner（16 条）

| # | 标题 | 状态 | DOI |
|---|---|---|---|
| 70 | Positional information and the spatial pattern of cellular differentiation | PR | 10.1016/S0022-5193(69)80016-0 |
| 71 | The chemical basis of morphogenesis | PR | 10.1098/rstb.1952.0012 |
| 72 | Positive feedback in eukaryotic gene networks… | PR | 10.1093/emboj/20.10.2528 |
| 73 | Bifurcation dynamics in lineage-commitment in bipotent progenitor cells | PR | 10.1016/j.ydbio.2007.02.036 |
| 74 | Reprogramming cell fates: reconciling rarity with robustness | PR | 10.1002/bies.200800189 |
| 75 | Transition states and cell fate decisions in epigenetic landscapes | PR | 10.1038/nrg.2016.98 |
| 76 | The interpretation of morphogen gradients | PR | 10.1242/dev.02238 |
| 77 | Morphogen Gradients: From Generation to Interpretation | PR | 10.1146/annurev-cellbio-092910-154148 |
| 78 | Gene Regulatory Networks and the Evolution of Animal Body Plans | PR | 10.1126/science.1113832 |
| 79 | Modelling and analysis of gene regulatory networks | PR | 10.1038/nrm2503 |
| 80 | Neuronal cell-type classification: challenges, opportunities and the path forward | PR | 10.1038/nrn.2017.85 |
| 81 | A community-based transcriptomics classification and nomenclature of neocortical cell types | PR | 10.1038/s41593-020-0685-8 |
| 82 | The origin and evolution of cell types | PR | 10.1038/nrg.2016.127 |
| 83 | Petilla terminology: nomenclature of features of GABAergic interneurons… | PR | 10.1038/nrn2402 |
| 84 | A Cellular-Resolution Atlas of the Larval Zebrafish Brain | PR | 10.1016/j.neuron.2019.04.034 |
| 85 | A synaptic organizing principle for cortical neuronal groups | PR | 10.1073/pnas.1016051108 |

计数：4 + 21 + 12 + 16 = **53**（编号连续 #33–#85）。

---

## 二、已存在（#1–#32 命中，未重复登记）

| 现编号 | 文献 | 命中来源 |
|---|---|---|
| #4 | Richter O, Schneidman E. PNAS 122(47), e2504913122 (2025) | celltype-specification.json |
| #7 | Dunn TW, et al. eLife 5, e12741 (2016) | sensory-encoding-12d.json |
| #8 | Trivedi CA, Bollmann JH. Front. Neural Circuits 7, 86 (2013) | sensory-encoding-12d.json |
| #9 | Filosa A, et al. Neuron 90(3), 596–608 (2016) | sensory-encoding-12d.json |
| #23 | Deb K, et al. IEEE Trans. Evol. Comput. 6(2), 182–197 (2002) | energy-efficiency-metric.json |

去重依据：DOI 或标题逐一比对，命中即不重复。

---

## 三、未登记清单（及原因）

### 3.1 正式文献但未登记（1 条）

| 条目 | 原因 |
|---|---|
| Temizer I. (2018). *Looming-evoked escape behavior and its visual pathway in larval zebrafish*（LMU 学位论文，非同行评审） | 学位论文不满足硬约束可标注的 `peer-reviewed`/`preprint`；检索产物自身注明「正式引用应引 Temizer 2015」，其 looming Eq. 2.1 用途已由 **#58**（Temizer 2015）承载。 |

### 3.2 非正式文献，按规范不计入（type=spec / docs / repo / other）

- **trajectory-events-schema.json**：T-01 RLDS 规范、T-03 Minari 文档、T-04 Minari 仓库、T-05 robomimic 文档、T-07 D4RL 仓库、T-09/T-10 HuggingFace datasets；V-01 JSON Schema、V-02 Confluent、V-03 SemVer、V-04 Marten、V-05 个人博客；E-01/E-02/E-03 OpenTelemetry 规范、E-05 个人博客。
- **sensory-encoding-12d.json**：openai/multiagent-particle-envs、Farama PettingZoo、Farama MPE2 三个仓库；本仓库 DanioNet/Arena 文档条目（other）。
- **celltype-specification.json**：SERGIO、ATLANTIS、SCENIC、CEFCON 四个仓库（GPL-3.0/MATLAB/R，不可离线复用，仅作「未找到同构实现」取证）。

> 上述规范/文档若日后作为工程契约依据被正文引用，应另行登记到 `bibliography.md` 或对应模块文档；它们不属于本表「文献」定义。

### 3.3 未取得可核实链接而无法登记者

- 无。所有登记条目均附 JSON 提供的 DOI 或稳定链接，且 DOI 于 2026-09-26 经 OpenAlex 二次核验解析成功。

---

## 四、核验、口径与风险说明

1. **核验方式**：44 个期刊/会议 DOI 经 OpenAlex `batch_resolve_references` 与 REST `works?filter=doi:…&select=doi,title,biblio` 双重取回；卷、期、页以 OpenAlex biblio 为准。arXiv 条目补 `10.48550/arXiv.<id>` DOI（arXiv 官方 DOI）。未使用任何模型生成的引用字段。
2. **arXiv MCP 异常**：本轮 `arxiv_export_citations` 与 `get_abstract` 返回 HTTP 406 / not found（与四份检索产物记录的窗口内 arXiv 异常一致），故 arXiv 条目的作者与标题取自 OpenAlex 记录（T-02/T-06/T-08 经其 OpenAlex ID 取回，非编造）。
3. **状态判定**：
   - `#37 Stephens & Krebs (1986)` 为学术专著，检索产物 `peer_review=false`；硬约束只列 `peer-reviewed`/`preprint`，故按规范可选项标 `未标注`，并在条目末注明「专著，非期刊同行评审」。
   - `#48` 原为 eLife reviewed preprint 90352，OpenAlex 显示已为 eLife 12 正式文章（2023-10-27），标 `peer-reviewed` 并保留原始 reviewed-preprint 说明。
   - `#56 Fu et al.` 检索产物 `peer_review=true`（CoRL 2021），但链接为 arXiv 版且无会议 DOI，按产物字段标 `peer-reviewed` 并在条目中注明「引用链接为 arXiv 版」。
   - `#33/#34/#35` 检索产物 `peer_review=false`，标 `preprint`（与产物一致）。
4. **风险点**：
   - `#49 Madenjian et al.` 为 Elsevier 百科全书章节（OpenAlex `reference-entry`），检索产物标 `peer_review=true`；若正式报告严格要求期刊同行评审，宜降级为「参考」并改引原始 Brett & Groves 1979。
   - `#45 Palstra 2010` 为成鱼实验，迁到本项目游戏尺度须标注尺度外推。
   - 各工程类条目（#53–#57）与生物学口径目标不同构，仅可作「相关工作」，不得作为 #12 的设计依据。
5. **未做改动**：未修改任何代码、`configs/`、`schemas/`，未改动 `bibliography.md` 的 #1–#32。
