# H3 历史依赖任务调研：可用于二维 Arena 的探针与 τ 异质性证据

> 检索时间：2026-09-26　｜　机器可读文件：`research/reference/h3-history-task.json`
> 用途：为「H3：异质 τ_i 在历史依赖任务中形成与 homogeneous-τ 不同的性能—效率权衡」找到可落地、可引用的任务范式与理论依据，回答 Arena 里“哪个任务体现历史依赖”。
> 约定：DOI/URL 于 2026-09-26 核实；引用数来自 OpenAlex（非 Google Scholar）；GMD 技术报告与 2026 Nature 论文无 OpenAlex 引用数，标 `null`。

---

## 一句话结论

历史依赖任务在斑马鱼上**有直接证据**（Yang 2022 脑干 integrator 自我位置记忆、Tanaka & Portugues 2025 光流记忆、Bloch 2019 成年斑马鱼 DMTS），其中 **Yang 2022 的“延迟后回到早先位置”最贴合 H3**；τ 异质性的支持证据分两级——**观测级**（Bernacchia 2011 皮层幂律 τ 库）与**模型级**（Tanaka 2022 DTS-ESN、Perez-Nieves 2021、Yamashita & Tani 2008）。但 Jaeger 2001 / Dambre 2012 给出**容量上界 = 状态数 N**，故 H3 只能主张“性能—效率权衡/有效时间尺度覆盖”的差异，**不能**主张异质 τ 提高记忆容量。

**推荐落地方案**：在 Arena 新增 **候选任务 A「遮蔽后延迟重定位（delayed prey relocation / last-seen prey memory）」**，作为 H3 的检验任务。

---

## 一、Arena 现状与 H3 的断点

- Arena 现有任务是二维捕食—逃逸—能量—成长（`arena/Danio_Arena设计规范.md`），输入 12 维含 `looming_rate`，但没有一个任务**刻意**让当前动作依赖“已不可见的历史状态”。
- DanioNet 已有 `integrator_memory` 神经类型与漏积分动力学（`connectome/DanioNet设计规范.md` §3），但 `homogeneous tau` 的取值在 §9/阅读问题 #7 中**未定义**——这是 H3 落地前必须先补的契约（否则违反项目“禁止 AI 填空”）。
- 因此 H3 的缺口是：**缺一个可控延迟 D、可证伪、可量化历史依赖的探针任务**。

---

## 二、任务范式候选（按落地成本排序）

| 候选 | 文献原型 | 历史依赖机制 | 在 Arena 的落地成本 | 评价 |
|---|---|---|---|---|
| **A. 遮蔽后延迟重定位** | Yang et al. 2022 *Cell*（斑马鱼脑干 integrator）；近邻：Tanaka & Portugues 2025、Bolton et al. 2019 | 当前动作依赖 D 步前“最后看到的 prey 位置” | 低：复用 prey 位置/FOV/obstacle，加隐藏与判定 | **首选** |
| B. delayed match-to-sample | Bloch et al. 2019（成年斑马鱼，延迟 3–4 s）；Miller et al. 1996（猕猴 PFC） | 延迟期维持样本线索，延迟后二选一 | 高：需新增“样本—延迟—左右二选一”操作性结构 | 仅作参考 |
| C. looming + 遮蔽藏身 | Temizer 2015；Dunn 2016；Bhattacharyya 2017 | 需人为加“遮蔽期记住安全区/威胁方向” | 中：looming 已有，但需重设计 | 仅作参考 |

**为何不选 B 作首选**：Arena 目前没有选择装置、prey 无颜色/价值分级（Arena 阅读问题 #10 已指出“高价值 prey 未定义”），复刻 DMTS 等于新造一个任务系统，且其“自由游动二维捕食”语义反而更远。
**为何不选 C**：单纯 looming 逃逸是反射式的，历史依赖弱（Temizer 2015 / Dunn 2016 的逃逸回路是快速反射），要用于 H3 必须额外构造延迟记忆结构，历史依赖成分不如 A 干净。

---

## 三、推荐落地方案：候选任务 A 的具体设计

> ⚠️ 以下为**提议**，Arena 目前未定义该任务。按 AGENTS「文档 → 代码 → 测试 → 回写文档」，须先在 `arena/Danio_Arena设计规范.md` 写入并标注状态（`草案待确认` / `已定稿`）后再实现。本节不含未定义的数值，占位参数须由 play-test 校准。

### 1. 状态量（Arena 侧，隐藏真相，不进 12 维输入）

- `last_seen_prey_pos`：最近一次 prey 可见时的位置 `(x*, y*)`。
- `last_seen_step` `t0`：该次可见的步号。
- `occlusion`：prey 处于 obstacle 后或出 FOV 的持续步数。

### 2. “历史依赖”如何计算

1. 试验开始：prey 在 `t0` 时刻位于 `(x*, y*)` 且可见。
2. 遮蔽事件：prey 被 obstacle 遮挡 / 移出 FOV，持续 **D** 步（D 为受控延迟，扫描多档）。
3. 判定窗口：在 `t0 + D` 时刻，若鱼移动到 `(x*, y*)` 邻域（`r_reloc` 待校准）则记为一次成功重定位。
4. 关键点：**成功只能靠网络内部维持 `(x*, y*)` 的估计**，因为输入在 D 步内不含该信息。

历史依赖的**可证伪量化**（不能只看总成功率）：

- 延迟曲线：成功率 `P(D)` 随 D 的退化速度。
- 内部记忆解码：对 `integrator_memory` 单元激活做线性/互信息解码，检验其是否编码隐藏 prey 方向；hetero-τ 组预期解码精度随 D 退化更慢。
- 打乱历史对照：把历史序列打乱后若性能不变，则该任务没有真正测到历史依赖——作为阴性对照。

### 3. hetero-τ vs homo-τ 对比协议

| 项 | 设定 |
|---|---|
| 对照组 | `homogeneous tau`：`τ_i` 全取 hetero 分布的均值 |
| 额外对照 | `τ` **网格扫描**（如 τ∈[1,10] 的若干档），报告同质基线的最优值 |
| 公平性 | 同数据、同预算、同种子多重复；DanioNet padding 到 48 nodes 不变 |
| 指标 | 各 D 下重定位成功率；单位能量消耗（§6 能量式）或 active-neuron×step 计算量 |
| 呈现 | 性能—效率 **Pareto 前沿**（预期 hetero-τ 前沿右移、长 D 退化更慢） |

### 4. 原型与局限（必须写进论文）

- 原型：Yang et al. 2022 *Cell* 是 **head-fixed fictive-swimming VR**，观测到被动位移后数秒游回早先位置；候选 A 是**抽象类比**，不是复刻。
- 近邻：Tanaka & Portugues 2025 的光流记忆 hysteresis 提供“历史依赖 = 当前反应依过去光流”的可操作定义，并提示自生运动需被扣除；Bolton et al. 2019 说明 prey 任务天然含短时程预测。
- 缺口：**未找到**“幼鱼自由游动 + 猎物消失后延迟重定位”的现成范式，故 A 无直接行为学复刻对象，须在论文中标为构建的探针。

---

## 四、τ 异质性证据与边界

| 级别 | 文献 | 结论 | 对 H3 的作用 |
|---|---|---|---|
| 观测 | Bernacchia et al. 2011 *Nat Neurosci* | 皮层神经元携带幂律分布的 τ（百毫秒—数十秒），可由 reservoir 模型复现 | 支撑“异质 τ 是合理先验” |
| 模型 | Tanaka et al. 2022 *Phys Rev Research*（DTS-ESN） | 异质 leaky integrator 在多尺度预测优于同质 | **最直接类比**：异质 τ 在时间结构任务占优 |
| 模型 | Perez-Nieves et al. 2021 *Nat Commun* | 异质性提升时间结构丰富任务的性能与稳定性 | 一般性支持 |
| 模型 | Yamashita & Tani 2008 *PLoS Comput Biol* | 多时间尺度 RNN 自组织功能层级 | 机理论述 |
| 理论 | Jaeger 2001；White et al. 2004；Dambre et al. 2012 | 记忆/计算总容量受状态数 N 上界约束（fading memory 下达 N） | **反证/限定**：H3 不得表述为“提高记忆容量” |

**必须的限定**：Dambre 2012 证明满足 fading memory 时系统总容量等于线性独立状态变量数 N。异质 τ **不改变**这个上界，能改变的是：可达容量、有效时间尺度覆盖、以及性能—效率权衡。论文若写成“异质 τ 提升记忆容量”会被 N 上界反例直接驳回。

---

## 五、实现参考（待验证）

- `reservoirpy/reservoirpy`：Python、MIT、657 stars（2026-09-26），ESN 工具库，可用于 DanioNet 之外做 τ 异质性最小对照。**风险点**：是否内置 heterogeneous leak rate 未逐行审计，需落地时验证。
- `stefanonardo/echo-state-network`：Matlab，与 Python/uv 约束不符，**不建议**使用，仅作算法复核。

---

## 六、结论分级

- **推荐直接用**：候选任务 A（遮蔽后延迟重定位）作为 H3 探针；Bernacchia 2011 + Tanaka 2022 作为 τ 异质性的立论与类比锚点。
- **仅作参考**：候选 B（DMTS，落地成本高）、候选 C（looming+藏身，历史依赖弱）；Cueva 2020 的低维动力学分析方法和 Cavanagh 2020 / Golesorkhi 2021 综述。
- **不建议**：Matlab ESN 仓库；以“提高记忆容量”措辞表述 H3（与 N 上界冲突）。

## 七、需进一步验证的风险点

1. `homogeneous tau` 取值未定义 → 落地前必须补文档（阻断项）。
2. 同质基线需 τ 网格扫描，否则 hetero-τ 的胜出可能是基线选值不佳的假象。
3. 历史依赖需阴性对照（打乱历史）与内部记忆解码，否则可能只是反应式策略。
4. 候选 A 无直接行为学复刻对象，论文须标为构建探针。
5. 未检索到“τ 异质 → 工作记忆行为提升”的因果实验；现有证据链是观测 + 模型类比。
6. arXiv 接口本次 HTTP 406，预印本仅经 OpenAlex 间接覆盖，可能有遗漏。
