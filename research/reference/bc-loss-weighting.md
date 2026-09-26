# BC 分维加权 MSE 的权重依据（lambda_omega / lambda_v）

> 由 `research/reference/bc-loss-weighting.json` 摘要生成（原始 JSON 为权威，含逐条 URL/DOI、peer-reviewed 状态与引用数）。
> 检索时间：2026-09-26

- **问题**：`L = lambda_omega * MSE(omega_hat, omega*) + lambda_v * MSE(v_hat, v*)`，其中 `omega in [-1,1]`（tanh 头，值域 2）、`v in [0,1]`（sigmoid 头，值域 1）；当前 `docs/参数总表.json` 登记 `missing`，`learning/行为克隆学习.md` §6 明确未定前不得自行选定。
- **预算**：`K = 20` mini-batch 更新（固定）；baseline 与消融须同数据、同预算、权重全局冻结、不得逐个体调参。
- **证据规模**：19 条（含 8 篇同行评审、4 篇预印本/教材章节、3 份官方文档、4 个开源实现）。
- **一句话推荐**：**按目标尺度（方差）归一化，`lambda_i = 1/sigma_i^2`（sigma_i = Stage-1 训练集上第 i 维动作的标准差），等价于在标准化动作上做等权 MSE；未取得统计量前预注册回退值 `lambda_omega = 0.4, lambda_v = 1.6`（比值 1:4）。**

---

## 方法逐一评估（做法 + 依据 + 适用/局限）

### 1. 原始量纲上等权（`lambda_omega = lambda_v = 1`）
- **做法**：直接对未归一化的 `(omega, v)` 做等权 MSE。
- **依据（支持与反对）**：Kendall et al. (CVPR 2018) 把"性能强烈依赖各 loss 的相对权重"作为全文立论；GradNorm (ICML 2018) §4 的 toy 实验用**同函数形式、仅输出尺度不同（sigma = 1.0 vs 100.0）**证明：`w_i` 全取 1 时高尺度任务会压制低尺度任务的学习。本项目两个维度值域不同（2 vs 1），且 tanh 在 0 处斜率 1、sigmoid 在 0 处斜率 0.25，原始 MSE 既非尺度不变也不代表等量误差。
- **适用**：仅在**目标已标准化**之后，等权才等价于合理的尺度归一化；或作为消融 baseline。
- **局限**：非尺度不变，权重含义随单位/分布变化；不应作为默认契约。

### 2. 目标尺度 / 方差归一化（推荐）
- **做法**：`lambda_i = 1 / sigma_i^2`，`sigma_i` = Stage-1 专家轨迹**训练集**上第 i 维动作的标准差；`sigma_i <- max(sigma_i, 0.05 R_i)`（`R_omega=2, R_v=1`）；整体缩放使 `lambda_omega + lambda_v = 2`；一次计算、冻结。
- **等价表述**：在标准化动作 `z_i = (a_i - mu_i)/sigma_i` 上做等权 MSE，因为 `MSE(z_i) = MSE(a_i)/sigma_i^2`。**不改变网络输出头与动作语义**，只在损失层缩放（符合现有契约形式）。
- **依据**：
  - scikit-learn StandardScaler 官方文档：按特征去均值缩放到单位方差，统计量在训练集上计算后保存；若某特征方差大几个数量级会主导目标函数。用于防泄漏与"训练集统计量"用法。
  - Kendall (CVPR 2018) 的似然推导给出权重形如 `1/(2 sigma^2)`（其 sigma 为**残差噪声** std；本项目改用**目标尺度** std，形式同源、语义不同，须在文档写明）。
  - GradNorm (ICML 2018) 明确"按各任务方差 `sigma_i^2` 归一化后的损失之和"是多任务性能的自然度量——为按方差归一化提供同行评审锚点。
  - 工程共识：Stable-Baselines3 官方 RL Tips 建议连续动作归一化；robomimic 官方文档明确"actions should be normalized between -1 and 1 ... enables easier policy learning via tanh layers"。
- **适用**：两维单位/尺度不同、确定性专家数据、预算极小（无法学习权重）——正是本项目情形。
- **局限与风险**：
  1. 若某维动作近乎恒定（`sigma_i` 很小），`1/sigma_i^2` 会把它权重推得很大，可能过度优化一个"容易"的维度（IJCV 2025 指出 UW 类方法有偏向易优化任务的倾向）→ 必须设下限 `epsilon = 0.05 R_i`。
  2. 只消除**量纲任意性**，**不编码任务重要性**。两者要分开处理（见 §重要性）。
  3. 建议整体缩放使均值 1，把损失尺度与学习率解耦（用户文档 §6.2 的 LR 也未定，两者需一并定义）。

### 3. 不确定性加权 UW（Kendall et al., CVPR 2018）
- **做法**：`L = sum (1/(2 sigma_i^2)) L_i + log sigma_i`，回归时用 `s_i := log sigma_i^2` 保证数值稳定，`sigma_i` 随训练学习。
- **依据**：高斯似然推导；原文 Appendix B 称权重"在几百次训练迭代内收敛到相近最优"；最终三任务权重比达 43:1:0.16。
- **适用**：训练步数充足、任务确有可建模观测噪声、单位/尺度差异大。
- **局限**：
  - 更新惯性：Analytical UW (GCPR 2024) 实测权重初值错位后约需 100 epoch 才恢复。
  - 易过拟合、homoscedastic 假设过强、`sigma` 训练中收缩导致权重无上界地变大（IJCV 2025）。
  - GradNorm 论文报告其权重"涨得过大过快"、后期训练退化。
- **本项目判断**：**不建议**。专家是确定性规则控制器，无真实 aleatoric 噪声；K=20 远少于"几百次迭代"，学出的 sigma 基本停在初值，等于一个由初始化决定的常数权重，不如直接算数据统计量可审计。

### 4. GradNorm（Chen et al., ICML 2018）
- **做法**：按共享层逐任务梯度范数 `G_W^(i)`，目标 `Gbar_W * r_i^alpha`，用 `L_grad = sum |G_W^(i) - Gbar_W * r_i^alpha|_1` 更新 `w_i`，每步重归一化 `sum w_i = T`；含超参 `alpha` 与权重学习率。
- **依据**：toy 实验直接针对"同函数形式、仅尺度不同"的场景；且其"按方差归一化的损失之和"给出尺度归一化的度量依据。
- **适用**：任务数多、梯度尺度失衡、训练步数充足、有调参预算。
- **局限**：需逐任务对共享层额外反向传播（NYUv2 上约 +5% 训练时间）；权重随时间演化，隐含长训练；Analytical UW 综述指出梯度类方法训练更慢且未超过简单 scalarization。
- **本项目判断**：**不建议**（K=20 内权重动态来不及收敛，额外反向与超参调优在固定预算下无意义）。实现可参考 LibMTL / `lucidrains/gradnorm-pytorch`。

### 5. 梯度冲突类（PCGrad, NeurIPS 2020）与元学习类（Auto-Lambda, TMLR 2022）
- **做法**：PCGrad 在梯度余弦为负时把一方梯度投影到另一方正交平面；Auto-Lambda 用双层梯度元学习动态任务权重。
- **依据**：PCGrad 解决**梯度冲突**；Auto-Lambda 学习任务关系。
- **本项目判断**：**不建议**。本项目核心矛盾是**尺度失衡**而非冲突；元学习预算远超 20 步。

### 6. 几何损失 GLS（Chennupati et al., CVPRW 2019）与随机加权 RLW（Lin et al., TMLR 2022）
- **做法**：GLS 用各任务损失的几何平均（免调权、尺度不敏感）；RLW 用随机采样的损失权重训练，作为检验复杂加权是否真有增益的 baseline。
- **依据/局限**：GLS 乘性，任一维损失接近 0 会强烈拉扯、任务数增多时数值敏感；RLW 需多次重复才统计可靠。RLW 的结论"随机权重即可比 SOTA"支持**不要过度工程化**。
- **本项目判断**：**仅作参考/消融对照**，不作默认；GLS 与已固定的加权和契约不符。

### 7. 对 tanh/sigmoid 饱和区损失加权
- **做法（若做）**：给饱和样本的损失乘更大的 lambda。
- **为什么无效**：对输出层预激活的 MSE 梯度为 `dL/dz = 2 (y_hat - a) * f'(z)`；饱和时 `f'(z) -> 0`，梯度已趋零。乘损失权重只是对已趋零的量再乘常数，不改变消失行为；乘 `f'` 反而使梯度 ∝ `(f')^2` 更小。
- **依据**：Goodfellow et al. (2016) §6.2.2.2——"when we use other loss functions, such as mean squared error, the loss can saturate anytime sigma(z) saturates ... the gradient can shrink too small to be useful for learning"；LeCun (1998) Efficient BackProp 的解法是**让目标值落在二阶导最大处、初始化使 sigmoid 工作在线性区、必要时用带线性项的 tanh**。
- **本项目判断**：**不建议**。正确动作是统计饱和样本占比，若高则在文档层面讨论输出参数化，而非加饱和权重。

---

## 极小预算 K=20 下权重选择的影响（Q2）

**直接文献：not found。** 未找到以 20 次（或数十次）mini-batch 更新为预算、专门研究 BC 分维损失权重敏感性的论文。可用的**相邻证据**：

| 证据 | 对本项目的含义 |
|---|---|
| Kendall (CVPR 2018)：UW 权重需"a few hundred training iterations"收敛 | K=20 少 1–2 个数量级，学习式权重≈固定初值，不可靠 |
| Analytical UW (GCPR 2024)：权重有约 100 epoch 更新惯性 | 学习式权重在早期基本无效 |
| GradNorm (ICML 2018)：尺度失衡在训练早期误差最大时危害最大 | 20 步几乎全在早期区间，权重对**偏置**的影响被放大 |
| Random Weighting (TMLR 2022)：随机/简单权重可比复杂动态加权 | 极小预算下应选解析固定权重，不上动态方案 |

**收敛/偏置判断**：固定尺度归一化不改变收敛阶，只改变各维有效步长与共享干的梯度方向；作用是让 20 步的梯度预算按归一化误差在两维间分配，而非被大尺度维度吃掉。因为 20 步几乎全处于误差最大的早期，**权重选择对初始学习方向（偏置）的影响显著大于长训练场景**。

---

## 尺度归一化的计算方式（Q3）

**主规则（训练集统计量）**：
1. 在 Stage-1 专家轨迹的**训练 split**（非验证/测试 episode）上，对全部 `(omega*, v*)` 样本分别计算 `sigma_omega = std(omega*)`、`sigma_v = std(v*)`。
2. `sigma_i <- max(sigma_i, 0.05 R_i)`，`R_omega = 2`、`R_v = 1`（下限 0.1 与 0.05），防止近恒定维度权重爆炸。
3. `lambda_i = 1 / sigma_i^2`；整体缩放使 `lambda_omega + lambda_v = 2`（把损失尺度与学习率解耦）。
4. **计算一次，全实验冻结**；baseline 与消融共用；只在训练 split 上算，防信息泄漏。

**回退（预注册解析值域）**：按 `lambda_i ∝ 1/R_i^2`，即
```
lambda_omega : lambda_v = R_v^2 : R_omega^2 = 1 : 4
```
在均值 1 归一化下即 **`lambda_omega = 0.4, lambda_v = 1.6`**。该回退假设动作在值域内近似均匀（此时方差 `= R^2/12`，与按方差归一化同解），保守、不依赖数据；一旦取得 Stage-1 统计量就切换为主规则并记录。

> 建议同时保留更温和的 `lambda_i ∝ 1/sigma_i` 作为备选：`1/sigma_i^2` 是真正的"标准化目标"；`1/sigma_i` 只拉平量纲、对近恒定维度更温和。

---

## 任务重要性（额外说明）
默认**重要性中性**：本次检索未找到任何外部依据支持"鱼类转向 omega 比推进 v 更重要/更不重要"的具体系数。项目 fitness 的 `0.35/0.25/0.20/0.20` 是演化聚合权重，**不是** BC 的动作重要性权重，不可直接搬用。若团队有先验，应写成显式乘子 `lambda_i = m_i / sigma_i^2`，作为**预注册超参**在文档标状态并做比例消融；否则属"AI 填空"。

---

## 推荐（可写进 `learning/行为克隆学习.md` §6，状态建议标『草案待确认』）

> BC 分维损失权重采用目标尺度（方差）归一化：`lambda_i = 1 / sigma_i^2`，`sigma_i` 为 Stage-1 专家轨迹训练集上第 i 维动作的标准差，取 `sigma_i <- max(sigma_i, 0.05 R_i)`，计算一次并在全部实验冻结；整体缩放使 `lambda_omega + lambda_v = 2`。等价于在标准化动作上做等权 MSE。未获得 Stage-1 统计量前，预注册回退值 **`lambda_omega = 0.4`、`lambda_v = 1.6`**（即比值 1:4，等价于按值域 `R^2` 归一化）。K=20 下禁止使用学习式权重（Kendall UW、GradNorm 等）；不允许逐个体调参；baseline 与消融必须用同一组冻结权重。禁止对 tanh/sigmoid 饱和区额外加权。

**风险/待验证**：该规则只消除量纲任意性、不编码任务重要性；若消融发现某一维（尤其 v）因权重被过度优化而损害任务指标，应降到 `lambda_i ∝ 1/sigma_i` 或回到等权并记录，且任何偏离都要在文档标注并做同预算对比。

---

## 三级结论
- **推荐直接用**：目标尺度/方差归一化规则 `lambda_i = 1/sigma_i^2`（等价于标准化动作上的等权 MSE），用于确定 `lambda_omega`、`lambda_v` 的比值与冻结流程。
- **仅作参考**（消融对照，不作默认）：等权 `lambda=1`（须在标准化目标上）、GLS、RLW、GradNorm/UW 作为"是否有增益"的对照。
- **不建议**：K=20 下使用 Kendall UW / GradNorm / Auto-Lambda 等学习式或梯度式动态加权；对饱和区加权；把 fitness 的 `0.35/0.25/0.20/0.20` 当成 BC 动作重要性权重。

## 没找到（not found）
1. 未检索到任何文献给出 EvoGenesis 场景下 `lambda_omega / lambda_v` 的具体数值——必须由本项目 Stage-1 统计量或预注册值决定。
2. 未找到以 20 次（或数十次）mini-batch 更新为预算、专门研究 BC 分维损失权重对收敛/偏置影响的论文。
3. 未找到支持"omega 与 v 之间重要性权重"的外部依据。
4. 未找到任何同行评审来源支持对 tanh/sigmoid + MSE 做"饱和区损失加权"。
5. 未验证 Kendall 的 sigma（残差噪声）与本项目采用的 sigma（目标尺度）可互换——这是本项目对该方法的改造，须显式标注为工程口径。

## 下一步建议（人工确认后再改文档/代码）
1. 生成 Stage-1 轨迹后，加只读统计脚本输出 `sigma_omega`、`sigma_v`、各维分位数、以及 `omega* -> ±1` / `v* -> 0,1` 的饱和占比，写进 run 记录。
2. 回写 `src/evogenesis/learning/行为克隆学习.md` §6 并同步 `docs/参数总表.json`（`missing` 改为规则 + 回退值，状态标『草案待确认』）。
3. 预注册最小消融：`{1:4（回退）, 1:1（等权）, 1/sigma^2（主规则）}` 三组，同数据同 K=20，报各维 MAE/RMSE + 任务指标。
4. 若做 GradNorm/UW 对照，可用 LibMTL（MIT, PyTorch, 2592 stars）作参考实现，但须承认其面向大预算、需改写为 DanioNet 的 2 维输出，且只作负对照，不进正式结果。
