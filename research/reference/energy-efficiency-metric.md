# Energy Efficiency 口径检索

> 由 `research/reference/energy-efficiency-metric.json` 摘要生成（原始 JSON 为权威）。

- 检索时间：2026-09-26
- 主题：EvoGenesis Arena fitness 的 `energy efficiency`（权重 0.20）口径——行为/生态能量学（净能量获取率、cost of transport、游泳代谢成本）+ 鱼类游泳经济性 + RL/机器人能耗项与 reward shaping + fitness 分量归一化到 [0,1]
- 范围：只采集可核实来源，为 `core/核心机制与数据流.md` §10 #12（口径未定义）与 `evolution/遗传繁殖与演化模型.md` §6/§阅读问题 2（归一化方式未定）给出候选定义与推荐公式。**仅采集与评估，未修改任何代码或配置。**
- 来源概述：同行评审（DOI 经 OpenAlex 核验）：Stephens & Krebs 1986（专著）、Ydenberg 1994（Behav. Ecol.，203 引）、Charnov 1976（Theor. Popul. Biol.，5463 引）、Brett 1964（JFRBC，2149 引）、Schmidt-Nielsen 1972（Science，960 引）、Tucker 1970（Comp. Biochem. Physiol.，379 引）、Videler & Nolet 1990（Comp. Biochem. Physiol. A，124 引）、Weihs 1973（Nature，165 引）、Palstra 2010（PLoS ONE，158 引）、Jahn & Seebacher 2022（JEB，29 引）、Guo 2021（Front. Mar. Sci.，15 引）、Madenjian 2024（Encyclopedia of Fish Physiology，2 引）、Chabot 2016（J. Fish Biol.，681 引）、West et al. 2001（Nature，1207 引）、West & Brown 2005（JEB，808 引）、Hwangbo 2019（Sci. Robotics，1511 引）、Deb 2002 NSGA-II（IEEE TEC，49700 引）。预印本/会议：Liang 2025（ICRA，arXiv:2403.20001）、Mahankali 2024（ICRA，EIPO）、Fu 2021（CoRL，arXiv:2111.01674）、Ng et al. 1999（ICML）。reviewed preprint：eLife 90352。GitHub 侧未找到可复用代码。

## 项目侧事实（结论中公式所用）

| 量 | 值/来源 |
|---|---|
| 能量递推 | `E' = clip(E − C_base − C_move·v² + R_food·1[本步捕获], 0, E_max)`（`arena/Danio_Arena设计与实现说明.md` §6；`env.py::step`） |
| `e_max` / 出生能量 | 1.0 / 1.0（`entities.py` 出生置 `e_max`） |
| `base_cost_per_step` | 0.0008 |
| `movement_cost_scale` | 0.0015 |
| `food_reward` | 0.12 |
| Δt | 0.05 s（30 s / 600 步） |
| `per_fish_log` 可用键 | generation / encounters / captures / predator_encounters / escape_successes / collisions / energy_trajectory / size_trajectory / survival_steps / motor_commands |
| fitness | `F = 0.35S + 0.25P + 0.20E + 0.20Q`，四分量先归一化（归一化方式未定） |

## 结论（推荐）

1. **【推荐定义公式（主）】** 采用生态学的**净能量获取率**货币（Stephens & Krebs 1986 的 `net rate of energy gain = (E_gain − E_cost)/T`；Ydenberg 1994 的 long-term net rate）。用本项目量逐鱼写为：

   \[
   r_i=\frac{R_{food}\cdot captures_i-\sum_{t=1}^{T_i}\left(C_{base}+C_{move}v_{i,t}^2\right)}{T_i},
   \qquad T_i=survival\_steps_i
   \]

   `v_{i,t}` 取自 `per_fish_log.motor_commands`；`R_food=0.12`、`C_base=0.0008`、`C_move=0.0015`、`E_max=E(0)=1.0`。分母 `E_spent,i = C_base·T_i + C_move·Σ v²` 即鱼类游泳代谢成本（Brett 1964；Videler & Nolet 1990；Palstra 2010 的量-速框架）。**等价式**：当能量更新中的 `clip(·,0,E_max)` 未触发时，由递推可证 `r_i = (E_i(T_i) − E_max)/T_i`（`E_i(T_i)` 取 `energy_trajectory` 末值），可用于无 `motor_commands` 的旧日志。

2. **【可选简化式】** 若只保留 `energy_trajectory` 与 `survival_steps`，用 `r_i^simple = (E_i(T_i) − E_max)/T_i`，再对同代 cohort 做 min-max 归一化。它在无 clip 时与主式恒等；clip 触发（饿死 E→0 / 吃满 E_max）时二者有偏，须在报告中注明。再退化到 `captures_i / max(T_i,1)` 只能占位，**不属于能量效率口径**（缺成本项），不得当最终定义。

3. **【归一化到 [0,1]】** 推荐

   \[
   Q_i=\frac{r_i-\min_j r_j}{\max_j r_j-\min_j r_j},
   \]

   min/max 取同一 cohort（同 `environment_id`、`episode_steps=600`、N=48、同 seed 协议）内被评个体；这是进化多目标按理想点/最差点归一化目标的成熟做法（Deb et al. 2002, NSGA-II）。约定：若 `max r = min r`（全员相等），`Q_i` 取固定值（建议 0 或 0.5）**并在文档一次性定稿，禁止代码隐式决定**。

4. **【推荐直接用的口径/来源】** 生态学有据：(a) 净能量获取率 (E_gain−E_cost)/T——Stephens & Krebs 1986 + Ydenberg 1994；(b) 边际价值/收益率——Charnov 1976；(c) 代谢成本随速上升、SMR/活跃代谢分离——Brett 1964 + Chabot 2016；(d) 单位距离成本 COT 与 Uopt 最小——Schmidt-Nielsen 1972 + Videler & Nolet 1990 + Weihs 1973 + Guo 2021 + Palstra 2010；(e) 鱼类能量收支恒等式 `Consumption = Respiration + Waste + Growth`，用于校验 r_i——Brett & Groves 1979 / Madenjian 2024。工程有据：(f) [0,1] 目标归一化——Deb et al. 2002。

5. **【仅作参考（需改造，不能直接当 0.20 分量）】**
   - Ydenberg 效率比率 `η_i = R_food·captures_i / E_spent,i` 是纯"收益/支出"，**忽略时间且被"少动少花"激励**；Ydenberg 1994 摘要本身即指出效率与速率是两种货币。它会奖励"吃一口就饿/被捕食"的个体，而 survival 已是独立 0.35 分量，再用 η 会语义重叠并鼓励静止。**建议把 η_i 与 COT 作为诊断量随原始 r_i 一起记录，不进加权和。**
   - 游泳经济/COT 诊断：`COT_i = E_spent,i / D_i`，`D_i = Σ_t v_{i,t}·Δt`，单位是"模型能量/世界单位"而非 J/kg/m，只能作相对量；其倒数即 Palstra 2010 的 swimming economy，最小值对应 Uopt（Videler & Nolet 1990；Guo 2021）。
   - RL/机器人口径：Liang 2025（distance-averaged energy consumption）、Fu 2021（仅能耗最小化涌现步态）、Mahankali 2024（EIPO：能耗作次要约束，避免与任务奖励互相拉扯）证明"能耗可作为目标/惩罚项"，但其任务方向与本项目相反，只借"按距离/按步平均"的构造。
   - 若未来把能耗并入单一代价：Ng et al. 1999 提醒辅助塑形项可能改变最优策略，**务必单独作为 fitness 分量**。

6. **【生态学 vs 工程口径的界限】** 生态学有据：货币形式、代谢成本随速上升、COT 随速呈 U 形并在 Uopt 最小、`COT=TEE/speed`（eLife 90352）。纯工程选择：`v²` 指数、`C_base/C_move/R_food` 数值、`E_max=1.0`、`Δt=0.05`、`episode_steps=600`、min-max 以本代 cohort 为基准。文献中代谢-速度幂指数跨研究落在 1.1–3.0（sprat 综述 PMC6874314，本仓库已登记），流体阻力功率基线为 v³（Schultz 2002）；故 v² 合理但**必须标注为选择而非定律**。

7. **【三级结论】**
   - **推荐直接用**：(a) 主定义 `r_i=(R_food·captures_i − E_spent,i)/T_i` 的概念与来源；(b) 等价式 `r_i=(E_i(T_i)−E_max)/T_i`；(c) min-max 归一化到 [0,1]（Deb 2002）并强制同 cohort 比较。
   - **仅作参考**：(d) Ydenberg 比率 η 与 COT 诊断量；(e) RL 按距离平均能耗（Liang 2025；Fu 2021；Mahankali 2024）；(f) West 2001 / West & Brown 2005 的代谢标度。
   - **不建议**：(g) 把 RL 的 "energy efficiency / sample efficiency"（达到性能所需样本数）与本项目混用；(h) min-max 后的 Q 跨代跨环境直接比较；(i) 把 v² 当鱼类游泳定律、把四系数当生物测量值；(j) 未经校准使用"理论上界"归一化（无外部来源定义本项目上界，属 AI 填空）。

8. **【没找到 / 已知缺口】**
   - 未找到与本项目完全一致的外部口径：`clip(E−C_base−C_move·v²+R_food·1[capture],0,E_max)` 是项目特有构造。
   - 未找到为该项目钦定的归一化上界；min-max 只是机制先例，上界须由本项目文档定稿。
   - Jahn & Seebacher 2022 与 Atlantic salmon 热驯化 JEB 文全文取不到，故 `net COT = (代谢率 − SMR)/速度` 只按标准用法陈述并标注待核；`gross COT = TEE/speed` 有 eLife reviewed preprint 显式原文支持。
   - 任务清单 "West 2001" 经核为 West, Brown & Enquist 2001 Nature《A general model for ontogenetic growth》(DOI 10.1038/35098076)，已补正；它与 West & Brown 2005 都不定义 COT。
   - arXiv MCP 本次对 1707.06347 / 2403.20001 返回错误，PPO 未作条目；reward shaping 改用已核验的 Ng et al. 1999。
   - GitHub：`gh search repos` 对 "cost of transport" / "energy efficient reinforcement learning" 未返回可复用、含许可证与维护记录的代码，故无 repo 条目，也不建议引入外部依赖。

9. **【下一步建议（人工确认后再改文档/代码）】**
   - (a) 在 `evolution/遗传繁殖与演化模型.md` §6 与 `core/核心机制与数据流.md` §10 #12 写明 Q 公式、`r_max=r_min` 约定、cohort 边界与状态，**再动代码**（AGENTS「禁止 AI 填空」）。
   - (b) 每鱼落盘原始 `r_i`（及可选 `η_i`、`COT_i`），与 `Q_i` 成对出现，供跨代审计；复合 fitness 只用 `Q_i`。
   - (c) 若坚持 `design-basis-metrics.md` 条目 4 的比率式作为 Q，须在文档承认其"奖励低支出/短命"偏置；否则推荐改用本文件净速率式。
   - (d) 对 v² 指数与四系数做同 seed、同预算的敏感度分析，作为赛题"结果对比/稳定性"证据。
   - (e) 把本文件登记进 `research/notes/bibliography.md`（未登记即引用＝缺陷）。

## 条目

| # | 名称 | 类型 | 来源 | 链接 | 相关度 | 摘要 |
|---|---|---|---|---|---|---|
| 1 | Foraging Theory (Stephens & Krebs 1986) | book | Princeton University Press | https://press.princeton.edu/books/paperback/9780691084428/foraging-theory | 5 | 最优觅食教科书；定义净能量获取率 (E_gain−E_cost)/T 与效率 E_gain/E_cost。 |
| 2 | Time and energy constraints and the relationships between currencies in foraging theory (Ydenberg et al. 1994) | paper | Behavioral Ecology | https://doi.org/10.1093/beheco/5.1.28 | 5 | 并置效率(gain/spent)与长期净速率(净能量/时间)；摘要指出实测策略常聚集于 efficiency 而非 rate。 |
| 3 | Optimal foraging, the marginal value theorem (Charnov 1976) | paper | Theoretical Population Biology | https://doi.org/10.1016/0040-5809(76)90040-x | 3 | 边际价值定理：以单位时间净能量收益为货币的最优觅食。 |
| 4 | The Respiratory Metabolism and Swimming Performance of Young Sockeye Salmon (Brett 1964) | paper | J. Fisheries Research Board of Canada | https://doi.org/10.1139/f64-103 | 5 | 鱼类游泳代谢率随速度对数增长；SMR 与活跃代谢差约 10–12 倍。 |
| 5 | Locomotion: Energy Cost of Swimming, Flying, and Running (Schmidt-Nielsen 1972) | paper | Science | https://doi.org/10.1126/science.177.4045.222 | 5 | COT/单位距离能量成本的经典框架。 |
| 6 | Energetic cost of locomotion in animals (Tucker 1970) | paper | Comparative Biochemistry and Physiology | https://doi.org/10.1016/0010-406x(70)91006-6 | 4 | 运动能量成本（单位距离）的早期系统比较。 |
| 7 | Costs of swimming measured at optimum speed (Videler & Nolet 1990) | paper | Comp. Biochem. Physiol. A | https://doi.org/10.1016/0300-9629(90)90155-l | 5 | 单位距离成本在 Uopt 最小的经典结论与尺度效应。 |
| 8 | Optimal Fish Cruising Speed (Weihs 1973) | paper | Nature | https://doi.org/10.1038/245048a0 | 4 | 流体力学推导鱼类巡游最优速度（单位距离能量成本最小）。 |
| 9 | Establishing Zebrafish as a Novel Exercise Model (Palstra et al. 2010) | paper | PLoS ONE | https://doi.org/10.1371/journal.pone.0014483 | 4 | 斑马鱼游泳经济与 COT 实测；Ucrit=0.548 m/s（18.0 BL/s）。 |
| 10 | Variations in cost of transport and their ecological consequences: a review (Jahn & Seebacher 2022) | paper | J. Experimental Biology | https://doi.org/10.1242/jeb.243646 | 4 | COT 综述：运动能耗占比、个体/物种差异、行为补偿机制。 |
| 11 | Fish Specialize Their Metabolic Performance to Maximize Bioenergetic Efficiency (Guo et al. 2021) | paper | Frontiers in Marine Science | https://doi.org/10.3389/fmars.2021.613965 | 4 | 定义 Uopt = gross COT 最小的游泳速度。 |
| 12 | Energy conservation by collective movement in schooling fish (eLife reviewed preprint 90352) | paper | eLife | https://elifesciences.org/reviewed-preprints/90352 | 4 | 斑马鱼群游代谢-速度曲线凹向上；显式给出 COT = TEE / speed。 |
| 13 | Fish bioenergetics modeling (Madenjian et al. 2024) / Brett & Groves 1979 | paper | Encyclopedia of Fish Physiology (Elsevier) | https://doi.org/10.1016/B978-0-323-90801-6.00063-X | 4 | 鱼类能量收支 `Consumption = Respiration + Waste + Growth`；gross growth efficiency。 |
| 14 | The determination of standard metabolic rate in fishes (Chabot et al. 2016) | paper | J. Fish Biology | https://doi.org/10.1111/jfb.12845 | 3 | SMR 测量与术语权威综述，是 net COT / 维护成本的基准量。 |
| 15 | A general model for ontogenetic growth (West, Brown & Enquist 2001) | paper | Nature | https://doi.org/10.1038/35098076 | 3 | 代谢能量在维护与生长间分配的通用模型。 |
| 16 | The origin of allometric scaling laws in biology (West & Brown 2005) | paper | J. Experimental Biology | https://doi.org/10.1242/jeb.01589 | 2 | 代谢率随质量 3/4 幂律综述；不直接定义 COT。 |
| 17 | Learning agile and dynamic motor skills for legged robots (Hwangbo et al. 2019) | paper | Science Robotics | https://doi.org/10.1126/scirobotics.aau5872 | 3 | RL reward 含能耗/力矩惩罚的工程惯例。 |
| 18 | Adaptive Energy Regularization… (Liang et al., ICRA 2025) | paper | arXiv / ICRA 2025 | https://arxiv.org/abs/2403.20001 | 3 | reward 用"按距离平均能耗"，速度自适应调权。 |
| 19 | Maximizing Quadruped Velocity by Minimizing Energy (Mahankali et al., ICRA 2024, EIPO) | paper | IEEE ICRA 2024 | https://srinathm1359.github.io/eipo-locomotion | 3 | 能耗作次要约束的约束优化；指出加权求和会互相拉扯。 |
| 20 | Minimizing Energy Consumption Leads to the Emergence of Gaits (Fu et al., CoRL 2021) | paper | arXiv / CoRL 2021 | https://arxiv.org/abs/2111.01674 | 3 | 仅以能耗最小化为奖励即可涌现步态。 |
| 21 | Policy Invariance Under Reward Transformations (Ng, Harada & Russell 1999) | paper | ICML 1999 / DBLP | https://dblp.org/rec/conf/icml/NgHR99 | 2 | 势函数塑形不改变最优策略；辅助项设计需谨慎。 |
| 22 | A fast and elitist multiobjective genetic algorithm: NSGA-II (Deb et al. 2002) | paper | IEEE Trans. Evolutionary Computation | https://doi.org/10.1109/4235.996017 | 4 | 按理想点/最差点归一化目标的标准先例，支撑 [0,1] 归一化机制。 |
