# ΔB_l 四分量操作化 与 penetrance 计算式

> 检索时间：2026-09-26。配套 JSON：`research/reference/delta-B-and-penetrance.json`（同一主题，28 条依据，含 DOI/URL 与 peer-reviewed 状态）。
> 服务对象：`development/RGCD数学模型.md` §12 与 `genome/生物学与进化遗传学基础.md` §3。
> 边界：只给候选定义、外部依据与推荐，不修改 `research/reference/` 以外任何文件；θ 数值与 a*(g) 映射不在此定稿。

---

## 一、主题 1：ΔB_l 四分量操作化

### 1.1 问题

RGCD §12 已定义结构距离

\[
d_{edge}^{(l)}=\frac{\|A(G)-A(G^{(l)})\|_1}{N^2},\qquad
d_{\tau}^{(l)}=\frac1N\sum_i|\tau_i(G)-\tau_i(G^{(l)})|
\]

并给出行为效应为四维 \(\Delta\mathbf B_l=(\Delta\mathrm{Capture},\Delta\mathrm{Escape},\Delta\mathrm{Survival},\Delta\mathrm{Energy})\)，明确不合成标量。缺口有三处：每个分量的计算口径、按鱼还是按种群聚合、归一化方式。

### 1.2 推荐定义式

对 locus \(l\)、野生型 \(G\)、突变体 \(G^{(l)}\)，取 \(K\) 个**匹配块** \(k=(\text{environment\_id},\text{episode\_seed})\)，每块用**同一 seed** 各跑一条野生型与一条突变体（common random numbers）。逐鱼原始率沿用 fitness 同口径：

\[
x_{\mathrm{Survival}}=\frac{\text{survival\_steps}}{600},\qquad
x_{\mathrm{Capture}}=\frac{\text{captures}}{\max(\text{capture\_attempts},1)},
\]
\[
x_{\mathrm{Escape}}=\frac{\text{escape\_successes}}{\max(\text{predator\_encounters},1)},\qquad
x_{\mathrm{Energy}}=\frac{E_i(T_i)-E_{\max}}{T_i},\ T_i=\text{survival\_steps}_i
\]

四维分量为

\[
\boxed{\ \Delta X_l=\frac{1}{K}\sum_{k=1}^{K}\big[x_X(G^{(l)},k)-x_X(G,k)\big],\quad X\in\{\mathrm{Capture,Escape,Survival,Energy}\}\ }
\]

每分量另报无量纲标准化效应（不作标量合成）：

\[
g_{X,l}=J(K-1)\cdot\frac{\Delta X_l}{s_{d_X}},\qquad
J(m)=1-\frac{3}{4m-1},\qquad
s_{d_X}=\mathrm{SD}_k\big[x_X(G^{(l)},k)-x_X(G,k)\big]
\]

置信区间用配对口径 \(\Delta X_l\pm t_{0.975,K-1}\,s_{d_X}/\sqrt K\)；\(K<8\) 或差值强偏时改 Wilcoxon signed-rank。

**聚合层级裁决**：先个体配对、再对 \(K\) 取平均。当配对为双射时，该均值恒等于「突变种群均值 − 野生存群均值」，点估计与种群层面完全相同；配对的价值在于去掉个体与环境的共同方差，把精度锚在 \(s_d/\sqrt K\)。因此「按鱼还是按种群」不是两个不同的估计量，而是同一估计量的两种方差估计方式。多层 episode 时把 fish 当随机效应、block 当配对因子，不得把同一 fish 的多 episode 当独立样本。

**归一化裁决**：用原始单位（三比例为 \([0,1]\)，能量为 能量/步）。跨分量可比性只通过每分量各自的 \(g_{X,l}\) 获得。不除以野生型基线（零分母、比值估计偏差），不用代内 min-max（那是 fitness \(F\) 的口径，改用后 ΔB 变成 cohort 相对量、跨 run 不可比，直接违反 evolution §5「跨代、跨环境比较一律用原始指标」）。

### 1.3 依据

| 依据 | 支撑点 | DOI / URL |
|---|---|---|
| Fisher 1941, *Ann. Eugenics* | 单等位替换的平均效应（average effect）原型；本设计只改一个 base、固定背景，故 ΔB_l 是因果平均效应 | 10.1111/j.1469-1809.1941.tb02272.x |
| Lee & Chow 2013, *Genetics Research* | 区分 average effect（因果）与 average excess（相关），支持配对因果差而非观察相关差 | 10.1017/S0016672313000074 |
| Hedges 1981, *J. Educ. Stat.* | 标准化均值差的小样本偏差与无偏校正 \(J\) | 10.3102/10769986006002107 |
| Lakens 2013, *Front. Psychol.* | 配对/独立样本效应量与 CI 的可引用规范 | 10.3389/fpsyg.2013.00863 |
| Goulet-Pelletier & Cousineau 2018, *TQMP* | 配对样本 \(d_z\)/Hedges \(g\) 的公式与 CI | 10.20982/tqmp.14.4.p242 |
| Morris & DeShon 2002, *Psych. Methods* | 重复测量与独立组效应量不可混用，须声明设计并用配对方差 | 10.1037/1082-989x.7.1.105 |
| Nelson 1987, *Oper. Res. Lett.* | common random numbers 通过正相关降低两方案差的方差 | 10.1016/0167-6377(87)90015-0 |
| Kesur 2009, *J. Transp. Eng.* | 随机仿真 + 演化算法中用 CRN 降适应度评估方差（与本项目同构） | 10.1061/(asce)0733-947x(2009)135:4(160) |
| Lessells & Boag 1987, *The Auk* | repeatability 正确的方差分层，禁止把重复当独立 | 10.2307/4087240 |
| Dingemanse & Dochtermann 2012, *J. Anim. Ecol.* | 行为表型的个体间/个体内方差分解 | 10.1111/1365-2656.12013 |
| Estrada, Ferrer & Pardo 2019, *Front. Psychol.* | average-based 与 individual-based 变化统计量的关系 | 10.3389/fpsyg.2018.02696 |
| Eyre-Walker & Keightley 2007, *Nat. Rev. Genet.* | 突变效应以「分布」而非单点均值报告 | 10.1038/nrg2146 |

### 1.4 局限

1. **CRN 只部分降方差**：突变与野生型在首次行为分歧后随机流解耦，\(s_d\) 未必显著小于独立样本方差。收益须实测，不能凭设计宣称。
2. **小分母比率不稳**：`capture_attempts` 或 `predator_encounters` 为 1 时比率方差很大；须报分母分布，或设最小分母阈值并声明。分母为 0 时约定该分量置 0 并标「非估计」。
3. **四分量相关且多 locus**：`captures` 与 energy 相关；全 genome 扫描带来多重比较。若做显著性须预注册族错误率控制，不得先合成标量再单点检验。
4. **「不合成标量」是硬约束**：本推荐用四分量的 \(g\) 并列，不做加权和。

### 1.5 推荐结论

**推荐直接用 D1**（配对个体差均值 + 每分量 Hedges \(g_z\)）。备选 D2（独立组种群差）仅在无法做 seed 配对时作退化基线，且必须显式声明。**不建议** D3 基期比值、D4 代内 min-max 分量差、D5 加权合成标量。

---

## 二、主题 2：penetrance 计算式

### 2.1 问题

genome §3 已冻结两条轴 `high_N ⟺ E_A>θ_N`、`high_H ⟺ E_B>θ_H`，并形成 2×2 架构档，要求「须同时报告各类 penetrance」，但未给计算式，也未定义如何把连续的 \(N\)、\(\tau\) 异质性离散成 high/low。

### 2.2 推荐定义式

标准定义：\(\mathrm{penetrance}=P(\text{表型}\mid\text{基因型})\)，即携带某基因型的个体中呈现相应表型的比例（Cooper et al. 2013；Kingdom & Wright 2022）。

对本项目，对每个 genotype 类 \(g\in\{A\_B\_,A\_bb,aaB\_,aabb\}\) 与其目标架构档 \(a^*(g)\)：

\[
\boxed{\ \mathrm{pen}(g)=\frac{\#\{i:\ g_i=g,\ \hat a_i=a^*(g)\}}{\#\{i:\ g_i=g\}}\ }
\]

其中观测架构档由发育产物二分：

\[
\hat a_i=\big(\mathbb 1[N_i>\theta_N^{\mathrm{obs}}],\ \mathbb 1[H_i>\theta_H^{\mathrm{obs}}]\big),\qquad
N_i=|M_i|\in[24,48],\quad H_i=\mathrm{CV}_\tau(i)=\frac{\mathrm{SD}_i(\tau)}{\mathrm{mean}_i(\tau)}
\]

- \(N_i=|M_i|\)：neuron 数档，判定 `high_N`。
- \(H_i=\mathrm{CV}_\tau(i)\)：\(\tau\) 异质性档，判定 `high_H`（推荐 CV；备选 IQR，属项目设计选择，须冻结）。
- \(\theta_N^{\mathrm{obs}},\theta_H^{\mathrm{obs}}\)：在**独立校准集**（建议 ≥1000 offspring/类）上取两类中位数中点或错分最小点，登记 `docs/参数总表.json`；**不得**在报告样本上调阈值（循环性）。

阈值模型的解析形式仅作诊断：

\[
\mathrm{pen}^{\mathrm{model}}(g)=1-\Phi\!\left(\frac{\theta^{\mathrm{obs}}-\mu_g}{\sigma}\right)
\]

（Falconer 1965；Falconer & Mackay 1996 Ch.18）。\(y\in\{N,H\}\) 写成 genotype 类均值 \(\mu_g\)、类内 SD \(\sigma\) 的潜变量，阈值 \(\theta^{\mathrm{obs}}\) 时，越阈概率即上式。二维 \(N\times H\) 仅在给定 \(g\) 下独立时可因子化，否则用经验 \(\mathrm{pen}(g)\)。

### 2.3 依据

| 依据 | 支撑点 | DOI / URL |
|---|---|---|
| Cooper et al. 2013, *Human Genetics* | penetrance = P(表型\|基因型) 的权威定义；reduced penetrance 的机制 | 10.1007/s00439-013-1331-2 |
| Kingdom & Wright 2022, *Front. Genet.* | penetrance 为二元现象，须与 variable expressivity 分开报告 | 10.3389/fgene.2022.920390 |
| Falconer 1965, *Ann. Hum. Genet.* | liability-threshold 模型奠基 | 10.1111/j.1469-1809.1965.tb00500.x |
| Falconer & Mackay 1996, *Intro. Quant. Genet.* Ch.18 | 阈值性状的标准推导与阈值/incidence 关系 | archive.org/details/IntroductionToQuantitativeGenetics |
| Roff 1996, *Q. Rev. Biol.* | 阈值性状演化综述，阈值位置与遗传方差共同决定表型比例 | 10.1086/419266 |
| Gianola & Foulley 1983, *GSE* | 阈值模型的统计估计框架 | 10.1186/1297-9686-15-2-201 |
| Altman & Royston 2006, *BMJ* | 二分连续变量损失信息与功效，须保留连续度量 | 10.1136/bmj.332.7549.1080 |
| MacCallum et al. 2002, *Psych. Methods* | 二分化的测量/统计损害与「同一样本选阈值」的循环 | 10.1037/1082-989x.7.1.19 |
| Waddington 1942, *Nature* | canalization 使同基因型仍可能落到不同档，解释 pen<1 的机制 | 10.1038/150563a0 |

### 2.4 报告规范

1. 四个 \(\mathrm{pen}(g)\) 各带 Wilson 95% CI。
2. 每个 genotype 类附 2×2 观测架构档混淆矩阵（8 格计数），定位是 N 轴还是 H 轴泄漏。
3. 连续 \(N\) 与 \(\mathrm{CV}_\tau\) 的分布（violin/ECDF）与 pen **并列**报告；pen 是派生摘要，不是主读数。 \(N\) 须同时报**原始** \(\bar N_K\) 与**逐 seed 居中**读数（基线 = 该 seed 分层集读数中位数；2026-09-27，见 `experiment §3.9`）—— 只有居中读数进判档。
4. genotype 计数（理想 9:3:3:1）与 phenotype penetrance（含噪声）分成两个数。
5. \(\theta^{\mathrm{obs}}\)、所用 \(\tau\) 异质性统计量、校准集代数与 seed 全部落盘。

### 2.5 局限

1. **映射未冻结**：genome §3 只冻结两条轴，未冻结四类→2×2 的具体赋值 \(a^*(g)\)。\(\mathrm{pen}(g)\) 的四个具体式子必须等 \(a^*(g)\) 定稿后才能写死；在此之前文档只能用 generic 形式并标「映射待定稿」。
2. **二分代价**：pen 是二分后的派生量，损失信息与功效（Altman & Royston 2006；MacCallum et al. 2002）。必须与连续分布并列。
3. **表达层定义退化**：若直接用 §3 字面的 `E_A>θ_N` 当 observed，则因 \(E_A\in\{1,0.5,0\}\)、\(\theta_N\in(0,0.5)\)，判定解析地完全分离，penetrance 恒为 1；只能作「阈值分离率」实现诊断，不能作 pen 主定义。
4. **模型式假设**：`1-Φ((θ-μ_g)/σ)` 依赖正态、类内同方差、二维独立，小样本下 μ_g/σ 不稳，只作诊断。
5. **阈值标定循环**：θ 必须在独立校准集上定，否则 pen 是自我实现的。

### 2.6 与「160 例为演示非统计验证」的一致性

n=160 下 9:3:3:1 类大小期望为 90/30/30/10，最小类 aabb 仅 10 例。本报告用精确二项与 Wilson CI 计算（非文献数值）：

| genotype 类 | 期望 n | 真 pen | Wilson 95% 半宽 | 以 pen≥0.8 筛查、真值 0.8 时观测落到界下的概率 |
|---|---|---|---|---|---|
| A_B_ | 90 | 0.90 | ≈0.063 | ≈0.54 |
| A_bb | 30 | 0.90 | ≈0.111 | ≈0.57 |
| aaB_ | 30 | 0.90 | ≈0.111 | ≈0.57 |
| aabb | 10 | 0.90 | ≈0.193 | ≈0.62 |

即使大类的筛查也接近掷硬币，小类 aabb 尤甚。结论：160 例只支持「展示 pen 的定义与计算流程」，不支持对 pen 下界的统计检验；与 `phenotype-threshold-mendel.md` 一致。报告须给 CI 与逐类 n，不得只用点估计宣称「遗传合理」。

---

## 三、未找到项

- **ΔB 四维行为效应向量的同行评审定义**：无。文献只支撑构件（因果平均效应、配对效应量、CRN、二分代价）。
- **2×2 架构档 penetrance 的文献先例**：无。penetrance 一般定义与阈值模型有文献，绑定 RGCD 的 N/τ 属项目自定义。
- **τ 异质性统计量（CV vs IQR）的文献裁决**：无，属设计选择。
- **θ_N、θ_H、θ_N^obs、θ_H^obs 数值**：无文献来源，属标定/反解（G12）。
- **a\*(g) 具体映射**：genome §3 未冻结。
- **arXiv 全文**：arXiv MCP 本次两次尝试均返回 HTTP 406，未取正文；论文锚点全部来自 OpenAlex 元数据与 DOI。
- **penetrance 专用 Python 库**：未发现权威实现；计数 + Wilson CI 即可，`statsmodels`/`scipy` 足够，无需新依赖。

## 四、工具与许可证备注

- `raphaelvallat/pingouin`（star 1931，pushed 2026-09-09）为 **GPL-3.0**（copyleft），不宜作交付/入库依赖；可作本地开发工具。
- `statsmodels/statsmodels`（star 11652，BSD-3-Clause）建议作为配对检验实现；Hedges \(J\) 校正自行实现（Hedges 1981 公式）。
- `easystats/effectsize`（R，star 353）仅作公式口径交叉参考，Python 栈不可直接用，license 需自辨。

## 五、下一步（交接给文档 owner）

1. 把 §1.2 的 ΔB 公式回写 `RGCD数学模型.md` §12，并注明「S/P/Esc/Q 率定义对齐 evolution §5，但不采用代内 min-max」。
2. 把 §2.2 的 pen 公式回写 `genome/生物学与进化遗传学基础.md` §3；同时冻结 a*(g) 与 τ 异质性统计量，标状态（`已定稿`/`草案待确认`）。
3. 在 `docs/参数总表.json` 登记 θ_N、θ_H（G12）与 θ_N^obs、θ_H^obs 的校准协议与状态。
4. 实现后用一组同 seed 的野生型/突变体最小实验，验证配对方差小于非配对；用一组 calibration offspring 验证 pen 的可复算性。
