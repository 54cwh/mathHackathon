# 调研：DanioNet 12 维感官向量的语义与 Arena 编码规则（问题 #13）

> 对应 JSON：`research/reference/sensory-encoding-12d.json`（meta + 20 items + owner_ruling + draft_encoding + 13 条 conclusions）
> 检索时间：2026-09-26 ｜ 来源：OpenAlex（DOI/引用核验）、PMC 全文、LMU eDoc、GitHub API
> 约束：现场离线、CPU 可跑；Arena 的 radius/FOV 为 config 参数，非真实斑马鱼解剖测量值。

---

## 一、结论速览（三级）

| 分级 | 结论 |
|---|---|
| **推荐直接用** | ① owner 裁决：12 维**语义**归 DanioNet §2，**编码规则**归 Arena §4，边界对象 `observation_12d` 在 `core/核心机制与数据流.md §10` 登记；② 结构化低维向量（非 raw pixels）方向正确；③ prey / threat 分通道有同行评审依据；④ looming 用经典角尺寸式 θ=2·arctan(l/r)，其生物学标定为 l/‖v‖。 |
| **仅作参考** | ① 左右通道的**具体构造**（方位角硬阈值 vs 软加权投影）无斑马鱼范式，属工程选择；② size→半径映射与归一化到 [0,1] 属设计选择；③ MPE/PettingZoo/MPE2 为工程惯例（非同行评审）。 |
| **不建议** | 把 looming 简化为「威胁在视野内=1」的 0/1，或用亮度变化代替角尺寸变化率（丢失强度校准与 dimming 成分）。 |

**阻断项（必须先裁决）**：`current_speed` 在 Arena 物理中无对应量——推荐解释为鱼自身瞬时速度 `v_t`（Arena §5，∈[0,1]）；若原意是环境水流，须先改 Arena 文档新增字段。

---

## 二、文献证据（peer-reviewed）

### 2.1 prey 与 threat 通道的解剖分离

| 论文 | DOI | 引用 | 用途 |
|---|---|---|---|
| Semmelhack et al. 2014, *eLife* | 10.7554/eLife.04878 | 227 | 顶盖前区 AF7 专门响应最优猎物刺激 → prey 通道独立 |
| Gahtan et al. 2005, *J Neurosci* | 10.1523/JNEUROSCI.2678-05.2005 | 361 | 顶盖下游网状脊髓神经元控制捕食朝向/追击 → prey 方位表征 |
| Bianco et al. 2011, *Front Syst Neurosci* | 10.3389/fnsys.2011.00101 | 367 | 尺寸依赖：小目标→捕食、大目标→逃逸 → 对象分类依据 |
| Bianco & Engert 2015, *Curr Biol* | 10.1016/j.cub.2015.01.042 | 246 | 顶盖神经元对 size/speed 混合选择 → 结构化标量通道合理 |
| Trivedi & Bollmann 2013, *Front Neural Circuits* | 10.3389/fncir.2013.00086 | 121 | VR 捕食的「追踪-接近-捕获」链 → prey 方位反复读取 |
| Temizer et al. 2015, *Curr Biol* | 10.1016/j.cub.2015.06.002 | 335 | looming→逃逸专用通路 → threat 通道独立 |
| Bhattacharyya et al. 2017, *Curr Biol* | 10.1016/j.cub.2017.08.012 | 115 | 威胁响应随刺激强度**校准** → threat 信号应为强度而非标签 |
| Filosa et al. 2016, *Neuron* | 10.1016/j.neuron.2016.03.014 | 205 | 进食状态调制猎物加工 → energy/hunger 独立维度 |
| Dunn et al. 2016, *eLife* | 10.7554/eLife.12741 | 359 | 左右交替转向/ARTR → 左右竞争旁证 |
| Bollmann 2019, *Annu Rev Vis Sci* | 10.1146/annurev-vision-091718-014723 | 129 | 综述：特征选择型 RGC 分通道投射 → 分通道输入依据 |

### 2.2 looming 的量化（定义锚点）

**Gabbiani, Krapp & Laurent 1999**（*J Neurosci*，cited 314，PMC 全文可读）给出：

- 逼近几何（Eq.1–2）：`x(t)=v·t`，`θ(t) = 2·tan⁻¹( l / (v·t) )`
- 角边缘速度（Eq.3）：`ψ(t) = θ̇(t)/2 = −(l/v) / (t² + (l/v)²)`
- 关键结论：视觉刺激**仅由 `l/‖v‖` 决定**；θ_thres ∈ 15°–40°，δ ∈ 15–35 ms。

**Temizer 学位论文**（LMU eDoc，Eq.2.1）与之一致：`tan(θ(t)/2) = l/x(t) = l/(v·t)`，l 为半宽（半径），刺激 2°→48° 扩张。

→ 对本项目：瞬时角尺寸 `θ_e = 2·arctan(l_e / r_e)`，`dθ_e/dt = −(2 l_e /(r_e²+l_e²))·(dr_e/dt)`；离散用 `Δθ/Δt`（Δt=0.05s，缓存上一帧距离）。

**风险提示**：Fotowat & Engert 2023（*eLife*，cited 48, DOI 10.7554/eLife.82916）把 dark looming 分解为「整体扩张」与「整体变暗」两个独立成分——纯角尺寸变化率会丢失 dimming 成分，写文档时应注明这是工程近似。

### 2.3 左右 / 相对尺寸编码

- **Harpaz et al. 2021, *Sci Adv***（10.1126/sciadv.abi7460，cited 48）：用「**relative visual field occupancy**」+ 全局视觉运动两个简单响应解释集体行为。
- **Harpaz et al. 2021, *Nat Commun***（10.1038/s41467-021-26748-0，cited 71）：对邻近个体视觉输入做「**retina-wide visual occupancy** 的整合与平均」。

→ 支持通道信号 =「视觉占用/距离核」而非 0/1；也支持左右用**软加权投影**（`w(r)·cos φ`）而非硬阈值。但两文均**未**给出「left/right 二分」的具体公式，故该分解属工程选择。

---

## 三、工程惯例：结构化状态向量 vs raw pixels

| 仓库 | star | license | 做法 |
|---|---|---|---|
| `openai/multiagent-particle-envs` | 2775 | MIT | observation = `[自身速度, 自身位置, 各 landmark 相对位置, 各他体相对位置, 队友速度]` |
| `Farama-Foundation/PettingZoo` | 3523 | MIT | MARL 标准 API；MPE 已迁至 MPE2 |
| `Farama-Foundation/MPE2` | 788 | MIT | MPE 维护后继，沿用相对位置/速度拼接 |

已核验 MPE `scenarios/simple_tag.py`：`entity_pos = entity.state.p_pos - agent.state.p_pos`。这为「用相对几何量拼结构化观测」提供了直接可抄的实现惯例（工程参考，非生物学依据）。

---

## 四、Owner 裁决建议（消除循环引用）

**现状**：DanioNet §2 写「编码规则见 Arena §4（待闭合）」；Arena §4 阅读问题 #1 写「12 维如何由视野算出未定义（对应 DanioNet sensory_dim=12）」。

**推荐方案（分属，单向）**：

| 归谁 | 拥有什么 |
|---|---|
| `connectome/DanioNet设计规范.md §2` | 12 维的**名字、冻结顺序、物理含义、值域/归一化区间**（网络输入接口契约） |
| `arena/Danio_Arena设计与实现说明.md §4`（新增 §4.1） | **由世界几何算出这 12 个分量**的规则：方位角划分、距离核、对象分类、looming 微分、归一化常数 |
| `core/核心机制与数据流.md §10` | 登记边界对象 `observation_12d`：producer=arena，consumer=DanioNet，并记录上述分属 |

**为什么**：`AGENTS.md` 规定「producer owns 边界对象」——Arena 产出 observation。但 12 维的语义/值域是 DanioNet 的输入契约（`U_i x_t` 直接消费），若全归 Arena，DanioNet 无法独立编译校验。分属后方向单向：**Arena 产出满足 DanioNet §2 契约的向量**；两份文档都删除「待闭合/见对方」的互指句。

> 备选（严格 producer-owns）：12 维（含语义名）整体归 Arena，DanioNet §2 仅保留一行「输入为 `arena.observation_12d`，见 Arena §4，不在此重定义」。两者都能消除循环；推荐前者。

**必须同步回写的文档**（沿数据流，缺一即视为未闭合）：
`DanioNet §2` → `Arena §4` → `core §10` → `docs/参数总表.json` → `configs/default_arena.yaml`。

---

## 五、12 维逐项计算草案

**共享记号**（详见 JSON `draft_encoding.shared_symbols`）：
`R=sensing.radius=18`，`halfFOV=110°`，`dt=0.05s`，`φ = wrapToPi(atan2(Δy,Δx) − θ_f)`（正=左），`r=‖Δ‖`，可见 `r≤R 且 |φ|≤halfFOV`；`l_e=s_e/2`（设计选择）。

| # | 维度 | 计算草案 | 依据 / 状态 |
|---|---|---|---|
| 1 | prey_left_signal | `max_{prey,可见,φ>0} w(r)`，无则 0；`w(r)=clamp(1−r/R,0,1)` | 通道=文献；核=设计选择 |
| 2 | prey_right_signal | 同 #1，`φ<0` | 同上 |
| 3 | threat_left_signal | `max_{predator,可见,φ>0} w(r)`（可乘 loom 强度） | 通道=文献；核=设计选择 |
| 4 | threat_right_signal | 同 #3，`φ<0` | 同上 |
| 5 | obstacle_left_signal | `max_{obstacle,可见,φ>0} w(r)` | 纯工程（Arena §11 避障） |
| 6 | obstacle_right_signal | 同 #5，`φ<0` | 纯工程 |
| 7 | prey_relative_size | 对驱动信号那只 prey：`s_prey/s_f`，再 `tanh(·−1)` 或 `clip(·,0,2)/2` | 特征=文献（Bianco 2011）；归一化=设计选择 |
| 8 | predator_relative_size | 对驱动 threat/loom 那只 predator：`s_pred/s_f`，同 #7 归一化 | 同上 |
| 9 | looming_rate | `θ_e=2·arctan(l_e/r_e)`；`dθ_e/dt=−(2l_e/(r_e²+l_e²))·(dr_e/dt)`；取可见 predator 最大值并 `max(0,·)`；离散 `Δθ/Δt` | 形式=文献（Gabbiani 1999 Eq.2/3）；归一化/离散=设计选择 |
| 10 | current_speed | 建议 = 自身 `v_t`（Arena §5，∈[0,1]） | 口径待确认（阻断项） |
| 11 | energy | `E_t/E_max`，Arena §6 | 已知口径 |
| 12 | hunger | `1 − E_t/E_max`，Arena §6 | 已知口径 |

**核函数备选**：线性 `(1−r/R)`（简单）｜视觉占用 `l²/(l²+r²)`（Harpaz 2021 锚点）｜反比 `1/(1+r)`｜软投影 `w(r)·cos φ`（retina-wide 加权，Harpaz 2021）。

**开放工程选择（须写入参数总表并标状态）**：
① 左右划分硬阈值 vs 软投影；② 距离核形式；③ `l_e=s_e/2` 映射；④ looming 归一化参考尺度；⑤ 对象分类是否依赖 size（κ=1.25 仅用于捕获判定）；⑥ 12 维最终值域/归一化常数在 DanioNet §2 冻结。

---

## 六、风险点与下一步

1. **参数漂移**：Arena §4 明言 FOV/radius 非真实解剖值 → 编码规则须与 `configs/default_arena.yaml` 同步。
2. **循环修复的顺序**：必须沿数据流回写（DanioNet §2 → Arena §4 → core §10 → 参数总表 → configs），反序视为违规。
3. **左右通道无现成来源**：文献只支持「视觉占用/分特征通道」，不支持特定的 left/right 二分公式 → 定为项目内设计选择，并做消融（硬阈值 vs 软投影）。
4. **待验证**：`current_speed` 口径；looming 归一化到 [0,1] 的尺度；是否需要把 dimming 成分纳入。

### 未找到

- arXiv 本次检索返回 `HTTP 406`，未取得相关预印本。
- GitHub 检索 `zebrafish tectum` / `looming` 仅 0–4 star 的论文伴随代码，**无**专门实现「斑马鱼左右视觉通道 12 维编码」的开源仓库。故左右通道与距离核的具体实现确无现成可抄来源，必须在项目内定为设计选择。
