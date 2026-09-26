# bibliography.md 登记报告（GA 选择方法）

- 搜索/写入时间：2026-09-26
- 目标文件：`research/notes/bibliography.md`
- 依据文件：`research/reference/ga-selection-methods.json`（刚核验，含 7 条文献的存在性 / DOI / 卷期页 / 评审状态 / 断言支撑结论）
- 写入方式：**只追加**；既有 #1–#130 未改动
- 去重基准：#1–#130（按 DOI / 标题全文检索）
- 本次搜索时间（meta）：2026-09-26

## 一、结果摘要

- **新增编号区间：#131–#137（共 7 条）**
- 新增章节标题：`## 依据新增（GA 选择方法，2026-09-26）`
- **已存在清单：无**（7 条点名词条在 #1–#130 中均无 DOI / 标题命中）
- **未登记清单：无**（点名的 7 条全部可核实并已登记）
- 说明：`ga-selection-methods.json` 的 `stronger_anchors` 中另有 4 条（Grefenstette & Baker 1989、Katoch et al. 2020 等）与 2 条「仅作参考」条目（Goldberg 1990、Miller & Goldberg 1995），本次任务未点名，**不登记**（见第四节）。

## 二、新增条目（#131–#137）

| 编号 | 作者/年份 | 标题 | venue | 状态 | DOI/链接 | 核验 |
|---|---|---|---|---|---|---|
| 131 | Holland 1975 / 1992 | Adaptation in Natural and Artificial Systems (2nd MIT ed.) | MIT Press（orig. Univ. Michigan Press 1975） | `未标注`（专著） | 10.7551/mitpress/1090.001.0001 | OpenAlex `batch_resolve_references`（W1497256448，book，1992，引 41315）✔ |
| 132 | Goldberg 1989 | Genetic Algorithms in Search, Optimization, and Machine Learning | Addison-Wesley, Reading, MA | `未标注`（专著） | archive.org/details/geneticalgorithm0000gold；ISBN 0-201-15767-5 | 出版方/Internet Archive 页面核验 ISBN；OpenAlex 无干净 book 记录（记录为 book-review / article），故不引 OpenAlex |
| 133 | Baker 1985 | Adaptive Selection Methods for Genetic Algorithms | Proc. 1st ICGA, 101–111 | `未标注`（会议论文） | dl.acm.org/doi/proceedings/10.5555/645511 | OpenAlex `biblio`：first_page=101, last_page=111（W1787544972，1985）✔ |
| 134 | Whitley 1989 | The GENITOR Algorithm and Selection Pressure: Why Rank-Based Allocation of Reproductive Trials is Best | Proc. 3rd ICGA, 116–123 | `未标注`（会议论文） | dl.acm.org/doi/10.5555/645512.657257 | OpenAlex `biblio`：first_page=116, last_page=123（W1550894544，1989）✔ |
| 135 | Goldberg & Deb 1991 | A Comparative Analysis of Selection Schemes Used in Genetic Algorithms | Foundations of Genetic Algorithms 1, 69–93, Morgan Kaufmann/Elsevier | `peer-reviewed`（书章） | 10.1016/b978-0-08-050684-5.50008-2 | OpenAlex `batch_resolve_references`（W1568834902，book-chapter，1991，页 69–93，引 2418）✔ |
| 136 | Blickle & Thiele 1996 | A Comparison of Selection Schemes Used in Evolutionary Algorithms | Evolutionary Computation 4(4), 361–394 | `peer-reviewed` | 10.1162/evco.1996.4.4.361 | OpenAlex `batch_resolve_references` + `get_work`（W2071806120，article，1996，4(4):361–394，引 602）✔ |
| 137 | Eiben & Smith 2015 | Introduction to Evolutionary Computing (2nd ed.) | Springer, Natural Computing Series | `未标注`（教科书） | 10.1007/978-3-662-44874-8 | OpenAlex `batch_resolve_references`（W2774185825，book，2015，引 1230）✔ |

### 断言与状态依据（摘自 `ga-selection-methods.json`，本次未新增断言）

- #133 Baker 1985：rank selection **首提**——由 #135 Goldberg & Deb 1991 明文确认（"introduced the notion of ranking selection to genetic algorithm practice"）。
- #134 Whitley 1989：rank-based selection **系统论证**，**非**首提；与 #133 区分。
- #135 Goldberg & Deb 1991：支撑「比例选择依赖尺度、需 scaling/ranking」；**明确不得**写成「提出 sigma scaling」（原文全文无该词）。
- #136 Blickle & Thiele 1996：证明 binary tournament（t=2）与**最大线性排名**（s=2 / η⁻=0）期望适应度分布等价（原文 "identical"，强于 "≈"）。
- #137 Eiben & Smith 2015：§5.2.4 明文 tournament 对 absolute fitness 不变（translation/transposition invariance）。

## 三、已存在（不重复登记）

**无。** 按下列键在 `bibliography.md` #1–#130 中全文检索，均无命中：

- DOI：`10.7551/mitpress/1090.001.0001`、`10.1016/b978-0-08-050684-5.50008-2`、`10.1162/evco.1996.4.4.361`、`10.1007/978-3-662-44874-8`。
- 标题/作者关键词：`Holland`、`Goldberg`（除 #132 本次加入外既无）、`Whitley`、`Blickle`、`Thiele`、`Eiben`、`Adaptation in Natural and Artificial Systems`、`GENITOR`、`sigma`、`tournament`、`rank`。
  - 注：`#60` 的 `Thiele TR`（不同人，斑马鱼视觉）、`#82` 的 `Baker CVH`（不同人，进化发育）与本次 #134/#133 作者无关，不构成重复。

## 四、未登记清单（附原因）

| 条目 | 原因 |
|---|---|
| **Forrest 1985**（sigma scaling 首提，Univ. Michigan 未发表技术文档） | 本次任务未点名；`ga-selection-methods.json` 明示其「unpublished / 技术文档」且未提供可核实稳定链接。按硬约束「无法核实的不登记」处理。正文若需 sigma scaling 归属，可改为引 #132 Goldberg 1989（sigma truncation）+ #135（尺度依赖）的组合作支撑，或另行取证后补登。 |
| **Goldberg 1990**（Complex Systems 4(4):445–460，Boltzmann tournament） | JSON 列为「仅作参考」；Complex Systems 不注册 DOI。本次未点名，不登记。 |
| **Miller & Goldberg 1995**（Complex Systems 9(3):193–212） | JSON 列为「仅作参考」，且不支撑「尺度无关」显式命题。本次未点名，不登记。 |
| **Grefenstette & Baker 1989**（Proc. 3rd ICGA） | JSON `stronger_anchors` 自述「可选补充；本次未独立核验 DOI/页码」。本次未点名，不登记。 |
| **Katoch et al. 2020**（Multimedia Tools and Applications 80(5):8091–8126） | JSON 列为「仅作近年综述补充锚点」。本次未点名，不登记。 |

> 说明：以上 5 条不是「核实失败」，而是**不在本次点名范围**或 JSON 自述仅作参考；如需引用，应另起一次登记并补足核验。

## 五、风险与待验证

1. **#134 Whitley 1989 页码著录冲突（重要）**：ACM DL 与 OpenAlex `biblio` 记 **116–123**，SCIRP/Springer 等大量文献记 **116–121**。本表择 **116–123**（一手著录）并在条目内标注冲突；正式 BibTeX 前须按目标期刊格式核实，或查 ICGA'89 会议录原书。
2. **#131 Holland 版本（建议）**：以 1992 MIT 重印版 DOI 登记，正文引用时须写明「1975 原版 / 1992 重印版」口径；本次未逐句核对原书正文，只作经典锚点。
3. **#132 Goldberg 1989 无 DOI（重要）**：以 Internet Archive 稳定链接 + ISBN 登记；正文引用须引纸质版书目（Addison-Wesley, Reading, MA, 1989）。
4. **#135 sigma scaling 归属（阻断级纠正已落实到条目）**：不得把「sigma scaling 提出」归给 Goldberg & Deb 1991；应归 Forrest 1985（首提）/#132 Goldberg 1989（sigma truncation）。
5. **#136 参数精度（建议）**：免费预印本（ETH TIK-Report 11, 1995）为 OCR 扫描、定理参数符号乱码；引用精确参数（s=2 / η⁻=0）时以 MIT Press 正式版为准；等价命题不可推广到任意线性排名参数。
6. **#133/#134 评审状态（重要）**：两条 ICGA 会议论文的评审程序本次未获独立证据，按 `未标注` 登记，**不得**作为「peer-reviewed 设计依据」使用；其内容归属（首提 / 系统论证）由 #135 明文转述支撑。

## 六、与上游文档的一致性

- 本记录为**过程证据**（Tier 6），不构成契约；文献事实以 `research/notes/bibliography.md` 为唯一来源。
- 未新增任何参数取值、公式或数值；`ga-selection-methods.json` 中的核验结论（含 sigma scaling 归属纠正）已按原文转写，未夸大。
