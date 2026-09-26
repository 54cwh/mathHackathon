# 细胞类型规范调研（celltype-specification）

> 检索时间：2026-09-26 ｜ 任务：裁决 EvoGenesis #14 —— RGCD §6（产出 type）与 DanioNet §1（六类功能语义）谁是「细胞类型」的 owner。
> 数据文件：`research/reference/celltype-specification.json`（17 篇同行评审文献 + 4 个 GitHub 仓库，含逐条来源与核验指标）。

## 一、中文摘要

本次检索要回答三个问题：发育中细胞命运如何被建模、真实神经「细胞类型」是连续还是离散、以及把发育得到的离散 type 映射到功能类别时的惯例与陷阱。

**1. 发育中的 fate specification 有成熟的建模惯例，且「渐变输入 → 离散命运」是公认结构。** Wolpert 1969 的「位置信息 + 发育能力（competence）」、Turing 1952 的反应–扩散、Ashe & Briscoe 2006 与 Rogers & Schier 2011 的形态原梯度解读，共同构成「位置/信号 → 区域特异 fate」的传统。在 GRN 层面，Huang et al. 2007 用分岔动力学证明 fate 是调控网络的多稳态吸引子；Huang 2009 与 Moris et al. 2016 用「表观遗传景观」刻画命运状态，并明确指出真实命运决定经历**连续、可逆的过渡态**，不是瞬间硬开关。Becskei et al. 2001 则给出「正反馈把渐变响应转成二值分化」的实验机制。因此，RGCD §6 的 `softmax`（渐变概率）→ `argmax`（离散 type）在结构上属于主流惯例，但 `argmax` 是理想化，须标注。

**2. 真实神经「细胞类型」是多模态、非单一权威的分类，功能类与分子类不重合。** Zeng & Sanes 2017（Nature Reviews Neuroscience）系统指出：cell type 可由转录组、形态、电生理、连接、功能等多个模态定义，各模态之间**并不一一对应**，至今无单一权威分类。Yuste et al. 2020 的社区共识文件要求命名显式分级、避免维度混淆；Petilla 2008 在 GABA 能中间神经元上已示范「形态/电生理/分子/连接」四维标签互不重合；Arendt et al. 2016 把 cell type 定义为进化保守的**核心调控复合体**，与功能角色属不同层级。斑马鱼方面，Kunst et al. 2019 的幼鱼全脑细胞分辨率图谱显示真实类型远超 6 类。也就是说：**「sensory / motor / interneuron」是功能角色，不是分子细胞类型。**

**3. type → 功能的映射需要显式声明，且不能双向定义。** Richter & Schneidman 2025（即已有 `[bib#4]`）用神经元 cell type、出生时间、胞体距离、互惠、修剪等少量特征生成线虫 connectome，发现**只需很少的 cell type**即可预测突触存在——这支撑了 RGCD §8 用 type 兼容矩阵 `z_i^T C z_j` 的合理性，但也说明 type 是「生成连接的有效特征」，不等于功能标签。Perin et al. 2011 同样表明连接概率可由可预测的节点分组规则描述。

## 二、推荐结论

### (a) Owner 裁决：**产出归 RGCD §6，语义归 DanioNet §1**（推荐直接用）

| 归属 | 内容 | 定位 |
|---|---|---|
| `development/RGCD数学模型.md` §3/§6 | `c_domain` 偏置矩阵、`l_i = U g_i + c_domain(i)`、`z_i = softmax(l_i)`、`type_i = argmax_k z_ik`；domain(6)↔type(6) 的对应与 ordering | **产出（producer）**：定义 type 如何被算出 |
| `connectome/DanioNet设计规范.md` §1/§5 | 六类功能定义（Sensory/Prey/Threat/Integrator-Memory/Inhibitory/Motor）、viability「每类至少一个」、Motor 的 left/right 标记与左右竞争 | **语义（consumer）**：定义 type 在网络上承担什么功能 |

**理由：**
1. **契约闭环**：`g_i`（§4 GRN）、`c_domain`（§3）、`z_i`（供 §8 的 `z_i^T C z_j`）全在 RGCD 内部，产出方天然是 owner。
2. **文献归属**：由 GRN 动力学决定 fate 属发育模型（Davidson & Erwin 2006；Karlebach & Shamir 2008；Huang et al. 2007）。
3. **功能类不能由发育方定义**：功能分类与分子/转录组分类不一一对应（Petilla 2008；Zeng & Sanes 2017；Yuste 2020），功能语义必须由消费它的 DanioNet 定义。

### domain(6) ↔ type(6) 的对应写在哪

**写在 `development/RGCD数学模型.md` §3/§6，且必须写成「competence 先验，而非同一性」。** §6 原文已声明 domain 只保证 developmental competence，最终 type 仍由 `U g_i` 决定。因此：

- `c_domain` 是一个 6×6 的偏置矩阵，其行/列 ordering 即 domain↔type 的对应约定，应在 RGCD 内冻结并进入 `schemas/`。
- DanioNet §1 **只引用** RGCD 的 type token，不复制、不重定义该对应关系。
- 若两处各写一版，即触发 AGENTS「边界对象唯一 owner、禁止循环引用」的 §10 缺陷。

### 是否有必要把「功能类」改称「功能投影」

**建议改，但属设计选择而非外部强制。**（推荐直接用，成本权衡见下）

- **文献依据**：真实 cell type 是多模态分类、功能仅其中一维（Petilla 2008；Zeng & Sanes 2017；Yuste 2020）；Arendt et al. 2016 的 cell type 定义与功能角色不同层。DanioNet §1 自己也已声明六类是功能抽象。
- **改名收益**：消除「RGCD 的 `type_i`（潜在/分子样标识）」与「DanioNet 的『细胞类型』（功能角色）」两级同名混淆。
- **最低成本方案**：不必全局重命名 token。只需在 `docs/` 术语表加一行——「本项目 `cell type/type_i` = 潜在类型标识；DanioNet 六类 = 功能投影」，并要求论文正文统一写「功能投影」。
- **无外部文献强制改名**：文献只强制「不要把功能类等同于分子细胞类型」，不强求某个中/英文字面。

### 需标注的风险点（仅作参考，非阻断）

1. **`argmax` 是离散化理想化**：真实 fate 是连续谱、有可逆过渡态（Moris et al. 2016；Zeng & Sanes 2017）。建议 §6 增加限定，并报告 `z_i` 熵/最大概率作「命运确定性」诊断。
2. **六类 ≠ 真实斑马鱼细胞类型**：Kunst et al. 2019 显示真实类型远超 6 类；正式论文须保留「功能抽象」限定语，不可声称等同真实细胞类型。
3. **不建议由 DanioNet 反向定义 type 产出规则**（softmax 温度、K 值等），否则出现两个 owner。

## 三、未找到 / 缺口（诚实声明）

- **arXiv 通道本次不可用**：`arxiv_search_papers` 在检索窗口内持续返回 HTTP 406，预印本层完全未覆盖。若存在 2025–2026 关于「GRN → cell type 生成式模型」的最新预印本，本次未纳入。建议 arXiv MCP 恢复后补检。
- **无可直接复用的开源实现**：GitHub 上找到的 GRN/命运相关仓库（SCENIC、SERGIO、ATLANTIS、CEFCON）均为 **scRNA-seq 推断工具**，与本项目「AKG 基因组 → motif GRN → softmax 命运分类 → type 兼容连接组」的生成式方向相反或无接口，且多为 R/MATLAB 或 GPL-3.0，**不建议引入**（详见 JSON items，relevance 1–2）。
- **「功能投影」是项目自造术语**：文献提供的是「功能类 vs 分子类」的概念区分，未使用该中文词；使用时须说明是本项目命名约定，不声称文献术语。

## 四、给文档的动作建议（供用户裁决，不擅自改文档）

1. `development/RGCD数学模型.md` §6：补一句「softmax→argmax 为离散化约定，需报告 `z_i` 熵」；§3/§6 明确 domain↔type 为 `c_domain` 先验而非同一性。
2. `connectome/DanioNet设计规范.md` §1：保留「功能抽象」限定 ；将标题/正文的「六类神经元」在术语上显式标为「功能投影」，并引用 Petilla 2008 / Zeng & Sanes 2017 / Yuste 2020。
3. `research/notes/bibliography.md`：若采纳上述引用，需把本次新增文献登记为 `[bib#n]`（当前未登记不得进论文）。
4. `docs/设计依据审计.md` 表 3「六 developmental domains 分类」行：可补充「domain↔type 为 competence 先验」的处置说明。
