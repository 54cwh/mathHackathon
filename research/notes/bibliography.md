# 核心参考文献

> **管辖范围**：文献事实的**单一来源**（DOI/评审状态/用途）。（层级与归属见 `AGENTS.md`「文档层级与优先级」。）

> **引用规则（硬约束）**
> 1. 每条必须有 **DOI 或稳定链接**；无法核实的不引。
> 2. 必须标注 **同行评审状态**：`peer-reviewed` / `preprint`（Zenodo/bioRxiv/arXiv 等）。
> 3. 正式报告只把 `peer-reviewed` 作为**设计依据**；`preprint` 只能作"相关工作/现状"。
> 4. 正文引用用 `[bib#n]` 对应本文件编号；本文件是唯一文献事实来源。
>
> 全部条目已于 2026-09-26 经 OpenAlex 核验存在（作者/年份/期刊/DOI 一致）。

---

## 已有研究边界（设计依据）

1. Zador AM. **A critique of pure learning and what artificial neural networks can learn from animal brains.** *Nature Communications* 10, 3770 (2019). `peer-reviewed`.
   DOI: https://doi.org/10.1038/s41467-019-11786-6
   用途：genomic bottleneck、innate wiring rules、`ΔW` 不遗传的立论基础。

2. Barabási DL, Beynon T, Katona Á, Perez-Nieves N, et al. **Complex computation from developmental priors.** *Nature Communications* 14, 2226 (2023). `peer-reviewed`.
   DOI: https://doi.org/10.1038/s41467-023-37980-1
   用途：developmental encoding / 用 wiring rules 生成权重矩阵。

3. Shuvaev SA, Lachi D, Koulakov AA, Zador AM. **Encoding innate ability through a genomic bottleneck.** *PNAS* 121(38), e2409160121 (2024). `peer-reviewed`.
   DOI: https://doi.org/10.1073/pnas.2409160121
   用途：genome-wide lossy compression of weight matrix。

4. Richter O, Schneidman E. **Building the connectome of a small brain with a simple stochastic developmental generative model.** *PNAS* 122(47), e2504913122 (2025). `peer-reviewed`.
   DOI: https://doi.org/10.1073/pnas.2504913122
   用途：cell type / birth time / distance / pruning 等发育规则生成 connectome（支撑 RGCD §8 cell-type compatibility `z^T C z`）。

5. Miikkulainen R. **Neuroevolution insights into biological neural computation.** *Science* 387(6735), eadp7478 (2025). `peer-reviewed`.
   DOI: https://doi.org/10.1126/science.adp7478
   用途：neuroevolution 与生物神经计算的统一视角（支撑 baseline 与演化框架定位）。

---

## 斑马鱼生物学依据（设计 prior）

6. Petrucco L, Lavian H, Wu YK, Svara F, Štih V, et al. **Neural dynamics and architecture of the heading direction circuit in zebrafish.** *Nature Neuroscience* 26, 765–773 (2023). `peer-reviewed`.
   DOI: https://doi.org/10.1038/s41593-023-01308-5
   用途：heading-direction ring 采样 / 左右运动竞争 / anterior hindbrain 回路（支撑 DanioNet §5）。

7. Dunn TW, Mu Y, Narayan S, Randlett O, Naumann EA, et al. **Brain-wide mapping of neural activity controlling zebrafish exploratory locomotion.** *eLife* 5, e12741 (2016). `peer-reviewed`.
   DOI: https://doi.org/10.7554/eLife.12741
   用途：spontaneous 左右交替转向、ARTR 群体（支撑 DanioNet 动力学与积分记忆）。

8. Trivedi CA, Bollmann JH. **Visually driven chaining of elementary swim patterns into a goal-directed motor sequence: a virtual reality study of zebrafish prey capture.** *Frontiers in Neural Circuits* 7, 86 (2013). `peer-reviewed`.
   DOI: https://doi.org/10.3389/fncir.2013.00086
   用途：prey capture 的视觉追踪与 bout 序列（支撑 DanioNet §2 prey channel、Arena 捕食任务）。

9. Filosa A, Barker AJ, Dal Maschio M, Baier H. **Feeding State Modulates Behavioral Choice and Processing of Prey Stimuli in the Zebrafish Tectum.** *Neuron* 90(3), 596–608 (2016). `peer-reviewed`.
   DOI: https://doi.org/10.1016/j.neuron.2016.03.014
   用途：hunger 调制 approach–avoidance（支撑 12 维输入的 energy/hunger、Arena §11 `w_p = w_{p0} + k_H H`）。

10. Zaupa M, Nagaraj N, Sylenko A, Baier H, Sawamiphak S. **The Calmodulin-interacting peptide Pcp4a regulates feeding state-dependent behavioral choice in zebrafish.** *Neuron* 112(7), 1155–1167 (2024). `peer-reviewed`.
    DOI: https://doi.org/10.1016/j.neuron.2024.01.001
    用途：feeding state 与 foraging 决策（补充支撑 hunger 调制）。

11. Zhao S, Shan H, Liu X, Qian Y, Huang J, et al. **A thalamus–brainstem attractor network drives history-biased decisions.** *Nature* (2026). `peer-reviewed`.
    DOI: https://doi.org/10.1038/s41586-026-10623-3
    用途：thalamus–brainstem attractor 驱动历史依赖决策（支撑 DanioNet 的 integrator_memory 与 H3）。

12. Baranasić D, Hörtenhuber M, Balwierz PJ, Zehnder T, Mukarram AK, et al. (DANIO-CODE). **Multiomic atlas with functional stratification and developmental dynamics of zebrafish cis-regulatory elements.** *Nature Genetics* 54, 1037–1050 (2022). `peer-reviewed`.
    DOI: https://doi.org/10.1038/s41588-022-01089-w
    用途：真实斑马鱼 cis-regulatory 元件目录（说明人工 motif/GRN 与真实调控基因组的关系，仅作对照，不导入）。

13. Herrera-Álvarez S, Patton JEJ, Thornton JW. **The structure of an ancient genotype–phenotype map shaped the functional evolution of a protein family.** *Nature Ecology & Evolution* 9, 1656–1669 (2025). `peer-reviewed`.
    DOI: https://doi.org/10.1038/s41559-025-02777-6
    用途：genotype–phenotype map 的结构与演化约束（支撑"DNA→结构"非任意映射的立论）。

14. Dorkenwald S, Matsliah A, Sterling AR, Schlegel PM, Yu S, et al. **Neuronal wiring diagram of an adult brain.** *Nature* 634, 124–138 (2024). `peer-reviewed`.
    DOI: https://doi.org/10.1038/s41586-024-07558-y
    用途：真实连接组的 cell type 与 wiring 组织（支撑 connectome 生成的生物学合理性论证）。

---

## 相关工程工作（仅作相关工作，不作设计依据）

15. Sudarshan TP. **Neural DNA: A Compact Genome for Growing Network Architecture.** Zenodo (2026). `preprint`（非同行评审，0 引用）。
    DOI: https://doi.org/10.5281/zenodo.19248389
    用途：**相关工作**——紧凑**学习到的**基因组（<300 参数）以 type-based compatibility rules 生长拓扑。
    ⚠️ 边界：其基因组**不含 ACGT、不含 motif**，由梯度学习得到。**不能**用于支撑本项目 `bp=128` 或 `n_motifs=8`。

16. Sudarshan TP. **Scaling Neural DNA to GPT-2: 354 Parameters Wire a Language Model.** Zenodo (2026). `preprint`（非同行评审，0 引用）。
    DOI: https://doi.org/10.5281/zenodo.19390927
    用途：同上，规模外推。⚠️ 同 #15 的边界。

---

## 斑马鱼外部数据资源（仅作校验 / 命名，不导入训练）

17. Marques JC, Lackner S, Félix R, Orger MB. **Structure of the Zebrafish Locomotor Repertoire Revealed with Unsupervised Behavioral Clustering.** *Current Biology* 28(2), 181–195.e5 (2018). `peer-reviewed`.
    DOI: https://doi.org/10.1016/j.cub.2017.12.002
    用途：幼鱼运动 repertoire 运动学统计。仅用于 core §8 生物合理性校验图（转向角分布 / bout 时长），不用于训练。

18. Hildebrand DGC, Cicconet M, Torres RM, Choi W, Quan TM, et al. **Whole-brain serial-section electron microscopy in larval zebrafish.** *Nature* 545(7654), 345–349 (2017). `peer-reviewed`.
    DOI: https://doi.org/10.1038/nature22356
    用途：幼鱼全脑 ssEM 体积（原始对齐图像约 2.7 TB）。仅用于引用佐证六类 fate / 连接密度 / 距离代价规则的生物学来源，不导入模型（违背"不做真实大脑逐神经元复刻"的冻结范围）。

19. Randlett O, Wee CL, Naumann EA, Nnaemeka O, Schoppik D, et al. **Whole-brain activity mapping onto a zebrafish brain atlas.** *Nature Methods* 12(11), 1039–1046 (2015). `peer-reviewed`.
    DOI: https://doi.org/10.1038/nmeth.3581
    用途：Z-Brain 脑区图谱。仅用于给 6 个 developmental domains 对应真实脑区命名。

---

## 依据新增（假设判据 / H3 / Dale 约束，2026-09-26）

20. Hartle H, Klein B, McCabe S, Daniels A, St-Onge G, Murphy C, Hébert-Dufresne L. **Network comparison and the within-ensemble graph distance.** *Proc. R. Soc. A* 476(2240), 20190744 (2020). `peer-reviewed`. DOI: https://doi.org/10.1098/rspa.2019.0744
    用途：小样本（n=3）下 connectome 差异的统计口径（H1）。

21. Smouse PE, Long JC, Sokal RR. **Multiple regression and correlation extensions of the Mantel test of matrix correspondence.** *Systematic Zoology* 35(4), 627–632 (1986). `peer-reviewed`. DOI: https://doi.org/10.2307/2413122
    用途：connectome↔behavior 矩阵相关检验（H2）。

22. Latora V, Marchiori M. **Efficient behavior of small-world networks.** *Phys. Rev. Lett.* 87(19), 198701 (2001). `peer-reviewed`. DOI: https://doi.org/10.1103/PhysRevLett.87.198701
    用途：图论 efficiency 定义；与本项目 "active-edge efficiency" 区分命名（H4）。

23. Deb K, Pratap A, Agarwal S, Meyarivan T. **A fast and elitist multiobjective genetic algorithm: NSGA-II.** *IEEE Trans. Evol. Comput.* 6(2), 182–197 (2002). `peer-reviewed`. DOI: https://doi.org/10.1109/4235.996017
    用途：性能—效率 Pareto 前沿（H3）。

24. Via S, Lande R. **Genotype–environment interaction and the evolution of phenotypic plasticity.** *Evolution* 39(3), 505–522 (1985). `peer-reviewed`. DOI: https://doi.org/10.1111/j.1558-5646.1985.tb00391.x
    用途：reaction norm / GxE（H5）。

25. Malosetti M, Ribaut JM, van Eeuwijk FA. **The statistical analysis of multi-environment data: modeling genotype-by-environment interaction.** *Front. Physiol.* 4, 44 (2013). `peer-reviewed`. DOI: https://doi.org/10.3389/fphys.2013.00044
    用途：AMMI/GGE 识别 rank reversal（H5）。

26. Yang E, Zwart MF, James B, Rubinov M, Wei Z, Narayan V, et al. **A brainstem integrator for self-location memory and positional homeostasis in zebrafish.** *Cell* 185(26), 5011–5027 (2022). `peer-reviewed`. DOI: https://doi.org/10.1016/j.cell.2022.11.022
    用途：H3 检验任务"遮蔽后延迟重定位"的行为学原型。

27. Bernacchia A, Seo H, Lee D, Wang XJ. **A reservoir of time constants for memory traces in cortical neurons.** *Nature Neuroscience* 14(3), 366–372 (2011). `peer-reviewed`. DOI: https://doi.org/10.1038/nn.2752
    用途：异质时间常数库支撑记忆痕迹（H3）。

28. Dambre J, Verstraeten D, Schrauwen B, Massar S. **Information processing capacity of dynamical systems.** *Scientific Reports* 2, 514 (2012). `peer-reviewed`. DOI: https://doi.org/10.1038/srep00514
    用途：记忆容量上界=状态数 N 的约束 → H3 不得写"提高记忆容量"。

29. Eccles JC, Fatt P, Koketsu K. **Cholinergic and inhibitory synapses in a pathway from motor-axon collaterals to motoneurones.** *J. Physiol.* 126(3), 524–562 (1954). `peer-reviewed`. DOI: https://doi.org/10.1113/jphysiol.1954.sp005226
    用途：Dale's principle 的实验形式化；突触符号由突触前决定。

30. Song HF, Yang GR, Wang XJ. **Training excitatory-inhibitory recurrent neural networks for cognitive tasks.** *PLoS Comput. Biol.* 12(2), e1004792 (2016). `peer-reviewed`. DOI: https://doi.org/10.1371/journal.pcbi.1004792
    用途：硬符号约束下训练 E/I 网络可行（支撑 ΔW 保持符号）。

31. Balwani A, et al. **Constructing biologically constrained RNNs via Dale's backpropagation.** *Science Advances* (2025). `peer-reviewed`. DOI: https://doi.org/10.1126/sciadv.adw4970
    用途：符号约束的实现技术（Dale's backprop）。

32. Parisien C, Anderson CH, Eliasmith C. **Solving the problem of negative synaptic weights in cortical models.** *Neural Computation* 20(6), 1473–1494 (2008). `peer-reviewed`. DOI: https://doi.org/10.1162/neco.2008.07-06-295
    用途：E/I 实现负权重的建模处理。

---

## 依据新增（#1/#2/#12/#13/#14 契约项，2026-09-26）

> 来源：`research/reference/trajectory-events-schema.json`、`energy-efficiency-metric.json`、`sensory-encoding-12d.json`、`celltype-specification.json` 的 items。
> 登记范围：`type=paper`（含 book / 正式学位论文）且与核心待冻结项 #1（轨迹 schema）、#2（事件词表）、#12（energy efficiency）、#13（12 维 observation）、#14（cell type owner）直接相关者。
> 去重：已与 #1–#32 按 DOI / 标题比对；重复条目见文末说明。所有 DOI 于 2026-09-26 经 OpenAlex 二次核验（作者/年份/期刊/卷页一致）；arXiv 条目附 arXiv DOI。

### #1 轨迹 schema / #2 事件词表（新增）

33. Ramos S, Girgin S, Hussenot L, et al. **RLDS: an Ecosystem to Generate, Share and Use Datasets in Reinforcement Learning.** *arXiv preprint* arXiv:2111.02767 (2021). `preprint`.
    DOI: https://doi.org/10.48550/arXiv.2111.02767
    用途：#1 轨迹契约——episode/step 两级组织与 Step 必填字段 is_first/is_last 的学术出处（含 imitation learning 场景）。

34. Mandlekar A, Xu D, Wong J, et al. **What Matters in Learning from Offline Human Demonstrations for Robot Manipulation.** *arXiv preprint* arXiv:2108.03298 (2021). `preprint`.
    DOI: https://doi.org/10.48550/arXiv.2108.03298
    用途：#1 轨迹契约——robomimic HDF5 布局（demo_N 组 + env_args + obs/actions/rewards/dones）的学术出处；BC 演示数据惯例。

35. Fu J, Kumar A, Nachum O, Tucker G, Levine S. **D4RL: Datasets for Deep Data-Driven Reinforcement Learning.** *arXiv preprint* arXiv:2004.07219 (2020). `preprint`.
    DOI: https://doi.org/10.48550/arXiv.2004.07219
    用途：#1 轨迹契约——observations/actions/rewards/terminals 扁平数组字段命名惯例；terminals↔timeouts 分列对应本项目 terminated/truncated 分列。

36. Overeem M, Spoor M, Jansen S, Brinkkemper S. **An empirical characterization of event sourced systems and their schema evolution — Lessons from industry.** *Journal of Systems and Software* 178, 110970 (2021). `peer-reviewed`.
    DOI: https://doi.org/10.1016/j.jss.2021.110970
    用途：#2 事件词表冻结——19 个工业事件溯源系统的 schema 演化五法（versioned events / weak schema / upcasting / in-place / copy-and-transform）。

### #12 energy efficiency 口径（新增）

37. Stephens DW, Krebs JR. **Foraging Theory.** *Princeton University Press* (1986). `未标注`（学术专著，非期刊同行评审；出版方 ISBN 页面为稳定链接）.
    链接: https://press.princeton.edu/books/paperback/9780691084428/foraging-theory
    用途：#12 净能量获取率 net rate=(E_gain−E_cost)/T 与效率 efficiency=E_gain/E_cost 两种觅食货币的定义来源（最优觅食理论标准权威）。

38. Ydenberg RC, Welham CVJ, Schmid-Hempel R, Schmid-Hempel P, Beauchamp G. **Time and energy constraints and the relationships between currencies in foraging theory.** *Behavioral Ecology* 5(1), 28–34 (1994). `peer-reviewed`.
    DOI: https://doi.org/10.1093/beheco/5.1.28
    用途：#12 效率（收益/支出）与净速率（净能量/时间）两种货币并置；本项目在比率与速率间取舍的直接依据。

39. Charnov EL. **Optimal foraging, the marginal value theorem.** *Theoretical Population Biology* 9(2), 129–136 (1976). `peer-reviewed`.
    DOI: https://doi.org/10.1016/0040-5809(76)90040-x
    用途：#12 以单位时间净能量收益为目标函数的理论锚点（边际价值定理）。

40. Brett JR. **The Respiratory Metabolism and Swimming Performance of Young Sockeye Salmon.** *Journal of the Fisheries Research Board of Canada* 21(5), 1183–1226 (1964). `peer-reviewed`.
    DOI: https://doi.org/10.1139/f64-103
    用途：#12 代谢成本随游泳速度上升、标准代谢(SMR)与活跃代谢分离的经典实测。

41. Schmidt-Nielsen K. **Locomotion: Energy Cost of Swimming, Flying, and Running.** *Science* 177(4045), 222–228 (1972). `peer-reviewed`.
    DOI: https://doi.org/10.1126/science.177.4045.222
    用途：#12 cost of transport（单位距离能量成本）概念的奠基引文。

42. Tucker VA. **Energetic cost of locomotion in animals.** *Comparative Biochemistry and Physiology* 34(4), 841–846 (1970). `peer-reviewed`.
    DOI: https://doi.org/10.1016/0010-406x(70)91006-6
    用途：#12 单位距离能耗（COT）口径的早期系统比较。

43. Videler JJ, Nolet BA. **Costs of swimming measured at optimum speed: Scale effects, differences between swimming styles, taxonomic groups and submerged and surface swimming.** *Comparative Biochemistry and Physiology Part A: Physiology* 97(2), 91–99 (1990). `peer-reviewed`.
    DOI: https://doi.org/10.1016/0300-9629(90)90155-l
    用途：#12 单位距离成本在最优游泳速度 Uopt 最小的经典结论（COT 与 Uopt）。

44. Weihs D. **Optimal Fish Cruising Speed.** *Nature* 245(5419), 48–50 (1973). `peer-reviewed`.
    DOI: https://doi.org/10.1038/245048a0
    用途：#12 鱼类巡游最优速度（单位距离能耗最小）的流体力学推导。

45. Palstra AP, Tudorache C, Rovira M, et al. **Establishing Zebrafish as a Novel Exercise Model: Swimming Economy, Swimming-Enhanced Growth and Muscle Growth Marker Gene Expression.** *PLoS ONE* 5(12), e14483 (2010). `peer-reviewed`.
    DOI: https://doi.org/10.1371/journal.pone.0014483
    用途：#12 斑马鱼游泳经济/COT 实测（Ucrit=0.548±0.007 m/s）；本项目物种级 COT 依据（成鱼实验，迁到游戏尺度须标尺度外推）。

46. Jahn M, Seebacher F. **Variations in cost of transport and their ecological consequences: a review.** *Journal of Experimental Biology* 225(15), jeb243646 (2022). `peer-reviewed`.
    DOI: https://doi.org/10.1242/jeb.243646
    用途：#12 COT 综述：个体内/跨物种差异与行为补偿；gross/net COT 定义的综述级依据。

47. Guo C, Ito S, Yoneda M, et al. **Fish Specialize Their Metabolic Performance to Maximize Bioenergetic Efficiency in Their Local Environment: Conspecific Comparison Between Two Stocks of Pacific Chub Mackerel (Scomber japonicus).** *Frontiers in Marine Science* 8, 613965 (2021). `peer-reviewed`.
    DOI: https://doi.org/10.3389/fmars.2021.613965
    用途：#12 确认「min gross COT 定义 Uopt」的现代用法。

48. Zhang Y, Lauder GV. **Energy conservation by collective movement in schooling fish.** *eLife* 12, e90352 (2023). `peer-reviewed`（原 eLife reviewed preprint 90352，2023-10 转为正式 eLife 文章）.
    DOI: https://doi.org/10.7554/eLife.90352
    用途：#12 COT=TEE/speed 的显式定义；鱼群游最低有氧成本约 1.0–1.25 BL/s。

49. Madenjian CP, Chipps SR, Deslauriers D, Guitard JJ, Daigle NJ. **Fish bioenergetics modeling.** *Encyclopedia of Fish Physiology* (Elsevier), 507–518 (2023). `peer-reviewed`（百科全书章节；同行评审状态依检索产物标注）.
    DOI: https://doi.org/10.1016/B978-0-323-90801-6.00063-X
    用途：#12 鱼类能量收支标准式 Consumption=Respiration+Waste+Growth 与 gross growth efficiency 定义（代表 Brett & Groves 1979）。

50. Chabot D, Steffensen JF, Farrell AP. **The determination of standard metabolic rate in fishes.** *Journal of Fish Biology* 88(1), 81–121 (2016). `peer-reviewed`.
    DOI: https://doi.org/10.1111/jfb.12845
    用途：#12 SMR 测量与术语权威综述；支撑基础维护成本 C_base 应单列（工程参数不得当作 SMR 实测）。

51. West GB, Brown JH, Enquist BJ. **A general model for ontogenetic growth.** *Nature* 413(6856), 628–631 (2001). `peer-reviewed`.
    DOI: https://doi.org/10.1038/35098076
    用途：#12 代谢能量在维护与生长间分配的理论框架（间接支撑 size–metabolism 耦合）。

52. West GB, Brown JH. **The origin of allometric scaling laws in biology from genomes to ecosystems.** *Journal of Experimental Biology* 208(9), 1575–1592 (2005). `peer-reviewed`.
    DOI: https://doi.org/10.1242/jeb.01589
    用途：#12 代谢率随质量 3/4 幂律（仅间接相关，与 COT 定义无直接关系）。

53. Hwangbo J, Lee J, Dosovitskiy A, et al. **Learning agile and dynamic motor skills for legged robots.** *Science Robotics* 4(26), eaau5872 (2019). `peer-reviewed`.
    DOI: https://doi.org/10.1126/scirobotics.aau5872
    用途：#12 工程口径——「任务奖励 + 能耗惩罚」的 RL 惯例（仅借其能耗项构造与量纲处理，不作生态效率依据）。

54. Liang B, Sun L, Zhu X, et al. **Adaptive Energy Regularization for Autonomous Gait Transition and Energy-Efficient Quadruped Locomotion.** *IEEE International Conference on Robotics and Automation (ICRA)*, 5350–5356 (2025). `peer-reviewed`.
    DOI: https://doi.org/10.1109/ICRA55743.2025.11128812
    用途：#12 工程口径——distance-averaged energy consumption 作为能耗项（仅作参考，不直接进本项目 fitness）。

55. Mahankali S, Lee CC, Margolis GB, Hong ZW, Agrawal P. **Maximizing Quadruped Velocity by Minimizing Energy.** *IEEE International Conference on Robotics and Automation (ICRA)*, 11467–11473 (2024). `peer-reviewed`.
    DOI: https://doi.org/10.1109/ICRA57147.2024.10609983
    用途：#12 工程口径——EIPO 把能耗作次要约束，指出加权求和会与任务奖励互相拉扯（仅作参考）。

56. Fu Z, Kumar A, Malik J, Pathak D. **Minimizing Energy Consumption Leads to the Emergence of Gaits in Legged Robots.** *arXiv preprint* arXiv:2111.01674 (2021)（CoRL 2021）. `peer-reviewed`.
    DOI: https://doi.org/10.48550/arXiv.2111.01674
    用途：#12 工程口径——仅以能耗最小化作奖励即可涌现步态（仅作参考；引用链接为 arXiv 版）。

57. Ng AY, Harada D, Russell SJ. **Policy Invariance Under Reward Transformations: Theory and Application to Reward Shaping.** *Proceedings of the 16th International Conference on Machine Learning (ICML 1999)*, 278–287 (1999). `peer-reviewed`（无 DOI，DBLP 稳定条目为链接）.
    链接: https://dblp.org/rec/conf/icml/NgHR99
    用途：#12 reward shaping 奠基——势函数塑形不改变最优策略；辅助能耗项应作独立 fitness 分量而非塞进 survival/prey_capture 的 reward。

### #13 12 维 observation 编码（新增）

58. Temizer I, Donovan JC, Baier H, Semmelhack JL. **A Visual Pathway for Looming-Evoked Escape in Larval Zebrafish.** *Current Biology* 25(14), 1823–1834 (2015). `peer-reviewed`.
    DOI: https://doi.org/10.1016/j.cub.2015.06.002
    用途：#13 threat_left/right 与 looming_rate 的核心依据（用 l/v 参数化视觉逼近刺激）。

59. Bhattacharyya K, McLean DL, MacIver MA. **Visual Threat Assessment and Reticulospinal Encoding of Calibrated Responses in Larval Zebrafish.** *Current Biology* 27(18), 2751–2762.e6 (2017). `peer-reviewed`.
    DOI: https://doi.org/10.1016/j.cub.2017.08.012
    用途：#13 威胁评估随刺激强度校准——threat 通道应编码可标量强度而非 0/1 标签。

60. Semmelhack JL, Donovan JC, Thiele TR, et al. **A dedicated visual pathway for prey detection in larval zebrafish.** *eLife* 3, e04878 (2014). `peer-reviewed`.
    DOI: https://doi.org/10.7554/eLife.04878
    用途：#13 prey 与 threat 通道解剖分离（顶盖前区 AF7）的关键证据。

61. Gahtan E, Tanger P, Baier H. **Visual Prey Capture in Larval Zebrafish Is Controlled by Identified Reticulospinal Neurons Downstream of the Tectum.** *Journal of Neuroscience* 25(40), 9294–9303 (2005). `peer-reviewed`.
    DOI: https://doi.org/10.1523/JNEUROSCI.2678-05.2005
    用途：#13 prey_left/right 方位编码的功能依据（猎物位置表征需持续更新）。

62. Bianco IH, Kampff AR, Engert F. **Prey Capture Behavior Evoked by Simple Visual Stimuli in Larval Zebrafish.** *Frontiers in Systems Neuroscience* 5, 101 (2011). `peer-reviewed`.
    DOI: https://doi.org/10.3389/fnsys.2011.00101
    用途：#13 尺寸依赖的趋近/回避（小目标→捕食、大目标→逃逸）；prey/predator_relative_size 与 capture κ=1.25 的依据。

63. Bianco IH, Engert F. **Visuomotor Transformations Underlying Hunting Behavior in Zebrafish.** *Current Biology* 25(7), 831–846 (2015). `peer-reviewed`.
    DOI: https://doi.org/10.1016/j.cub.2015.01.042
    用途：#13 顶盖对刺激 size/speed 呈混合选择——支持 relative_size 与 looming（速度）为独立维度。

64. Fotowat H, Gabbiani F. **Collision Detection as a Model for Sensory-Motor Integration.** *Annual Review of Neuroscience* 34, 1–19 (2011). `peer-reviewed`.
    DOI: https://doi.org/10.1146/annurev-neuro-061010-113632
    用途：#13 looming/碰撞检测的权威综述框架（角尺寸阈值、时间到碰撞）。

65. Gabbiani F, Krapp HG, Laurent G. **Computation of Object Approach by a Wide-Field, Motion-Sensitive Neuron.** *Journal of Neuroscience* 19(3), 1122–1141 (1999). `peer-reviewed`.
    DOI: https://doi.org/10.1523/JNEUROSCI.19-03-01122.1999
    用途：#13 looming 经典量化式 θ(t)=2·tan⁻¹(l/(v·t))、ψ(t)=θ̇/2，响应仅由 l/‖v‖ 决定——looming_rate 第一锚点。

66. Bollmann JH. **The Zebrafish Visual System: From Circuits to Behavior.** *Annual Review of Vision Science* 5, 269–293 (2019). `peer-reviewed`.
    DOI: https://doi.org/10.1146/annurev-vision-091718-014723
    用途：#13 视网膜特征选择型 RGC 与分通道结构化输入——12 维结构化向量而非 raw pixels 的生物学依据。

67. Harpaz R, Aspiras AC, Chambule S, et al. **Collective behavior emerges from genetically controlled simple behavioral motifs in zebrafish.** *Science Advances* 7(41), eabi7460 (2021). `peer-reviewed`.
    DOI: https://doi.org/10.1126/sciadv.abi7460
    用途：#13 relative visual field occupancy 作为视觉驱动行为 motif——左右通道距离核的文献锚点。

68. Harpaz R, Nguyen MN, Bahl A, Engert F. **Precise visuomotor transformations underlying collective behavior in larval zebrafish.** *Nature Communications* 12, 6578 (2021). `peer-reviewed`.
    DOI: https://doi.org/10.1038/s41467-021-26748-0
    用途：#13 retina-wide visual occupancy 的整合与平均——支持左右软加权投影而非硬阈值划分。

69. Fotowat H, Engert F. **Neural circuits underlying habituation of visually evoked escape behaviors in larval zebrafish.** *eLife* 12, e82916 (2023). `peer-reviewed`.
    DOI: https://doi.org/10.7554/eLife.82916
    用途：#13 风险提示——dark looming 含独立整体扩张与整体变暗两成分，纯角尺寸变化率会丢失 dimming 信号。

### #14 cell type 产出/语义 owner（新增）

70. Wolpert L. **Positional information and the spatial pattern of cellular differentiation.** *Journal of Theoretical Biology* 25(1), 1–47 (1969). `peer-reviewed`.
    DOI: https://doi.org/10.1016/S0022-5193(69)80016-0
    用途：#14 positional information 与 competence——domain 提供 competence bias（`c_domain`）的奠基文献。

71. Turing AM. **The chemical basis of morphogenesis.** *Philosophical Transactions of the Royal Society B* 237(641), 37–72 (1952). `peer-reviewed`.
    DOI: https://doi.org/10.1098/rstb.1952.0012
    用途：#14 背景——位置/几何参与模式形成的建模传统；本项目未实现反应–扩散，不得声称实现 Turing 型机制。

72. Becskei A, Séraphin B, Serrano LG. **Positive feedback in eukaryotic gene networks: cell differentiation by graded to binary response conversion.** *The EMBO Journal* 20(10), 2528–2535 (2001). `peer-reviewed`.
    DOI: https://doi.org/10.1093/emboj/20.10.2528
    用途：#14 softmax（渐变）→ argmax（二值）离散化在生物学上不荒谬；引用须限定为正反馈机制的类比。

73. Huang S, Guo Y, May G, Enver T. **Bifurcation dynamics in lineage-commitment in bipotent progenitor cells.** *Developmental Biology* 305(2), 695–713 (2007). `peer-reviewed`.
    DOI: https://doi.org/10.1016/j.ydbio.2007.02.036
    用途：#14 GRN 多稳态/分岔→fate 离散吸引子；precursor→type 的主流计算建模范式。

74. Huang S. **Reprogramming cell fates: reconciling rarity with robustness.** *BioEssays* 31(5), 546–560 (2009). `peer-reviewed`.
    DOI: https://doi.org/10.1002/bies.200800189
    用途：#14 把 softmax 解释为命运分布、argmax 落入吸引子谷的概念类比（须限定非真实势能景观）。

75. Moris N, Pina C, Martínez Arias A. **Transition states and cell fate decisions in epigenetic landscapes.** *Nature Reviews Genetics* 17(11), 693–703 (2016). `peer-reviewed`.
    DOI: https://doi.org/10.1038/nrg.2016.98
    用途：#14 关键限定——真实 fate 是连续谱、有可逆过渡态；softmax→argmax 为离散化理想化，须报告 z_i 熵作诊断。

76. Ashe HL, Briscoe J. **The interpretation of morphogen gradients.** *Development* 133(3), 385–394 (2006). `peer-reviewed`.
    DOI: https://doi.org/10.1242/dev.02238
    用途：#14 渐变 logit（l_i）→ 离散 type 的解读步骤；解读依赖细胞自身状态（competence/domain）。

77. Rogers KW, Schier AF. **Morphogen Gradients: From Generation to Interpretation.** *Annual Review of Cell and Developmental Biology* 27, 377–407 (2011). `peer-reviewed`.
    DOI: https://doi.org/10.1146/annurev-cellbio-092910-154148
    用途：#14 与 Ashe & Briscoe 互补的综述级依据（domain competence + 位置偏置 → fate）。

78. Davidson EH, Erwin DH. **Gene Regulatory Networks and the Evolution of Animal Body Plans.** *Science* 311(5762), 796–800 (2006). `peer-reviewed`.
    DOI: https://doi.org/10.1126/science.1113832
    用途：#14 GRN 驱动 fate 产出——type 产出规则属发育模型的范式归属（支撑 owner 裁决 a）。

79. Karlebach G, Shamir R. **Modelling and analysis of gene regulatory networks.** *Nature Reviews Molecular Cell Biology* 9(10), 770–780 (2008). `peer-reviewed`.
    DOI: https://doi.org/10.1038/nrm2503
    用途：#14 迭代连续式（sigmoid 递推）表示 GRN 是主流建模惯例之一。

80. Zeng H, Sanes JR. **Neuronal cell-type classification: challenges, opportunities and the path forward.** *Nature Reviews Neuroscience* 18(9), 530–546 (2017). `peer-reviewed`.
    DOI: https://doi.org/10.1038/nrn.2017.85
    用途：#14 核心——细胞类型分类多模态且各维度不一一对应；产出规则属发育/分子侧、功能语义属功能侧。

81. Yuste R, Hawrylycz M, Aalling N, et al. **A community-based transcriptomics classification and nomenclature of neocortical cell types.** *Nature Neuroscience* 23(12), 1456–1468 (2020). `peer-reviewed`.
    DOI: https://doi.org/10.1038/s41593-020-0685-8
    用途：#14 命名空间须显式区分「分子/潜在类型」与「功能类」，避免混淆。

82. Arendt D, Musser JM, Baker CVH, et al. **The origin and evolution of cell types.** *Nature Reviews Genetics* 17(12), 744–757 (2016). `peer-reviewed`.
    DOI: https://doi.org/10.1038/nrg.2016.127
    用途：#14 cell type 定义为进化保守的核心调控复合体，与功能角色属不同层级。

83. Petilla Interneuron Nomenclature Group (PING). **Petilla terminology: nomenclature of features of GABAergic interneurons of the cerebral cortex.** *Nature Reviews Neuroscience* 9(7), 557–568 (2008). `peer-reviewed`.
    DOI: https://doi.org/10.1038/nrn2402
    用途：#14 功能类 ≠ 分子类；本项目把 DanioNet 六类显式标为功能抽象的关键引用。

84. Kunst M, Laurell E, Mokayes N, et al. **A Cellular-Resolution Atlas of the Larval Zebrafish Brain.** *Neuron* 103(1), 21–38.e5 (2019). `peer-reviewed`.
    DOI: https://doi.org/10.1016/j.neuron.2019.04.034
    用途：#14 真实斑马鱼细胞类型远超六类；六类仅为面向任务的功能投影，不能声称等同真实细胞类型。

85. Perin R, Berger TK, Markram H. **A synaptic organizing principle for cortical neuronal groups.** *PNAS* 108(13), 5419–5424 (2011). `peer-reviewed`.
    DOI: https://doi.org/10.1073/pnas.1016051108
    用途：#14 连接概率由节点分组/共同邻居可预测——支撑 RGCD §8 type 兼容连接矩阵的合理性（原文规则为共同邻居，须限定）。

### 本次检索产物中「已存在」条目（未重复登记）

- `#4` Richter O, Schneidman E. PNAS 122(47), e2504913122 (2025) —— celltype-specification.json 的 Richter & Schneidman 2025（DOI 10.1073/pnas.2504913122）。
- `#7` Dunn TW, et al. eLife 5, e12741 (2016) —— sensory-encoding-12d.json 的 Dunn et al. 2016。
- `#8` Trivedi CA, Bollmann JH. Front. Neural Circuits 7, 86 (2013) —— sensory-encoding-12d.json 的 Trivedi & Bollmann 2013。
- `#9` Filosa A, et al. Neuron 90(3), 596–608 (2016) —— sensory-encoding-12d.json 的 Filosa et al. 2016。
- `#23` Deb K, et al. IEEE Trans. Evol. Comput. 6(2), 182–197 (2002) —— energy-efficiency-metric.json 的 NSGA-II（DOI 10.1109/4235.996017）。

### 未能登记清单（说明原因）

- **Temizer I. (2018) LMU 学位论文**（`https://edoc.ub.uni-muenchen.de/19569/1/Temizer_Incinur.pdf`）：type=paper 但学位论文非同行评审，且检索产物自身注明「正式引用应引 Temizer 2015」；其唯一用途（looming Eq. 2.1 的公开全文）已由 #58 承载，故不单独登记。
- **type=spec / docs / repo / other（非正式文献）**：不满足「type=paper 或 other 但属正式文献」登记条件，未登记。包括——
  - trajectory：T-01 RLDS 规范、T-03 Minari 文档、T-04 Minari 仓库、T-05 robomimic 文档、T-07 D4RL 仓库、T-09/T-10 HuggingFace datasets；V-01 JSON Schema、V-02 Confluent、V-03 SemVer、V-04 Marten、V-05 个人博客；E-01/E-02/E-03 OpenTelemetry 规范、E-05 个人博客。
  - sensory：openai/multiagent-particle-envs、Farama PettingZoo、Farama MPE2 三个仓库，及本仓库 DanioNet/Arena 文档条目（other）。
  - celltype：SERGIO、ATLANTIS、SCENIC、CEFCON 四个仓库（GPL-3.0/MATLAB/R，均不可离线复用，仅作「未找到同构实现」取证）。
  > 上述规范/文档若后续作为工程契约依据被正文引用，应另行登记到本文件或对应模块文档，不属本表「文献」范围。

> 登记口径说明：#37 Stephens & Krebs (1986) 为学术专著，检索产物 peer_review=false，本表按硬约束可选项标 `未标注`；正文引用时须注明其为专著而非期刊同行评审文献。

---

## 依据新增（genome #1–#3，2026-09-26）

> 来源：`research/reference/genotype-grn-aggregation.json`、`research/reference/phenotype-threshold-mendel.json` 的 `items`。
> 登记范围：与 genome 未决项 #1（allele 聚合 / GRN 输入）、#2（dominance 阈值）、#3（四类 phenotype / Mendel）直接相关且预期会被引用的正式文献（论文 / 专著 / 开放教科书）。
> 去重：已与 #1–#85 按 DOI / 标题比对；重复者不重登，见 `research/reference/bibliography-registration-genome.md`。
> 核验：#86–#107 的 DOI 于 2026-09-26 经 OpenAlex `batch_resolve_references` 解析、卷期页经 OpenAlex/Crossref 二次核取；#108–#110 为开放教科书（稳定链接，非同行评审）。凡源未提供卷末页者在该条 `⚠️` 注明，未杜撰。

### genome #1 allele 聚合 / GRN 输入（新增）

86. Omholt SW, Plahte E, Øyehaug L, Xiang K. **Gene Regulatory Networks Generating the Phenomena of Additivity, Dominance and Epistasis.** *Genetics* 155(2), 969–980 (2000). `peer-reviewed`.
    DOI: https://doi.org/10.1093/genetics/155.2.969
    用途：genome #1——diploid GRN 中 additivity/dominance/overdominance/epistasis 由两条 allele 的 gene dosage 与下游非线性调控涌现；支撑「聚合算子 + 下游 σ/阈值共同决定显性」。⚠️ 具体 allele 合并方程本次未逐字取得（PMC PDF 解析失败），正式引用前须核对原文。

87. Gjuvsland AB, Hayes BJ, Omholt SW, Carlborg Ö. **Statistical Epistasis Is a Generic Feature of Gene Regulatory Networks.** *Genetics* 175(1), 411–420 (2006). `peer-reviewed`.
    DOI: https://doi.org/10.1534/genetics.106.058859
    用途：genome #1——定量遗传模型结合 diploid 表达剂量网络，证明网络层产生统计非加性效应（Omholt 2000 的方法学后续）。

88. Emmrich PMF, Roberts HE, Pancaldi V. **A Boolean gene regulatory model of heterosis and speciation.** *BMC Evolutionary Biology* 15, 24 (2015). `peer-reviewed`.
    DOI: https://doi.org/10.1186/s12862-015-0298-0
    用途：genome #1——diploid Boolean GRN 把双亲全部 allele 放入同一网络、由网络动态产生显性；证明「先合并成单一算子」并非唯一路线。

89. Kacser H, Burns JA. **The molecular basis of dominance.** *Genetics* 97(3–4), 639–666 (1981). `peer-reviewed`.
    DOI: https://doi.org/10.1093/genetics/97.3-4.639
    用途：genome #1/#2——酶网络饱和非线性使单个 functional allele 通常已接近通路饱和；支撑 dominance 由下游非线性涌现、聚合算子不必取 max。

90. Crombach A, Hogeweg P. **Evolution of Evolvability in Gene Regulatory Networks.** *PLoS Computational Biology* 4(7), e1000112 (2008). `peer-reviewed`.
    DOI: https://doi.org/10.1371/journal.pcbi.1000112
    用途：genome #1——genotype（调控矩阵/阈值）→连续表达动力学的标准编码参照（单倍体，无两条 homolog 聚合）。

91. Banzhaf W. **Artificial Regulatory Networks and Genetic Programming.** In *Genetic Programming Theory and Practice*, ch.4, 43–61, Kluwer (2003). `未标注`（专著章节，非期刊同行评审）.
    DOI: https://doi.org/10.1007/978-1-4419-8983-3_4
    用途：genome #1——ARN：promoter/coding bit 串经 XOR 匹配度→连续调控强度；「motif affinity→GRN 输入」最同构的人工编码（单倍体）。

92. Kuo D, Banzhaf W, Leier A. **Network topology and the evolution of dynamics in an artificial genetic regulatory network model created by whole genome duplication and divergence.** *BioSystems* 85(3), 177–200 (2006). `peer-reviewed`.
    DOI: https://doi.org/10.1016/j.biosystems.2006.01.004
    用途：genome #1——ARN 的「bit-match→调控强度」可核实细节与全基因组复制研究（单倍体，未定义两条 homolog 聚合）。

93. Cussat-Blanc S, Harrington K, Banzhaf W. **Artificial Gene Regulatory Networks—A Review.** *Artificial Life* 24(4), 296–328 (2019). `peer-reviewed`.
    DOI: https://doi.org/10.1162/artl_a_00267
    用途：genome #1——人工 GRN 的 genotype→GRN→phenotype 建模谱系总览；未给出统一的 allele 合并算子。

94. Yan J, Qiu Y, Santos AMR, et al. **Systematic analysis of binding of transcription factors to noncoding variants.** *Nature* 591(7848), 147–151 (2021). `peer-reviewed`.
    DOI: https://doi.org/10.1038/s41586-021-03211-0
    用途：genome #1——SNP-SELEX：对 reference/alternative 两条 allele 分别计算 PWM 打分、以 ΔPWM 表达效应；「两条 homolog 各算一次 affinity」有据，合并惯例不存在。

95. Abramov S, Boytsov A, Bykova D, et al. **Landscape of allele-specific transcription factor binding in the human genome.** *Nature Communications* 12, 2751 (2021). `peer-reviewed`.
    DOI: https://doi.org/10.1038/s41467-021-23007-0
    用途：genome #1——ASB：两条 allele 分别打分、以 P 值 log ratio 作 affinity fold-change；支持先分 haplotype 打分，合并算子须项目自定并显式声明。

### genome #2 dominance 阈值（新增）

96. Wilkie AOM. **The molecular basis of genetic dominance.** *Journal of Medical Genetics* 31(2), 89–98 (1994). `peer-reviewed`.
    DOI: https://doi.org/10.1136/jmg.31.2.89
    用途：genome #2——显性分子机制清单（haploinsufficiency / 剂量增加 / dominant negative 等）；显性取决于剂量与阈值而非固定规则。

97. Billiard S, Castric V, Llaurens V. **The integrative biology of genetic dominance.** *Biological Reviews* 96(6), 2925–2942 (2021). `peer-reviewed`.
    DOI: https://doi.org/10.1111/brv.12786
    用途：genome #2——统一 Fisher 与 Wright 两派：显性是 diploid genotype 与 phenotype 之间非线性映射的产物；为「聚合算子 + 下游非线性」提供权威综述口径。

98. Veitia RA, Caburet S, Birchler JA. **Mechanisms of Mendelian dominance.** *Clinical Genetics* 93(3), 419–428 (2017). `peer-reviewed`.
    DOI: https://doi.org/10.1111/cge.13107
    用途：genome #2——「剂量 + 阈值」框架下 haploinsufficiency 与 dominant negative 产生显性；直接支撑阈值型 dominance 建模。

99. Agrawal AF, Whitlock MC. **Inferences About the Distribution of Dominance Drawn From Yeast Gene Knockout Data.** *Genetics* 187(2), 553–566 (2010). `peer-reviewed`.
    DOI: https://doi.org/10.1534/genetics.110.124560
    用途：genome #2——显性系数均值约 0.2、呈连续分布；用于论证 max（完全显性）是极端特例而非默认。

100. Green RM, Fish JL, Young NM, et al. **Developmental nonlinearity drives phenotypic robustness.** *Nature Communications* 8, 1970 (2017). `peer-reviewed`.
    DOI: https://doi.org/10.1038/s41467-017-02037-7
    用途：genome #2——Fgf8 剂量与表型间的非线性（饱和/阈值）压缩；实验证据支撑「一个 functional allele 足够」。

101. Curnow RN. **The Multifactorial Model for the Inheritance of Liability to Disease and Its Implications for Relatives at Risk.** *Biometrics* 28(4), 931 (1972). `peer-reviewed`.
    DOI: https://doi.org/10.2307/2528630
    用途：genome #2/#3——Falconer liability-threshold 模型的形式化：连续潜在量超过阈值才发病；支撑「表达越阈→dominance-like」。⚠️ 末页未由 OpenAlex/Crossref 提供（仅首页面 931），正式 BibTeX 前须补全。

102. Falconer DS. **The inheritance of liability to certain diseases, estimated from the incidence among relatives.** *Annals of Human Genetics* 29(1), 51–76 (1965). `peer-reviewed`.
    DOI: https://doi.org/10.1111/j.1469-1809.1965.tb00500.x
    用途：genome #2/#3——liability-threshold 模型奠基文献（连续 liability 超阈值→离散疾病/表型）。⚠️ 注：`genotype-grn-aggregation.json` 记为「未取得可核实 DOI」，本文件以 OpenAlex 解析该 DOI（Ann Hum Genet 29(1):51–76，引 1691）确认可核实，故登记；正式引用前建议再核原文可获取性。

103. Falconer DS, Mackay TFC. **Introduction to Quantitative Genetics, 4th edition — Ch.18 Threshold characters.** *Addison Wesley Longman*, Harlow (1996). `未标注`（教材，非期刊同行评审）.
    链接: https://archive.org/details/IntroductionToQuantitativeGenetics
    用途：genome #3——「一个/多个阈值→二类/多类离散表型」（含三表型类、双阈值示例），四类 phenotype 合法化的直接依据。⚠️ 第18章具体页码（约 pp.306–310）与版次依 Internet Archive 第4版扫描与检索片段，正式 BibTeX 前须核对。ISBN 9780582243026。

### genome #3 四类 phenotype / Mendel（新增）

104. Gianola D, Foulley JL. **Sire evaluation for ordered categorical data with a threshold model.** *Genetics Selection Evolution* 15(2), 201 (1983). `peer-reviewed`.
    DOI: https://doi.org/10.1186/1297-9686-15-2-201
    用途：genome #3——有序分类表型的「潜变量 + 阈值」统计模型（probit/threshold）；Falconer 概念在统计实现层面的经典锚点。⚠️ 末页未由 OpenAlex/Crossref 提供（仅首页面 201），正式 BibTeX 前须补全。

105. Kicheva A, Briscoe J. **Control of Tissue Development by Morphogens.** *Annual Review of Cell and Developmental Biology* 39, 91–121 (2023). `peer-reviewed`.
    DOI: https://doi.org/10.1146/annurev-cellbio-020823-011522
    用途：genome #3——连续 morphogen 剖面经下游 GRN/信号阈值转为离散 cell fate；「连续表达→阈值→离散表型」的发育生物学依据。

106. Simsek MF, Özbudak EM. **Patterning principles of morphogen gradients.** *Open Biology* 12(10), 220224 (2022). `peer-reviewed`.
    DOI: https://doi.org/10.1098/rsob.220224
    用途：genome #3——阈值解读 morphogen 梯度（French-flag）为离散表达域；阈值化离散化的标准范式。⚠️ `phenotype-threshold-mendel.json` 注明其 CC 具体版本未核，引用时须补核。

107. Abdul Rahman H, Noraidi AA, Khalid ANH, et al. **Practical guide to calculate sample size for chi-square test in biomedical research.** *BMC Medical Research Methodology* 25, 144 (2025). `peer-reviewed`.
    DOI: https://doi.org/10.1186/s12874-025-02584-4
    用途：genome #3——χ² 拟合优度检验的功效/样本量口径（非中心 χ²，Cohen's w 经验界）；支撑 n=160 对 9:3:3:1 只称「演示」而非「验证」的判据。

108. Iowa State University Digital Press. **Chapter 5: Gene Effects — Quantitative Genetics for Plant Breeding.** *Iowa State University Digital Press*（开放教科书）. `未标注`（开放教科书，非同行评审）.
    链接: https://iastate.pressbooks.pub/quantitativegenetics/chapter/gene-effects
    用途：genome #2——定量遗传标准编码 AA=+a, Aa=d, aa=−a；d=+a 或 −a 为完全显性；是把 max 算子解读为完全显性的定义依据来源。

109. OpenStax / LibreTexts. **Alternatives to Dominance and Recessiveness (incomplete dominance).** *LibreTexts*（改编自 OpenStax Biology 2e），CC BY. `未标注`（开放教科书，非同行评审）.
    链接: https://bio.libretexts.org/Bookshelves/Introductory_and_General_Biology/General_Biology_(Boundless)/12%3A_Mendel's_Experiments_and_Heredity/12.02%3A__Patterns_of_Inheritance/12.2D%3A_Alternatives_to_Dominance_and_Recessiveness
    用途：genome #2/#3——完全显性（Aa 等同 AA→3:1）与不完全显性（杂合为中间表型→1:2:1）的定义；用于固定 Mendel Mode「完全显性」前提。

110. Thompson Rivers University. **A Dihybrid Cross Showing Mendel's Second Law (Introduction to Genetics, open textbook).** *TRU Pressbooks*（开放教科书）. `未标注`（开放教科书，非同行评审）.
    链接: https://opengenetics.pressbooks.tru.ca/chapter/a-dihybrid-cross-showing-mendels-second-law-independent-assortment
    用途：genome #3——两独立位点、每基因完全显性时 AaBb×AaBb 后代 A_B_/A_bb/aaB_/aabb = 9/16:3/16:3/16:1/16；四类 phenotype 的孟德尔推导来源。

---

## 依据新增（RGCD 布线/放置/初始化，2026-09-26）

> 来源：`research/reference/rgcd-wiring-and-placement.json`（OpenAlex 标题/DOI 核验 + 本次全量 OpenAlex `biblio` 复核）。登记记录见 `research/reference/bibliography-registration-rgcd.md`。

111. Qiao M. **Deciphering the genetic code of neuronal type connectivity through bilinear modeling.** *eLife* 12, e91532 (2024). `peer-reviewed`.
    DOI: https://doi.org/10.7554/eLife.91532
    用途：RGCD §8——gene-expression 布线项 R 的双线性形式直接依据：预测连接矩阵 = X̂ Â (Ŷ B̂)^T ≡ X̂ (Â B̂^T) Ŷ^T，即 gene_i^T M gene_j（低秩 M=AB^T）；小鼠视网膜重建 r=0.83、隐维 2；C. elegans innexin→电突触 AUC≈0.64。⚠️ OpenAlex 记 publication_year 2023（reviewed preprint 版），电子正式版 2024-06-10（JSON）。

112. Kovács IA, Barabási DL, Barabási AL. **Uncovering the genetic blueprint of the C. elegans nervous system.** *PNAS* 117(52), 33570–33577 (2020). `peer-reviewed`.
    DOI: https://doi.org/10.1073/pnas.2009093117
    用途：RGCD §8——Spatial Connectome Model：B = X O X^T（对称双线性规则矩阵）+ 空间接触约束；支撑 R 用共享规则矩阵并与 -λd 联合使用（缺失接触当 0 会估错规则）。

113. Kurmangaliyev YZ, Yoo J, LoCascio SA, Zipursky SL. **Modular transcriptional programs separately define axon and dendrite connectivity.** *eLife* 8, e50822 (2019). `peer-reviewed`.
    DOI: https://doi.org/10.7554/eLife.50822
    用途：RGCD §3/§8——果蝇 T4/T5 轴突/树突布线模块化转录程序；提示单一 g_i^T g_j 只捕捉汇总相似度，M=I 忽略轴突/树突规则分离。

114. Arnatkevičiūtė A, Fulcher B, Pocock R, Fornito A. **Hub connectivity, neuronal diversity, and gene expression in the Caenorhabditis elegans connectome.** *PLoS Computational Biology* 14(2), e1005989 (2018). `peer-reviewed`.
    DOI: https://doi.org/10.1371/journal.pcbi.1005989
    用途：RGCD §8——表达↔连接统计关联的独立物种证据；关联非均匀，存在 hub 特异转录特征，R 不应当作均匀强预测器。

115. Patiño M, Rossa M, Lagos WN, Patne NS, Callaway EM. **Transcriptomic cell-type specificity of local cortical circuits.** *Neuron* 112(23), 3851–3866.e4 (2024). `peer-reviewed`.
    DOI: https://doi.org/10.1016/j.neuron.2024.09.003
    用途：RGCD §3/§8——START（单突触狂犬病毒示踪 + snRNA-seq）：小鼠 V1 转录组亚型有特异局部输入连接；证据为亚型层级，非单细胞级精确可预测。

116. Gamlin CR, Schneider-Mizell CM, Mallory M, Elabbady L, Gouwens NW, et al. **Connectomics of predicted Sst transcriptomic types in mouse visual cortex.** *Nature* 640(8058), 497–505 (2025). `peer-reviewed`.
    DOI: https://doi.org/10.1038/s41586-025-08805-6
    用途：RGCD §3/§8——Patch-seq + EM：Sst 转录组类型参与不同皮层回路、各有连接规则；转录组类型携带连接规则信息（近期正向证据）。本次 OpenAlex 已补齐（W4409283541，引 23），修正 JSON「OpenAlex 未取到」。

117. Tasic B, Yao Z, Graybuck LT, Smith KA, Nguyen TN, et al. **Shared and distinct transcriptomic cell types across neocortical areas.** *Nature* 563(7729), 72–78 (2018). `peer-reviewed`.
    DOI: https://doi.org/10.1038/s41586-018-0654-5
    用途：RGCD §3/§8——23,822 细胞 / 133 转录组细胞类型 ↔ 投射特异性分类学；只建立「类型↔投射特异」分类，不得据此声称给出 R 的函数形式。

118. Sperry RW. **Chemoaffinity in the orderly growth of nerve fiber patterns and connections.** *PNAS* 50(4), 703–710 (1963). `peer-reviewed`.
    DOI: https://doi.org/10.1073/pnas.50.4.703
    用途：RGCD §8——chemoaffinity 假说：分子化学标记匹配靶点，是「分子匹配决定布线」的定性奠基；未给函数形式或量级，不能据此选定双线性/余弦。

119. Sanes JR, Zipursky SL. **Synaptic Specificity, Recognition Molecules, and Assembly of Neural Circuits.** *Cell* 181(3), 536–556 (2020). `peer-reviewed`.
    DOI: https://doi.org/10.1016/j.cell.2020.04.008
    用途：RGCD §8——识别分子（cadherin/neurexin/LRR/Ig）为异源相互作用 ⇒ 支持 M 非单位阵（低秩 M=AB^T）；M=I 是可解释简化而非文献必然。

120. Caron SJC, Ruta V, Abbott LF, Axel R. **Random convergence of olfactory inputs in the Drosophila mushroom body.** *Nature* 497(7447), 113–117 (2013). `peer-reviewed`.
    DOI: https://doi.org/10.1038/nature12063
    用途：RGCD §8 边界——单神经元层级强随机性（约 2000 KC 采样约 50 类 PN，n=200 KC 无重复输入组合）；R 只宜作概率偏置，不能决定单细胞级精确连接。

121. Hayashi T, MacKenzie AJ, Ganguly I, Ellis KE, Smihula HM, et al. **Mushroom body input connections form independently of sensory activity in Drosophila melanogaster.** *Current Biology* 32(18), 4000–4012.e5 (2022). `peer-reviewed`.
    DOI: https://doi.org/10.1016/j.cub.2022.07.055
    用途：RGCD §8——布线不依赖感觉活动的反例：R 不应默认采用 Hebbian/共激活形式；若用活动依赖项须另立机制并声明适用范围。

122. Rosenbaum R, Smith MA, Kohn A, Rubin JE, Doiron B. **The spatial structure of correlated neuronal variability.** *Nature Neuroscience* 20(1), 107–114 (2016). `peer-reviewed`.
    DOI: https://doi.org/10.1038/nn.4433
    用途：RGCD §2——单位正方形域、距离以域边长归一、连接概率随距离衰减；为 -λd 的坐标归一化与 λ 标定提供范式。

123. Hill S, Wang Y, Riachi I, Schürmann F, Markram H. **Statistical connectivity provides a sufficient foundation for specific functional connectivity in neocortical neural microcircuits.** *PNAS* 109(42), E2885–E2894 (2012). `peer-reviewed`.
    DOI: https://doi.org/10.1073/pnas.1202128109
    用途：RGCD §2——298 细胞独立随机放置 + 轴突-树突统计重叠即可复现特异功能连接；直接支持 p_i ~ U(域) 而非规则网格。⚠️ OpenAlex 末页记作「94」（截断），E2894 依 PNAS 页面；正式 BibTeX 前复核。

124. Risi S, Stanley KO. **An Enhanced Hypercube-Based Encoding for Evolving the Placement, Density, and Connectivity of Neurons.** *Artificial Life* 18(4), 331–363 (2012). `peer-reviewed`.
    DOI: https://doi.org/10.1162/artl_a_00071
    用途：RGCD §2——ES-HyperNEAT：固定几何 substrate + CPPN 按 (源坐标,目标坐标) 查询连接；规则网格是 neuroevolution 工程惯例（仅作参考，非生物机制证据）。详见 `research/reference/design-basis-connectome.md` R6。

125. Ercsey-Ravasz M, Markov NT, Lamy C, Van Essen DC, Knoblauch K, et al. **A Predictive Network Model of Cerebral Cortical Connectivity Based on a Distance Rule.** *Neuron* 80(1), 184–197 (2013). `peer-reviewed`.
    DOI: https://doi.org/10.1016/j.neuron.2013.07.036
    用途：RGCD §2——P ∝ exp(-λd) 距离依赖连接的最强实证规律；猕猴皮层 λ=0.188 mm^-1（二值密度约 66%），须按本项目无量纲尺度重标定，禁照搬。证据表另见 `research/reference/design-basis-connectome.md` R3。注：JSON 将其与 Waxman 1988、Kaiser & Hilgetag 2004 合并，后两者的独立链接见登记记录「未登记」。

126. Glorot X, Bengio Y. **Understanding the difficulty of training deep feedforward neural networks.** *Proceedings of the 13th International Conference on Artificial Intelligence and Statistics (AISTATS), PMLR* 9, 249–256 (2010). `peer-reviewed`.
    链接: https://proceedings.mlr.press/v9/glorot10a/glorot10a.pdf
    用途：RGCD §10——Xavier/Glorot 初始化 Var(w)=2/(n_in+n_out)（uniform 上限 √(6/(n_in+n_out))）；用于 GRN 的 B、P、U、u 等非递归权重。⚠️ 无 DOI；页码 249–256 经 PMLR 官方页面核验。

127. Yildiz IB, Jaeger H, Kiebel SJ. **Re-visiting the echo state property.** *Neural Networks* 35, 1–9 (2012). `peer-reviewed`.
    DOI: https://doi.org/10.1016/j.neunet.2012.07.005
    用途：RGCD §10——谱半径 ρ(W)<1 与 echo state property；为 W_g 重标定到 ρ≈0.9 的「经验充分条件/稳定性启发式」提供依据（非定理，原文给出反例）。

128. Bertschinger N, Natschläger T. **Real-Time Computation at the Edge of Chaos in Recurrent Neural Networks.** *Neural Computation* 16(7), 1413–1436 (2004). `peer-reviewed`.
    DOI: https://doi.org/10.1162/089976604323057443
    用途：RGCD §10——随机递归网络的 ordered→chaotic 临界边界与「混沌边缘计算能力最高」；支持递归权重谱半径置于 ≈1 附近（对 D_M integrator-memory 相关）。

129. Saxe AM, McClelland JL, Ganguli S. **Exact solutions to the nonlinear dynamics of learning in deep linear neural networks.** *arXiv* 1312.6120 (2013); ICLR 2014. `preprint`.
    DOI: https://doi.org/10.48550/arXiv.1312.6120
    用途：RGCD §10 备选——正交初始化（dynamical isometry）使奇异值均匀，缓解梯度爆炸/消失；仅作相关工作/现状，不作设计依据。⚠️ OpenAlex 记为 preprint（ICLR 2014 无正式 proceedings），JSON 的「peer-reviewed conference」标注不予采用。

130. Weaver DC, Workman CT, Stormo GD. **Modeling Regulatory Networks with Weight Matrices.** *Pacific Symposium on Biocomputing (PSB)* 4, 112–123 (1999). `peer-reviewed`.
    链接: https://psb.stanford.edu/psb-online/proceedings/psb99/Weaver.pdf
    用途：RGCD §10——GRN 线性权重矩阵建模传统：随机权重矩阵 + 参数化非零比例/权值上下限 + 每基因至少一正一负输入；说明 GRN 历史上用「小随机+稀疏+有界」而非 Xavier，但稳定性判据与递归网络一致。

---

## 依据新增（GA 选择方法，2026-09-26）

> 来源：`research/reference/ga-selection-methods.json`（含 7 条文献的存在性 / DOI / 卷期页 / 评审状态 / 断言支撑核验）。
> 去重：已与 #1–#130 按 DOI / 标题比对，**无重复**（GA 选择方法此前未登记）。
> 核验：4 条带 DOI 者于 2026-09-26 经 OpenAlex `batch_resolve_references` 解析（作者/年份/卷期页一致）；2 条无 DOI 的 ICGA 会议论文经 OpenAlex `biblio` 核页码；图书经出版方 / Internet Archive 核 ISBN。登记记录见 `research/reference/bibliography-registration-ga.md`。

131. Holland JH. **Adaptation in Natural and Artificial Systems: An Introductory Analysis with Applications to Biology, Control, and Artificial Intelligence.** *MIT Press*（University of Michigan Press 1975 原版；1992 MIT 重印版）(1992). `未标注`（学术专著，非期刊同行评审）.
    DOI: https://doi.org/10.7551/mitpress/1090.001.0001
    用途：GA 领域奠基原著；适应度比例繁殖（fitness proportionate selection）与 schema theorem 的思想源头。⚠️ 1975 原版无 DOI，此处以 1992 MIT 重印版 DOI 登记；本次未逐句核对原书正文。

132. Goldberg DE. **Genetic Algorithms in Search, Optimization, and Machine Learning.** *Addison-Wesley*, Reading, MA (1989). `未标注`（学术专著，非期刊同行评审）.
    链接: https://archive.org/details/geneticalgorithm0000gold（ISBN 0-201-15767-5）
    用途：sigma truncation（sigma scaling 的标准可引锚点）与线性、幂律 fitness scaling 的提出/命名来源；系统讨论比例选择的尺度问题。⚠️ sigma scaling 首提为 Forrest 1985（未正式发表技术文档，本次未取得可核实稳定链接），故本项目以 Goldberg 1989 作为 sigma truncation 的正式锚点；归属边界见 #135。

133. Baker JE. **Adaptive Selection Methods for Genetic Algorithms.** *Proc. 1st International Conference on Genetic Algorithms (ICGA)*, 101–111 (1985). `未标注`（会议论文，评审状态本次未独立核验；会议录不注册 DOI）.
    链接: https://dl.acm.org/doi/proceedings/10.5555/645511
    用途：rank selection（排名选择）首提——由 #135 Goldberg & Deb 1991 明文确认（"Baker (1985) introduced the notion of ranking selection to genetic algorithm practice"）。

134. Whitley LD. **The GENITOR Algorithm and Selection Pressure: Why Rank-Based Allocation of Reproductive Trials is Best.** *Proc. 3rd International Conference on Genetic Algorithms (ICGA)*, 116–123 (1989). `未标注`（会议论文，评审状态本次未独立核验；会议录不注册 DOI）.
    链接: https://dl.acm.org/doi/10.5555/645512.657257
    用途：rank-based selection 的系统论证——按排名分配繁殖次数优于比例繁殖；**非** rank selection 首提（首提为 #133 Baker 1985），两者须区分「系统论证」与「首提」。⚠️ 页码著录冲突：ACM DL 与 OpenAlex `biblio` 记 116–123，SCIRP/Springer 等大量文献记 116–121；本表择 116–123（一手著录），正式 BibTeX 前须按目标期刊核实。

135. Goldberg DE, Deb K. **A Comparative Analysis of Selection Schemes Used in Genetic Algorithms.** In *Foundations of Genetic Algorithms 1*, 69–93, Morgan Kaufmann/Elsevier (1991). `peer-reviewed`（FoGA 会议衍生的经典卷，书章）.
    DOI: https://doi.org/10.1016/b978-0-08-050684-5.50008-2
    用途：比例选择依赖目标函数尺度、需 scaling/ranking 缓解（原文："proportionate selection is dependent on the objective function used … It is exactly this effect that has caused researchers to turn to scaling techniques and ranking methods."）。**不得**写「Goldberg & Deb 1991 提出 sigma scaling」——原文全文无 "sigma scaling"；该归属应为 Forrest 1985（首提）/#132 Goldberg 1989（sigma truncation）。

136. Blickle T, Thiele L. **A Comparison of Selection Schemes Used in Evolutionary Algorithms.** *Evolutionary Computation* 4(4), 361–394 (1996). `peer-reviewed`.
    DOI: https://doi.org/10.1162/evco.1996.4.4.361
    用途：以 fitness distribution 建模选择算子，定理级证明 **binary tournament（t=2）与最大线性排名（s=2 / η⁻=0）在期望适应度分布上等价（identical）**。⚠️ 等价限于该特定（最大压力）线性排名参数，不可推广到任意线性排名；免费预印本（ETH TIK-Report 11, 1995）为 OCR 扫描、参数符号有乱码，引用精确参数以 MIT Press 正式版为准。

137. Eiben AE, Smith JE. **Introduction to Evolutionary Computing** (2nd ed.). *Springer, Natural Computing Series* (2015). `未标注`（教科书，非期刊同行评审）.
    DOI: https://doi.org/10.1007/978-3-662-44874-8
    用途：教科书级明文（§5.2.4）——tournament selection 比较相对而非绝对适应度，故对 fitness 的 translation/transposition 不变，与 ranking 同具尺度不变性；支撑「tournament 对绝对适应度不变」命题的主引用。

---

## 依据新增（模型链定义与实现参考，2026-09-26）

> 来源：`research/reference/{phenotype-E-A-B-definition, module-ownership-and-shapes, bc-loss-weighting, delta-B-and-penetrance}.json`。已按 DOI / 稳定链接 / 标题与 #1–#137 比对去重，四套调研之间亦去重；新增如下。
> 评审状态：`peer-reviewed` 作设计依据；`preprint` 仅作相关工作；官方文档 / 开源实现 / 教材标 `未标注`。核验沿用上游调研（OpenAlex / DOI / 官方站点），本表登记未逐条重核。

138. The Correlation between Relatives on the Supposition of Mendelian Inheritance (Fisher 1918). `peer-reviewed`.
    DOI: https://doi.org/10.1017/s0080456800012163
    用途：把孟德尔因子与连续性状方差联系起来的奠基文献：多位点 allele 效应可加性分解，是 additive gene action / gene dosage 的原始锚点。

139. The Evolution of Threshold Traits in Animals (Roff 1996). `peer-reviewed`.
    DOI: https://doi.org/10.1086/419266
    用途：阈值性状综述：离散形态由潜在连续变量 + 一个/多个阈值决定，且阈值模型适用于多基因（polygenic）而非简单孟德尔；支持'连续量 -> 阈值 -> 离散类'的建模惯例。

140. Canalization of development and the inheritance of acquired characters (Waddington 1942). `peer-reviewed`.
    DOI: https://doi.org/10.1038/150563a0
    用途：canalization 概念起点：发育在扰动下仍沿既定轨迹，表型对遗传/环境噪声具缓冲。支持'阈值/饱和非线性使小扰动不外显'的读法。

141. Order-preserving principles underlying genotype-phenotype maps ensure high additive proportions of genetic variance (Gjuvsland et al. 2011). `peer-reviewed`.
    DOI: https://doi.org/10.1111/j.1420-9101.2011.02358.x
    用途：GP map 的单调/保序性（allele 含量增加 => 表型不降）是加性方差占比高的前提；支持把 E 定义为对 allele 含量的单调函数（加性/gene dosage）。

142. Monotonicity is a key feature of genotype-phenotype maps (Gjuvsland et al. 2013). `peer-reviewed`.
    DOI: https://doi.org/10.3389/fgene.2013.00216
    用途：给出 GP map 单调性的两个度量，并论证调控网络设计原则会生成高度单调的 GP map；为 E 取'allele 剂量的单调聚合'提供量化依据。

143. Transcriptional regulation by the numbers: models (Bintu et al. 2005). `peer-reviewed`.
    DOI: https://doi.org/10.1016/j.gde.2005.02.007
    用途：转录调控的热力学/占据模型：启动子占据由 TF 浓度与结合位点亲和力决定，转录速率随之给定；这是'motif/PWM affinity -> 表达强度'的标准映射，属表达层。

144. Transcriptional regulation by the numbers: applications (Bintu et al. 2005). `peer-reviewed`.
    DOI: https://doi.org/10.1016/j.gde.2005.02.006
    用途：上文的配套应用：把结合位点亲和力、协同性、TF 浓度组合成可拟合的表达预测式；支持 E 由 motif 亲和力（而非网络拓扑）读出。

145. PWhiddy/Growing-Neural-Cellular-Automata-Pytorch. `未标注（开源实现）`.
    链接: https://github.com/PWhiddy/Growing-Neural-Cellular-Automata-Pytorch
    用途：人工发育系统（NCA）参考实现；非 diploid、无 motif->expression 编码，仅作背景对照。

146. chenmingxiang110/Growing-Neural-Cellular-Automata. `未标注（开源实现）`.
    链接: https://github.com/chenmingxiang110/Growing-Neural-Cellular-Automata
    用途：NCA 参考实现；Python；无 diploid 聚合，仅作背景对照。

147. mspitzna/NCAtorch. `未标注（开源实现）`.
    链接: https://github.com/mspitzna/NCAtorch
    用途：轻量 NCA（PyTorch）；非 diploid motif->expression，仅作参考。

148. jdisset/grgen. `未标注（开源实现）`.
    链接: https://github.com/jdisset/grgen
    用途：通用人工 GRN 库；C++，非 Python 生态，不建议依赖。

149. d9w/AGRN.jl. `未标注（开源实现）`.
    链接: https://github.com/d9w/AGRN.jl
    用途：Julia 人工 GRN 演化库；非 Python，不建议。

150. Sisyphus192/Kern-AGRN. `未标注（开源实现）`.
    链接: https://github.com/Sisyphus192/Kern-AGRN
    用途：Python 人工 GRN；停更、无许可证，不建议。

151. Mehrshad-Ebadi/With_Mutation (aGRN + WGD). `未标注（开源实现）`.
    链接: https://github.com/Mehrshad-Ebadi/With_Mutation
    用途：人工 GRN + 全基因组复制建模；Jupyter，无许可证、无社区验证，不建议。

152. Reil (1999), Dynamics of Gene Expression in an Artificial Genome — Implications for Biological and Artificial Ontogeny. `peer-reviewed`.
    DOI: https://doi.org/10.1007/3-540-48304-7_63
    用途：人工基因组模型的奠基工作：基因组序列编码基因及其调控区，基因表达由转录因子产物与调控位点的匹配决定；是 Banzhaf/Kuo 系列 ARN 的直接源头。

153. Knabe, Nehaniv & Schilstra (2008), Regulation of gene regulation — smooth binding with dynamic affinity affects evolvability. `peer-reviewed`.
    DOI: https://doi.org/10.1109/cec.2008.4630901
    用途：对比静态绑定与『按 site–product 匹配质量决定绑定概率』的 smooth binding 模型；明确把调控位点识别建模为基因组调控区的读出函数，再进入网络动力学。

154. Stormo (2000), DNA binding sites: representation and discovery. `peer-reviewed`.
    DOI: https://doi.org/10.1093/bioinformatics/16.1.16
    用途：PWM/PSSM 表示与 binding-site 预测的经典综述：把『给定 motif 表示 → 扫描新序列 → 预测位点』定义为序列层面的分析问题。

155. Sherman & Cohen (2012), Thermodynamic State Ensemble Models of cis-Regulation. `peer-reviewed`.
    DOI: https://doi.org/10.1371/journal.pcbi.1002407
    用途：系统给出由调控 DNA 的位点构成与结合常数预测基因表达的模型类；明确把『表达 = f(位点、亲和力)』放在调控 DNA 解读层。

156. Cartharius et al. (2005), MatInspector and beyond: promoter analysis based on transcription factor binding sites. `peer-reviewed`.
    DOI: https://doi.org/10.1093/bioinformatics/bti473
    用途：启动子分析工具：摘要明言『promoter analysis is an essential step on the way to identify regulatory networks』，即 TFBS 预测是构建调控网络之前的序列层步骤。

157. Frankle & Carbin (2019), The Lottery Ticket Hypothesis: Finding Sparse, Trainable Neural Networks. `peer-reviewed`.
    链接: https://arxiv.org/abs/1803.03635（DOI: 10.48550/arXiv.1803.03635）
    用途：『中奖彩票』假说：在一个固定稀疏子网络（固定 mask/支撑）上用原始初始化独立训练，只更新存活连接；是『支撑冻结、只改幅度』的标准范式。

158. Hoefler, Alistarh, Ben-Nun, Dryden & Peste (2021), Sparsity in Deep Learning: Pruning and growth for efficient inference and training in neural networks. `preprint`.
    链接: https://arxiv.org/abs/2102.00554（DOI: 10.48550/arXiv.2102.00554）
    用途：稀疏深度学习综述，形式化 W = M ⊙ W（mask 与权重同形状）、区分固定 mask 训练与动态改 mask 训练，并讨论稀疏梯度/更新。

159. PyTorch Pruning Tutorial (Michela Paganini), torch.nn.utils.prune. `未标注（工程文档）`.
    链接: https://docs.pytorch.org/tutorials/intermediate/pruning_tutorial.html
    用途：官方惯例：剪枝 mask 以 buffer `weight_mask` 保存，形状与 weight 相同；前向用 `weight = weight_mask * weight_orig`，参数仍为同形状 `weight_orig`。

160. PyTorch MaskedTensor Overview. `未标注（工程文档）`.
    链接: https://docs.pytorch.org/tutorials/unstable/maskedtensor_overview.html
    用途：mask 语义：梯度只提供给被选中的子集（masked-in），等价于把支撑外元素的梯度屏蔽，而非置零后继续更新。

161. PyTorch, torch.set_default_dtype. `未标注（工程文档）`.
    链接: https://pytorch.org/docs/stable/generated/torch.set_default_dtype.html
    用途：PyTorch 浮点默认 dtype 为 torch.float32；可用 set_default_dtype 改为 float64（float32↔complex64，float64↔complex128）。

162. PyTorch Tensor Attributes — type promotion. `未标注（工程文档）`.
    链接: https://pytorch.org/docs/stable/tensor_attributes.html
    用途：类型提升规则：混合 dtype 的算术按『满足条件的最小 dtype』提升；浮点标量算子的 dtype 取 get_default_dtype()；与 NumPy 不同，PyTorch 不检查标量数值来决定最小 dtype。

163. PyTorch, Numerical accuracy（notes）. `未标注（工程文档）`.
    链接: https://pytorch.org/docs/stable/notes/numerical_accuracy.html
    用途：浮点加法不满足结合律，PyTorch 不保证数学等价计算得到 bitwise 一致结果；跨版本/跨平台、尤其 CPU 与 GPU 之间结果可不同。

164. PyTorch, Reproducibility（notes）. `未标注（工程文档）`.
    链接: https://pytorch.org/docs/stable/notes/randomness.html
    用途：Bitwise 一致不跨设备/后端/版本保证；不同 SDPA backend 浮点累加顺序不同即结果不同；需显式 use_deterministic_algorithms 才可能确定。

165. NumPy, Array creation（basics）. `未标注（工程文档）`.
    链接: https://numpy.org/doc/stable/user/basics.creation.html
    用途：NumPy 默认浮点为双精度 float64（np.zeros/ones 等默认 dtype=float64，平台相关整数默认）。

166. NumPy, Data type promotion. `未标注（工程文档）`.
    链接: https://numpy.org/doc/stable/reference/arrays.promotion.html
    用途：NumPy 提升规则：Python float 与 float32 数组交互通常保持 float32（按值），但若按类型提升（result_type(type(x), f32)）则得 float64；整数默认 int64。

167. Micikevicius et al. (2018), Mixed Precision Training. `peer-reviewed`.
    链接: https://arxiv.org/abs/1710.03740（DOI: 10.48550/arXiv.1710.03740）
    用途：混合精度训练标准做法：权重/激活/梯度低精度存储，但保留一份 float32 master copy 用于参数更新，以维持更新保真度。

168. PyTorch, Automatic Mixed Precision package — torch.amp. `未标注（工程文档）`.
    链接: https://pytorch.org/docs/stable/amp.html
    用途：autocast 选择性降精度：若多输入 op 中任一为 float32，则将全部输入 cast 到 float32 再算，保证数值稳定；列出按最宽 dtype 提升的算子。

169. PyTorch Forums, Huge performance decrease when matrix multiplication goes from float32 to float64. `未标注（工程文档）`.
    链接: https://discuss.pytorch.org/t/huge-performance-decrease-when-matrix-multiplication-goes-from-float32-to-float64/190689
    用途：社区实测：A6000（torch 2.1 / CUDA 12.1）上 float64 矩阵乘比 float32 慢约 40–50×；消费级 GPU 缺 FP64 加速。

170. Multi-Task Learning Using Uncertainty to Weigh Losses for Scene Geometry and Semantics (Kendall, Gal & Cipolla, CVPR 2018). `未标注`.
    链接: https://openaccess.thecvf.com/content_cvpr_2018/papers/Kendall_Multi-Task_Learning_Using_CVPR_2018_paper.pdf
    用途：不确定性加权（UW）的代表作：对回归任务取高斯似然，得到 L = (1/(2 sigma_i^2)) * L_i + log sigma_i，sigma_i 通过梯度下降学习；权重随任务噪声增大而减小，log sigma 项防止 sigma 无限增大。作者在回归里回归 s := log sigma^2（而非 sigma^2）以保证数值稳定。

171. GradNorm: Gradient Normalization for Adaptive Loss Balancing in Deep Multitask Networks (Chen, Badrinarayanan, Lee & Rabinovich, ICML 2018). `未标注`.
    链接: http://proceedings.mlr.press/v80/chen18a/chen18a.pdf
    用途：GradNorm：按共享层上的**逐任务梯度范数**动态调权，目标范数为 Gbar_W * r_i(t)^alpha，用 L_grad = sum |G_W^(i) - Gbar_W * r_i^alpha|_1 更新权重，并每步重归一化 sum w_i = T。含一个超参 alpha 与权重学习率。

172. Multi-Task Learning for Dense Prediction Tasks: A Survey (Vandenhende et al., TPAMI 2021). `未标注`.
    DOI: https://doi.org/10.1109/tpami.2021.3054719
    用途：多任务学习综述，把损失平衡（loss balancing）方法系统归类为：不确定性加权（Kendall）、GradNorm、DWA、GLS 等，并指出权重选择对多任务性能敏感、需要方法特定的学习率调参。

173. Analytical Uncertainty-Based Loss Weighting in Multi-Task Learning (Kirchdorfer et al., GCPR 2024). `preprint`.
    链接: https://arxiv.org/abs/2408.07985（DOI: 10.48550/arXiv.2408.07985）
    用途：把 Kendall UW 改成解析解：最优不确定性权重正比于 **损失倒数**（omega_t = 1/L_t），再用带温度的 softmax 归一化（UW-SO）；并系统报告 UW 的'更新惯性'：权重初值错位后需约 100 个 epoch（占训练 1/4）才恢复。

174. Investigating Uncertainty Weighting for Multi-Task Learning: Insights and Analytical Alternative (Kirchdorfer et al., IJCV 2025). `未标注`.
    DOI: https://doi.org/10.1007/s11263-025-02625-x
    用途：对 Kendall UW 的批判性研究，确认其三类局限：易过拟合、homoscedastic 假设过强、对很多常用损失缺乏理论依据；并指出学习到的 sigma_k 会在训练中收缩，导致任务权重无上界地变大、过度优化'看起来好优化'的任务。

175. Reasonable Effectiveness of Random Weighting: A Litmus Test for Multi-Task Learning (Lin et al., TMLR 2022). `preprint`.
    链接: https://arxiv.org/abs/2111.10603（DOI: 10.48550/arXiv.2111.10603）
    用途：提出随机损失加权（RLW）/随机梯度加权（RGW），在五个图像数据集与两个多语言任务上与 12 个 SOTA 方法对比，随机权重即可取得可比性能；主张把随机加权作为必要 baseline 来检验复杂动态加权是否真有增益。

176. MultiNet++: Multi-Stream Feature Aggregation and Geometric Loss Strategy for Multi-Task Learning (Chennupati et al., CVPRW 2019). `未标注`.
    DOI: https://doi.org/10.1109/cvprw.2019.00159
    用途：几何损失策略（GLS）：用各任务损失的几何平均代替加权和，从而无需人为设权重、天然对尺度不敏感。

177. Gradient Surgery for Multi-Task Learning (Yu et al., NeurIPS 2020, PCGrad). `preprint`.
    链接: https://arxiv.org/abs/2001.06782（DOI: 10.48550/arXiv.2001.06782）
    用途：PCGrad：当任务梯度余弦为负（冲突）时，把一个任务的梯度投影到另一个的正交平面上以消除冲突；在 RL 与监督多任务上提升。

178. Auto-Lambda: Disentangling Dynamic Task Relationships (Liu et al., TMLR 2022). `preprint`.
    链接: https://arxiv.org/abs/2202.03091（DOI: 10.48550/arXiv.2202.03091）
    用途：用梯度元学习自动学习任务间连续、动态的权重关系（Auto-Lambda）。

179. Efficient BackProp (LeCun, Bottou, Orr & Müller, 1998; Neural Networks: Tricks of the Trade). `未标注`.
    链接: http://yann.lecun.com/exdb/publis/pdf/lecun-98b.pdf
    用途：经典训练技巧：sigmoid 输出单元若用 MSE 会在饱和区梯度极小；'Choose target values at the point of the maximum second derivative on the sigmoid so as to avoid saturating the output units'；权重初始化应使 sigmoid 主要工作在**线性区**，过大权重导…

180. Deep Learning, Chapter 6 (Goodfellow, Bengio & Courville, MIT Press 2016) §6.2.2.2. `未标注`.
    链接: https://www.deeplearningbook.org/contents/mlp.html
    用途：教材明确：用了 MSE 时，'the loss can saturate anytime sigma(z) saturates'——sigmoid 在 z 很大/很小时饱和；梯度可能小到无法学习，'whether the model has the correct answer or the incorrect answer'。因此 sigmoid 输出应优先配最大似然/交叉熵，而非 MSE。

181. scikit-learn StandardScaler 官方文档（按特征去均值、缩放到单位方差）. `未标注（工程文档）`.
    链接: https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html
    用途：标准化定义：z = (x - u) / s，按特征独立计算均值与标准差；并说明若某特征方差比其它大几个数量级，会主导目标函数、使估计器无法正确学习其它特征。统计量在**训练集**上计算并保存、再 transform 后续数据。

182. Stable-Baselines3 — Reinforcement Learning Tips and Tricks（动作空间归一化）. `未标注（工程文档）`.
    链接: https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html
    用途：连续控制最佳实践：'normalize your action space and make it symmetric if it is continuous'，建议缩放到 [-1,1]；并给出官方 VecNormalize 实现。

183. robomimic 数据格式文档 — 'Actions should be normalized between -1 and 1'. `未标注（工程文档）`.
    链接: https://robomimic.github.io/docs/datasets/overview.html
    用途：机器人模仿学习数据约定：动作应归一化到 [-1,1]，'because this range enables easier policy learning via the use of tanh layers'；并提供 get_dataset_info.py 来检查动作范围是否违规。

184. LibMTL: A PyTorch Library for Multi-Task Learning (JMLR 2023). `未标注（开源实现）`.
    链接: https://github.com/median-research-group/LibMTL
    用途：PyTorch 多任务学习库，统一实现 EW（等权）、UW（Kendall）、GradNorm、DWA、GLS、PCGrad、IMTL、CAGrad、RLW 等，命令行一行切换 --weighting 即可对比。JMLR 2023 接收。

185. lucidrains/gradnorm-pytorch — practical GradNorm implementation. `未标注（开源实现）`.
    链接: https://github.com/lucidrains/gradnorm-pytorch
    用途：GradNorm 的轻量 PyTorch 实现，可插入任意多损失模型。

186. tianheyu927/PCGrad — official code for Gradient Surgery for Multi-Task Learning. `未标注（开源实现）`.
    链接: https://github.com/tianheyu927/PCGrad
    用途：PCGrad 官方 TensorFlow/PyTorch 实现。

187. lorenmt/auto-lambda — official implementation of Auto-Lambda (TMLR 2022). `未标注（开源实现）`.
    链接: https://github.com/lorenmt/auto-lambda
    用途：Auto-Lambda（梯度元学习动态任务加权）官方实现。

188. Average excess and average effect of a gene substitution (Fisher 1941, Annals of Eugenics 11(1):53-63). `peer-reviewed`.
    DOI: https://doi.org/10.1111/j.1469-1809.1941.tb02272.x
    用途：定义 gene substitution 的 average effect：在固定遗传背景下替换一个等位基因所导致的表型期望变化；是‘单突变平均效应’的量化遗传学原型。

189. The causal meaning of Fisher's average effect (Lee & Chow 2013, Genetics Research 95(2-3):89-100). `peer-reviewed`.
    DOI: https://doi.org/10.1017/S0016672313000074
    用途：区分 Fisher 的 average effect（因果：实际改变同源等位状态引起的表型变化）与 average excess（相关：群体中携带某等位基因者的平均偏差），并指出二者在非随机关联下不同。

190. The distribution of fitness effects of new mutations (Eyre-Walker & Keightley 2007, Nature Reviews Genetics 8(8):610-618). `peer-reviewed`.
    DOI: https://doi.org/10.1038/nrg2146
    用途：突变效应通常以‘效应量分布（DFE）’而非单点均值报告；分布形状本身是结论的一部分。

191. Distribution Theory for Glass's Estimator of Effect size and Related Estimators (Hedges 1981, Journal of Educational Statistics 6(2):107-128). `peer-reviewed`.
    DOI: https://doi.org/10.3102/10769986006002107
    用途：给出标准化均值差的精确分布、小样本偏差与无偏校正因子 J（即 Hedges' g 的由来）。

192. Statistical Power Analysis for the Behavioral Sciences (Cohen 1988/2013, 2nd ed., Routledge). `未标注`.
    DOI: https://doi.org/10.4324/9780203771587
    用途：Cohen's d 家族与效应量小/中/大基线的权威来源；含配对设计 d_z 的口径。

193. Calculating and reporting effect sizes to facilitate cumulative science: a practical primer for t-tests and ANOVAs (Lakens 2013, Frontiers in Psychology 4:863). `peer-reviewed`.
    DOI: https://doi.org/10.3389/fpsyg.2013.00863
    用途：可在论文中直接引用的效应量计算与报告规范；含独立样本与配对样本 d 的公式与 CI。

194. A review of effect sizes and their confidence intervals, Part I: The Cohen's d family (Goulet-Pelletier & Cousineau 2018, The Quantitative Methods for Psychology 14(4):242-256). `peer-reviewed`.
    DOI: https://doi.org/10.20982/tqmp.14.4.p242
    用途：系统给出两独立组与两重复测量（配对样本）设计的 Cohen's d 与 Hedges' g 公式及 CI。

195. Combining effect size estimates in meta-analysis with repeated measures and independent-groups designs (Morris & DeShon 2002, Psychological Methods 7(1):105-125). `peer-reviewed`.
    DOI: https://doi.org/10.1037/1082-989x.7.1.105
    用途：重复测量与独立组设计的效应量不可直接混用；必须变换到同一度量并按设计专用方差估计精度。

196. Unrepeatable Repeatabilities: A Common Mistake (Lessells & Boag 1987, The Auk 104(1):116-121). `peer-reviewed`.
    DOI: https://doi.org/10.2307/4087240
    用途：repeatability 的正确估计（组内/组间方差分解）与常见错误；行为测量在个体内与个体间分层的经典依据。

197. Quantifying individual variation in behaviour: mixed-effect modelling approaches (Dingemanse & Dochtermann 2012, Journal of Animal Ecology 82(1):39-54). `peer-reviewed`.
    DOI: https://doi.org/10.1111/1365-2656.12013
    用途：把行为表型方差分解为个体间与个体内成分；不同成分的生态/演化含义不同。

198. Statistics for Evaluating Pre-post Change: Relation Between Change in the Distribution Center and Change in the Individual Scores (Estrada, Ferrer & Pardo 2019, Frontiers in Psychology 9:2696). `peer-reviewed`.
    DOI: https://doi.org/10.3389/fpsyg.2018.02696
    用途：区分布局中心变化（average-based）与个体变化（individual-based）两类统计量，并给出两者关系。

199. Some properties of simulation interval estimators under dependence induction (Nelson 1987, Operations Research Letters 6(4):175-181). `peer-reviewed`.
    DOI: https://doi.org/10.1016/0167-6377(87)90015-0
    用途：common random numbers（CRN）通过诱导正相关降低两方案差值估计的方差；给出区间估计性质。

200. Advances in Genetic Algorithm Optimization of Traffic Signals (Kesur 2009, Journal of Transportation Engineering 135(4):160-171). `peer-reviewed`.
    DOI: https://doi.org/10.1061/(asce)0733-947x(2009)135:4(160)
    用途：在随机仿真 + 遗传算法中用 common random numbers 降低适应度评估方差，并讨论 replication 数与计算分配。

201. Green Simulation of Pandemic Disease Propagation (Wilson, Alabdulkarim & Goldsman 2019, Symmetry 11(4):580). `peer-reviewed`.
    DOI: https://doi.org/10.3390/sym11040580
    用途：用 common random numbers 跨情景复用随机数流以减少重仿真、降低方差。

202. The cost of dichotomising continuous variables (Altman & Royston 2006, BMJ 332(7549):1080). `peer-reviewed`.
    DOI: https://doi.org/10.1136/bmj.332.7549.1080
    用途：把连续变量二分会导致信息损失与统计功效下降；应优先保留连续度量或至少并列报告。

203. On the practice of dichotomization of quantitative variables (MacCallum, Zhang, Preacher & Rucker 2002, Psychological Methods 7(1):19-40). `peer-reviewed`.
    DOI: https://doi.org/10.1037/1082-989x.7.1.19
    用途：系统论证中位数/阈值二分对测量与统计分析的损害，以及‘以同一样本选阈值’带来的循环。

204. Where genotype is not predictive of phenotype: towards an understanding of the molecular basis of reduced penetrance in human inherited disease (Cooper et al. 2013, Human Genetics 132(10):1077-1130). `peer-reviewed`.
    DOI: https://doi.org/10.1007/s00439-013-1331-2
    用途：penetrance 的权威定义：携带某基因型的个体中呈现相应表型的比例；不呈现即 reduced/incomplete penetrance。

205. Incomplete Penetrance and Variable Expressivity: From Clinical Studies to Population Cohorts (Kingdom & Wright 2022, Frontiers in Genetics 13:920390). `peer-reviewed`.
    DOI: https://doi.org/10.3389/fgene.2022.920390
    用途：把 penetrance 明确为二元现象（基因型是否导致预期表型），并区分 incomplete penetrance 与 variable expressivity。

206. raphaelvallat/pingouin. `未标注（开源实现）`.
    链接: https://github.com/raphaelvallat/pingouin
    用途：Python/Pandas 统计包，含 Cohen's d / Hedges g（独立与配对）、配对 t/Wilcoxon、效应量 CI。

207. statsmodels/statsmodels. `未标注（开源实现）`.
    链接: https://github.com/statsmodels/statsmodels
    用途：Python 统计建模库：配对 t 检验、Wilcoxon 符号秩、描述统计与回归，许可证宽松。

208. easystats/effectsize. `未标注（开源实现）`.
    链接: https://github.com/easystats/effectsize
    用途：R 语言效应量包，覆盖 Cohen's d / Hedges g / 配对设计口径。

---

## 依据新增（BC / 模仿学习超参，2026-09-26）

> 来源：`research/reference/bc-hyperparameters.json`（BC 超参：损失权重口径 / optimizer+lr / batch size / 专家轨迹规模）。
> 去重：已与 #1–#208 按 DOI / 标题比对。Kendall 2018 见 #170、GradNorm 见 #171、LeCun Efficient BackProp 见 #179，**均不重复登记**；robomimic 见 #34（arXiv 版，其同行评审版 CoRL 2021 PMLR 164:1678–1690 本次已核验）。以下 6 条为新增。
> 核验：所有 DOI 于 2026-09-26 经 OpenAlex `get_work` 或 PMLR 官方页面解析（作者/年份/卷期页一致）。⚠️ 本文件在本次检索期间被其他子代理并发追加，故编号自当前最大 #208 之后续接（原任务下发的「从 138 起」已被并发写入占用）。

209. Pomerleau D. **Efficient Training of Artificial Neural Networks for Autonomous Navigation.** *Neural Computation* 3(1), 88–97 (1991). `peer-reviewed`.
    DOI: https://doi.org/10.1162/neco.1991.3.1.88
    用途：BC 奠基工作（ALVINN）：通过观看人类驾驶、在 5 分钟内学会控制 Navlab；支撑「专家演示 + 监督回归」为 BC 原型。⚠️ 仅作历史锚点，未含本文所需具体超参取值。

210. Zhao TZ, Kumar V, Levine S, Finn C. **Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware.** *Proceedings of Robotics: Science and Systems (RSS) XIX* (2023). `peer-reviewed`.
    DOI: https://doi.org/10.15607/rss.2023.xix.016
    用途：ACT：动作逐维 z-score 标准化（std clip 1e-2）后单一损失；官方示例 lr=1e-5、batch_size=8、num_epochs=2000、kl_weight=10；真实精细任务仅需约 10 分钟演示。支撑「逐维标准化」与「少量演示即可」的数量级参照。

211. Chi C, Feng S, Du Y, Xu Z, Cousineau EA, Burchfiel B, et al. **Diffusion Policy: Visuomotor Policy Learning via Action Diffusion.** *Proceedings of Robotics: Science and Systems (RSS) XIX* (2023). `peer-reviewed`.
    DOI: https://doi.org/10.15607/rss.2023.xix.026
    用途：官方实现逐动作维度 min-max 归一化到 [-1,1]；训练配置 batch_size=64、AdamW lr=1e-4、weight_decay=1e-6。支撑动作逐维标准化与 batch/lr 区间。⚠️ 期刊扩展版见 IJRR (2024), DOI 10.1177/02783649241273668，未逐页核对。

212. Ren A, Veer S, Majumdar A. **Generalization Guarantees for Imitation Learning.** *Proceedings of the 2020 Conference on Robot Learning (CoRL)*, PMLR 155, 1426–1442 (2021). `peer-reviewed`.
    链接: https://proceedings.mlr.press/v155/ren21a.html
    用途：与本题规模相近的 MLP 模仿学习采用 lr=1e-3、weight decay=1e-5，作为小型 MLP 的 IL 学习率锚点。PMLR 页码已核验；会议录不注册 DOI。

213. Foster DJ, Block A, Misra D. **Is Behavior Cloning All You Need? Understanding Horizon in Imitation Learning.** *Advances in Neural Information Processing Systems (NeurIPS)* (2024). `preprint`（此处登记 arXiv 版；正式版为 NeurIPS 2024）.
    DOI: https://doi.org/10.48550/arxiv.2407.15007
    用途：分析 BC 相对 horizon 的样本复杂度；实验使用约 500 条专家轨迹量级，作为专家数据规模的现代旁证。⚠️ 实验含 Atari 等大动作空间，与本题 2 维动作差异大，仅作数量级参考。

214. Ross S, Gordon G, Bagnell D. **A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning (DAgger).** *Proceedings of the 14th International Conference on Artificial Intelligence and Statistics (AISTATS)*, PMLR 15, 627–635 (2011). `peer-reviewed`.
    链接: https://proceedings.mlr.press/v15/ross11a.html
    用途：证明朴素 BC 存在协变量偏移与误差累积（quadratic horizon dependence），需在线交互纠正；本题 Stage 2 为纯离线 BC，须在论文中显式声明该局限。非超参文献。PMLR 页码已核验。


## 开源「大鱼吃小鱼」项目（工程参考，非学术文献）


> 来源：workbuddy（Olivia）只读精读报告（入库副本 `research/reference/open-source-fish-games-机制对照.md`）。
> **本组为开源项目，非 `peer-reviewed`、亦非 `preprint`，故不得作为「设计依据」，仅作机制对照的 Tier 6 证据。**
> 6 个仓库均于 2026-09-26 以 `git ls-remote` 核验存在，HEAD 记录于下（锁定所读版本）。
> **License 红线**：仅 #215/#218 为 MIT；其余未声明或仅教育用途。全部只作「读机制、自行重写」，**不复制代码与素材**。


215. Test1609. **big-fish-eat-small-fish.** GitHub 开源项目（MIT），核验 HEAD `95aa3c7f`｜非同行评审


   链接: https://github.com/Test1609/big-fish-eat-small-fish


   用途：机制对照（Tier 6 证据，**非设计依据**）：面积守恒生长 `r=√(r²+r_prey²·0.35)`（index.html:371-375）、体型分层生成权重、逃/追不对称检测半径（逃 d<180 / 追 d<300）、NPC 环绕回卷（:293,:355-358）。对照认领表 A2/A4/A5/A6。


216. ahmedehhab. **Feeding-Frenzy-Game.** GitHub 开源项目（仅教育用途（未声明标准许可证）），核验 HEAD `0802918d`｜非同行评审


   链接: https://github.com/ahmedehhab/Feeding-Frenzy-Game


   用途：机制对照：`config/config.js` 分层生成权重与危险物调度（`js/Spawner.js:29-64` 按等级动态调权：同级 ×2.0、高一级 ×1.5、低一级 0.3^diff）。仅供「难度自适应」设想参考；**未采纳入本项目**。


217. tghbrk. **fish-eat-fish.** GitHub 开源项目（未声明许可证），核验 HEAD `0b3fc6ab`｜非同行评审


   链接: https://github.com/tghbrk/fish-eat-fish


   用途：机制对照：三色可食性描边（0.8×可食 / 1.2×危险，`js/enemy.js:228,241`）与 AI 三态状态机 wander/hunt/flee + `stateTimer` 滞后 + 追击扰动（`js/ai-player.js:121-232`）。后者为 ExpertPolicy 平滑化（BC 数据质量）的对照来源。


218. MonkWarrior08. **Interactive_Fish_Eating_Game.** GitHub 开源项目（MIT），核验 HEAD `cf3cdf30`｜非同行评审


   链接: https://github.com/MonkWarrior08/Interactive_Fish_Eating_Game


   用途：机制对照：**限时追击** `max_chase_time` 180–300 帧（3–5 s @60fps，`fish.py:124,205-208`）超时放弃目标；谱系最严体型门 κ=1.5（`fish.py:145,331`）；NPC 出界即移除+补生成（`fish.py:82-83,323-326`）。对照认领表 A2/A8 与 §12 prey 再生。


219. chen4546. **Fish-Eat.** GitHub 开源项目（未声明许可证），核验 HEAD `afaf787d`｜非同行评审


   链接: https://github.com/chen4546/Fish-Eat


   用途：机制对照：显式边际递减生长 `growth = prey.size × (0.2 − 0.01×size/10)`（`character/FishPlayer.py:142`）与耐力制（移动 −2/帧、静止 +0.5/帧，:111-115）。对照认领表 A3/A4。


220. HuiDBK. **DragonFeast.** GitHub 开源项目（未声明许可证），核验 HEAD `7af27fbe`｜非同行评审


   链接: https://github.com/HuiDBK/DragonFeast


   用途：机制对照：时间驱动生精灵调度器（定时 + 保底数量双触发，`src/game_main.py:310-334`）；障碍物为伤害性事件（`game_settings.py`）——后者支持「障碍=负奖励事件」而非改 Arena 的接法。对照认领表 A7 与 §12。


221. Mihalitsis M, Bellwood DR. **A morphological and functional basis for maximum prey size in piscivorous fishes.** *PLoS ONE* 12(9), e0184679 (2017). `peer-reviewed`.
    DOI: https://doi.org/10.1371/journal.pone.0184679
    用途：**替代物种**最大可吞咽猎物**体高**（depth）= 捕食者 SL 的 **20%（P. forsteri）–27%（C. urodeta）**。**限定条件必须随引**：度量对象是**猎物体高**、物种为 4 种替代掠食鱼（*Cephalopholis urodeta / Paracirrhites forsteri / Pterois volitans / Lates calcarifer*），**不可**倒数为本项目的 `capture_size_ratio κ=1.25`（κ 属**设计选择**，见 `arena/Danio_Arena设计与实现说明.md` §8）。核验：OpenAlex `W2753764258`（2017-09-08；OA gold，CC-BY）。

---

## 待登记（未核验；**P0 债**，2026-09-26 由只读审计 `research/notes/引用登记缺口.md` 提出）

> 本节条目**尚未**按本文件开头第 1–3 条规则完成核验（离线环境无法做 OpenAlex 核验），因此**不占正式编号、
> 不得按 `[bib#n]` 引用**。补完核验后移入正式序列。

~~**（待登记-1）Mihalitsis & Bellwood 2017**~~ ✅ **已核验并登记为 `[bib#221]`（2026-09-26）** —— 见正式序列 221。

**（待登记-2）Arena 生物学调研共 5 组** —— `research/reference/` 下 `zebrafish-escape-capture.md`、`param-basis-biology.md`、
`looming-and-growth.md`、`arena-boundary-collision.md`、`episode-termination-fitness.md` 所引文献**一条都未登记**
（挂账最早见 `research/notes/arena-设计意见-给李辰钊.md`）。**影响**：凡据其取值的**冻结参数**，其依据目前不可核。

**（待登记-3）`docs/参数总表.json` 的 `reference_magnitudes`** —— 其中 6 条来源（Fuiman & Webb 1988 / Plaut 2000 /
Fuiman 1986 / Budick & O Malley 2000 / Patterson 2013 / McKee & McHenry 2020）未登记。

**（待登记-4）License 复核** —— `[bib#217]` `tghbrk/fish-eat-fish` **未声明许可证**，其机制曾在
`research/notes/契约决策记录.md`「开源机制对照的采纳」中被列为可借鉴项。**已核实未被实现**：
`arena/policies.py` 无状态机（ExpertPolicy 仍是简单加权规则），故未复制代码；仍须补声明，
见 `docs/declaration/THIRD_PARTY.md`（现为空表）。

**（待登记-5）前端候选资源** —— 来源 `research/reference/前端可用资源-调研与选型.md`（Tier6 入库副本）。
**采用前**须逐项登记（License 与版本）：Kenney Fish Pack 2.0（CC0）、8bitcn-ui（MIT）、SeqViz（MIT）、
cytoscape-fcose / cytoscape-dagre（MIT）、Press Start 2P（OFL）、Lospec 调色板（逐页核实）、
OpenGameArt「Cute Fish Sprites」（OGA-BY 3.0，**须署名**）、TensorFlow Playground（Apache-2.0，仅作交互参考不引代码）。
