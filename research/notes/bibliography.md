# 核心参考文献

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
