# 参数依据调研（工程参数）

> 对应 JSON：`research/reference/param-basis-engineering.json`
> 搜索时间：2026-09-26
> 对象：`docs/参数总表.json` 表 D 中 12 个参数
> 检索来源：OpenAlex、arXiv 全文、Tavily（论文 PDF / 官方文档）、GitHub CLI（仓库与源码）
> 限制：本次 arXiv MCP 的 `search_papers` 持续返回 HTTP 406，改用 `download_paper` 的 HTML 抓取与第三方索引；GitHub raw 直链被拦截处改用 `gh api` 读文件。

---

## 结论速览

| 参数 | 当前值 | 常见范围 / 实例 | 判定 | 置信度 |
|---|---:|---|---|---|
| `bp_per_haplotype_chromosome` | 128 | 紧凑人工基因组 50–10⁴ bases（Avida 50；Banzhaf ARN 1000–10000） | 在范围内 | 中 |
| `n_motifs` | 8 | 无 | **无依据** | 低 |
| `grn_dim` | 8 | GRN 节点 2–20+（Mehra & Hintze N=20；Banzhaf ARN 2–19） | 在范围内 | 中高 |
| `development_steps` | 12 | NCA 形态发生 10–50；GRN 收敛 100–1000 | 偏小 | 中 |
| `grn_rho` | 0.35 | leaky/EMA 0.1–1.0；GRN 实例 0.2 | 在范围内 | 中高 |
| `initial_precursors` | 24 | substrate 10–64（5×5=25 常见）；发育起始细胞 1–数个 | 在范围内（口径见下） | 中 |
| `world_width, world_height` | 100, 60 | 同类环境均为正方形 | **无依据** | 低 |
| `sim_hz` | 20 | 20–100 Hz；20 Hz 为标准 | **在范围内** | 高 |
| `episode_seconds` | 30 | 20–50 s | 在范围内 | 中高 |
| `population_size` | 48 | NEAT 150；GA 50–200；De Jong 50 | 偏小 | 中高 |
| `selection_beta` | 3.0 | 无通用值 | **无依据** | 低 |
| `crossover_probability` | 0.5 | 两点交叉 0.6–0.9；均匀交叉 0.5 | 偏小（均匀除外） | 中 |

**一句话**：只有 `sim_hz` 拿到了「多个权威实现共用一个值」的硬依据；`grn_dim`、`grn_rho`、`episode_seconds`、`population_size` 有可靠区间；`bp`、`development_steps`、`initial_precursors`、`crossover_probability` 需要改写表述；`n_motifs`、`world_size`、`selection_beta` 找不到依据，只能标为设计选择。

---

## 一、逐参数依据

### 1. bp_per_haplotype_chromosome = 128（haploid=256）

- **Banzhaf 人工化学 GRN**（Miralavy & Banzhaf, arXiv:2209.04114）用 1000–10000 bases 的基因组，3000 bases 对应约 6 个基因，跑 1000 个 regulatory cycles。
  <https://arxiv.org/abs/2209.04114>
- **Reil 人工基因组模型**（Rohlf & Winkler, arXiv:0908.3610）明确用 4 字母表（对应 ACGT），启动子长 4、基因长 6；基因组长度 S 与基因数 N 满足 `⟨N⟩≈S/λ^{l_p}`。
  <https://arxiv.org/abs/0908.3610>
- **Avida-ED** 数字生物基因组固定为 50 条指令（单基因组）。
  <https://avida-ed.msu.edu/files/curricula/LabBook/Avida-ED_LabBook.pdf>
- **Koulakov / Zador genomic bottleneck**（PNAS 2024）只给定性结论：基因组容量比网络连接规格小若干数量级，无具体碱基数。
  <https://doi.org/10.1073/pnas.2409160121>

**判定**：256 bp（haploid）落在紧凑人工基因组 50–10⁴ 区间内，但比 Banzhaf ARN 小一个量级，接近 Avida 系。**没有任何来源恰好用 128**，应写成「区间内的设计选择」。
**反例提醒**：本项目引文里的 Neural DNA（NDNA）用的是 <400 个可学习参数，不是 ACGT 碱基，因此不能用 NDNA 支持 bp 值。<https://github.com/tejassudsfp/ndna>

### 2. n_motifs = 8 —— 无依据

- Reil 人工基因组只用 **1 个固定启动子 motif**，结合位点由蛋白序列精确匹配决定，没有「8 个 motif 类型」的设定。<https://arxiv.org/abs/0908.3610>
- 生物参照：人类约 1600–2000 个序列特异性 TF，其中约 1211 个已有结合 motif；实际 motif 目录是数百到上千量级。Lambert et al., Cell 2018 <https://doi.org/10.1016/j.cell.2018.01.029>
- NDNA 等 genomic bottleneck 实现根本不扫描 motif。

**判定**：无出处。写论文时只能标「设计选择（未验证）」，并做 motif 数敏感性（如 4/8/16）。

### 3. grn_dim = 8

- **Mehra & Hintze, ALife 2023**：GRN 用 N=20 个基因，N×N 交互矩阵，表达更新 100 步，阻尼 β=0.2。
  <https://www.diva-portal.org/smash/get/diva2:1820427/FULLTEXT01.pdf>（DOI:10.1162/isal_a_00604）
- **Miralavy & Banzhaf**：基因组 1000→2 基因、10000→19 基因（原文表格）。
  <https://arxiv.org/abs/2209.04114>
- **Banzhaf 经典 ARN**（2003）。<https://link.springer.com/chapter/10.1007/978-1-4419-8983-3_4>

**判定**：8 落在人工 GRN 常见的个位数–20 区间，区间支持充分，但无来源恰用 8。

### 4. development_steps = 12 —— 偏小

- Mehra & Hintze：**100 个离散时间步**。<https://www.diva-portal.org/smash/get/diva2:1820427/FULLTEXT01.pdf>
- Miralavy & Banzhaf：**1000 个 regulatory cycles**。<https://arxiv.org/abs/2209.04114>
- HyperNCA（arXiv:2204.11674）：**10 个发育步**长出策略，变形再 **20 步**。<https://arxiv.org/abs/2204.11674>
- Empowered NCA（arXiv:2205.06771）：评估时运行 **N=50 步**。<https://arxiv.org/abs/2205.06771>
- Growing Neural Cellular Automata（Distill 2020）：图案在 **steps 10–20** 成形。<https://distill.pub/2020/growing-ca>

**判定**：12 与 NCA 形态发生（10–20 步）同尺度，但远小于 GRN 收敛研究（100–1000 步）。需说明这是预算截断，并做 12 vs 50 vs 100 的收敛对比。

### 5. grn_rho = 0.35

- Mehra & Hintze 的更新式 `G'_i = G_i − β(G_i − Q_i)` 与本项目 `(1−ρ)g+ρσ(·)` 同构，**β=0.2**。<https://www.diva-portal.org/smash/get/diva2:1820427/FULLTEXT01.pdf>
- Leaky-integrator ESN 综述：leak rate **0.1–1.0**。<https://preprints.opticaopen.org/articles/preprint/Reservoir_Computing_for_Future_Communications_A_Survey_and_Empirical_Study/33253971/1/files/67539177.pdf>
- reservoirnet 示例 **lr=0.1**。<https://computo-journal.org/published-202505-ferte-reservoirnet>

**判定**：0.35 ∈ [0.1,1.0]，与文献常用的 0.2 同量级。注意 ρ 与步数耦合，等效记忆长度 ≈ 1/ρ。

### 6. initial_precursors = 24

- **Risi et al., GECCO 2011**：FS5x5 substrate = **5×5=25 个隐藏节点**；FS10x1 为默认单排 10 节点。<https://groups.csail.mit.edu/EVO-DesignOpt/gecco2011Proceedings/proceedings/p1539.pdf>
- Stanley et al., Artificial Life 2009：以 5×5 网格为例。<https://doi.org/10.1162/artl.2009.15.2.15202>
- **反衬**：经典发育编码从 **单个细胞** 起步——Dellaert & Beer 1996 <https://www.cs.swarthmore.edu/~meeden/DevelopmentalRobotics/dellaert96.pdf>；Astor & Adami 2000 <https://doi.org/10.1162/106454600568834>。

**判定**：24 ≈ 标准 5×5 substrate 的 25，作为「网络起始节点数」在常见范围；但作为「发育生物学初始细胞数」则偏大。论文里必须明确采用哪种口径。

### 7. world_width=100, world_height=60 —— 无依据

- POSGGym PredatorPrey：正方形网格 5×5 / 10×10 / 15×15 / 20×20。<https://posggym.readthedocs.io/en/latest/environments/grid_world/predator_prey.html>
- PettingZoo MPE：归一化正方形连续域 [-1,1]²。<https://pettingzoo.farama.org/environments/mpe/>
- 未找到任何以 100×60（5:3）为默认的连续多智能体或 ALife 仿真。

**判定**：5:3 更像浏览器 Canvas 显示比例驱动的工程选择，应标设计选择并做尺度敏感性。

### 8. sim_hz = 20 —— 依据最硬

- **Gymnasium HalfCheetah-v5**：`dt = frame_skip × frametime = 5 × 0.01 = 0.05` s → 20 Hz。<https://github.com/Farama-Foundation/Gymnasium/blob/main/gymnasium/envs/mujoco/half_cheetah_v5.py>
- MuJoCo half_cheetah.xml：`timestep="0.01"`。<https://github.com/Farama-Foundation/Gymnasium/blob/main/gymnasium/envs/mujoco/assets/half_cheetah.xml>
- **robosuite 文档**：`control_freq = 20, # 20 hz control for applied actions`。<https://robosuite.ai/docs/modules/environments.html>

**判定**：20 Hz（dt=0.05）是运动控制/仿真的标准频率，多有实现依据。→ **推荐直接用**。

### 9. episode_seconds = 30

- Gymnasium HalfCheetah-v4/v5：`max_episode_steps=1000`，×0.05 s = **50 s**。<https://github.com/Farama-Foundation/Gymnasium/blob/main/gymnasium/envs/__init__.py>
- robosuite：`horizon=200`（文档另述评估用 500 步），20 Hz 下分别 10 s / **25 s**。<https://robosuite.ai/docs/modules/environments.html>
- LunarLander-v3 / CarRacing-v3：`max_episode_steps=1000`，折算约 **20 s**。

**判定**：30 s 落在 20–50 s 常见区间。注意「步数→秒」的折算是我的计算（已在 JSON 中标注为推断），各环境 dt 口径不同。

### 10. population_size = 48 —— 偏小

- NEAT / neat-python 示例：**pop_size = 150**（survival_threshold=0.2，elitism=2）。<https://github.com/CodeReclaimers/neat-python/blob/master/examples/xor/config-feedforward>、<https://github.com/CodeReclaimers/neat-python/blob/master/docs/config_file.rst>
- Deep HyperNEAT：**population size = 150**。<https://web.mit.edu/fsosa/www/papers/dhn18.pdf>
- De Jong 标准设置 population **50**；Grefenstette 设置 **30**；GA 经验规则 **50–200**。<https://www.eislab.gatech.edu/people/scholand/gapara.htm>

**判定**：48 略低于 GA 经验下沿、明显低于 NEAT 系 150，接近 De Jong 的 50。可接受但需说明并报敏感性。

### 11. selection_beta = 3.0 —— 无依据

- softmax 定义：β=1/(kT)，β 越大越尖锐，**无推荐值**。<https://en.wikipedia.org/wiki/Softmax_function>
- Boltzmann tournament selection 以 exp(−E/T) 实现并需降温调度，无固定 β。<https://content.wolfram.com/sites/13/2018/02/04-4-5.pdf>
- RL softmax action selection 同样只给机制不给 β 数值。<http://incompleteideas.net/book/first/ebook/node17.html>

**判定**：β 的绝对强度取决于适应度尺度；项目尚未定义适应度归一化方式，故 3.0 无法被证实或证伪。需补「适应度尺度 + β 敏感性」，或改用尺度无关的锦标赛/排名选择。（「β=3 属中等偏强选择」是我的推断，非来源结论。）

### 12. crossover_probability = 0.5 —— 偏小（除非均匀交叉）

- De Jong 标准设置：交叉率 **0.6**；「均匀交叉等破坏性更强的方法应降到 **0.50**」。<https://www.eislab.gatech.edu/people/scholand/gapara.htm>
- Grefenstette 设置：交叉率 **0.9**。
- 综述：常见范围 **0.6–0.9**，默认约 0.7–0.8。<https://algorithmafternoon.com/books/genetic_algorithm/chapter05>

**判定**：0.5 对两点交叉偏低，对均匀交叉正好是建议值。项目注释「最大熵默认假设」在来源中无支撑。若采用均匀交叉，写明 `uniform crossover, p_c=0.5` 即可自洽。

---

## 二、三级结论

**推荐直接用**
- `sim_hz=20`：Gymnasium MuJoCo（dt=0.05）与 robosuite（control_freq=20）双重实现依据。

**仅作参考（需改写表述或补验证）**
- `grn_dim=8`、`grn_rho=0.35`、`episode_seconds=30`：区间有依据，但无来源恰用本项目数值。
- `bp_per_haplotype_chromosome=128`：区间内设计选择，禁止写成「惯例」。
- `initial_precursors=24`：须注明是「substrate 节点数」口径还是「发育起始细胞数」口径。
- `development_steps=12`：补收敛性检查（12/50/100）。
- `population_size=48`：补 24/48/96 敏感性。
- `crossover_probability=0.5`：限定为均匀交叉。

**不建议（找不到依据，勿编引用）**
- `n_motifs=8`、`world_width/height=100/60`、`selection_beta=3.0`：标「设计选择（未验证）」，列入敏感性计划。

---

## 三、需进一步验证的风险点

1. **引文谱系不匹配**：本项目引用的 Neural DNA（NDNA）不用 ACGT 碱基与 motif，而是 <400 个可学习参数。`bp` 与 `n_motifs` 不能引 NDNA。
2. **步数/秒的口径差异**：30 s × 20 Hz = 600 步，与来源默认（1000/500/200 步）各自绑定不同 dt，跨环境换算是我做的推断。
3. **检索覆盖**：arXiv MCP `search_papers` 本次不可用（HTTP 406），未做 arXiv 全库穷尽检索；结论基于四路交叉，仍可能遗漏。
4. **selection_beta 的可比性**：在适应度未归一化前，β=3.0 无确定含义。

## 四、下一步

- 为 `n_motifs`、`world_size`、`selection_beta` 补「设计选择说明 + 敏感性实验」。
- `development_steps` 补 12 / 50 / 100 的收敛对比；`population_size` 补 24 / 48 / 96。
- 论文中严格区分「有出处取值」与「设计选择」，本 JSON 作为可核查依据保留。
