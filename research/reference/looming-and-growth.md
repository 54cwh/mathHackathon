# looming_rate 与生长模型：调研摘要

> 对应 `research/reference/looming-and-growth.json`（27 条依据：looming 14、growth 13）。
> 检索时间 2026-09-26。本文件只做证据与设计建议，不改代码、不改规范正文。
> 依据等级：**A**=同行评审 + 原始全文/摘要可核；**B**=同行评审但本次仅二手引述；**C**=书/预印本/代码。

## 结论速览

| 分级 | 条款 |
|---|---|
| **推荐直接用** | ① looming 用**角度口径**：`θ=2·arctan(l/r)`，主通道取**相对扩张率** `1/τ=θ̇/θ`；② 归一化 `loom=clip((1/τ)/R_loom,0,1)`，`R_loom` 进 config；③ 恒 0 根因修复=step() 内每步一次、移动前计算并缓存；④ 生长让 `biomass` 成为**被读取的唯一状态**，`size` 由其饱和映射导出；⑤ 单局 30 s 内 `size` 视为常数，生长属跨 episode 尺度。 |
| **仅作参考** | 金鱼/鳕/鲱作为替代物种的阈值与生长函数形式；TTC 工程库（`Yiru-Jiao/Two-Dimensional-Time-To-Collision` 等）。 |
| **不建议** | 保留 `clip(10·Δ(predator_relative_size),0,1)` 作为主定义；保留 `biomass` 只写不读；不声明时间压缩就调大生长系数。 |

---

## 主题 1：looming_rate 的定义与神经编码

### 1.1 标准定义：是视角变化率，不是相对尺寸变化率

looming 的标准对象是**逼近物体在视网膜上张成的视角（visual angle）的扩张**，不是「物体尺寸/距离」这个比值本身。两条权威口径携带同一几何信息：

- **角口径（Gabbiani 1999）**：`θ(t)` 为视角，`ψ(t)=θ̇/2` 为角边缘速度；LGMD/DCMD 发放率 `∝ ψ(t−δ)·e^{−α·θ(t−δ)}`，`α=1/tan(θ_thres/2)`。峰值出现在**固定角度阈值** `θ_thres∈[15°,40°]`、延迟 `δ∈[15,35] ms`，且**独立于目标大小与速度**。〔A，DOI 10.1523/jneurosci.19-03-01122.1999，cited 314〕
- **相对扩张率口径（Lee 1976）**：`τ=θ/θ̇` 为碰撞时间（time-to-collision），其倒数 `θ̇/θ=1/τ` 是**无量纲**的相对（分数）扩张率。〔A，DOI 10.1068/p050437，cited 2109〕

两条口径的关系：`1/τ` 就是 `θ̇` 除以 `θ`。在 `r≫l` 时 `θ≈2l/r`，故 `1/τ≈v_close/r`——**尺寸无关、距离归一**。

Gabbiani 2001 进一步证明该角度计算对**形状（方/圆）、纹理、逼近角（水平面 ≥135°）不变**，这为 Arena 把天敌简化为圆盘提供了直接依据。〔A，DOI 10.1523/jneurosci.21-01-00314.2001，cited 118〕

**当前代码的问题**：`clip(10·Δ(predator_relative_size),0,1)` 里的 `predator_relative_size = min(pred_size/fish.size/2.5, 1)` 是「表观尺寸比」，它的差分既不是角度、又额外按**自身体型**和常数 2.5 归一化。这属于设计选择，不是文献口径；且 `10·Δ` 是**每步差**（dt=0.05 时等价于 `0.5·d(rel)/dt`），**随 hz 改变语义**。

### 1.2 斑马鱼/金鱼 looming→escape 的关键量与阈值

| 范式 | θ_thresh | 潜伏期 | 来源 | 等级 |
|---|---|---|---|---|
| 成鱼斑马鱼（投影刺激，最佳拟合） | **10.3°–15.8°** | 740–780 ms | McKee & McHenry 2020, DOI 10.1093/iob/obaa023 | A（PMC7750966 全文核对） |
| 成鱼斑马鱼（活体捕食者，四分位） | Q1 低至 6.3°，Q3 ≤17.4° | — | 同上 | A |
| 幼虫斑马鱼（头固定） | **21.7°** | 35 ms | Temizer et al. 2015, DOI 10.1016/j.cub.2015.06.002 | B（经 McKee 全文引述） |
| 幼虫斑马鱼（自由游动） | **≈72°** | 81 ms | Dunn et al. 2016, DOI 10.1016/j.neuron.2015.12.021 | B（PMC4742414 + McKee 双源） |
| 金鱼（替代物种） | ≈21° | 35 ms | Preuss et al. 2006, DOI 10.1523/jneurosci.5259-05.2006 | A（正文摘要）+ B（21° 引述） |

其他关键量：
- 金鱼 C-start 响应概率 0.7–0.91，平均潜伏期 142–716 ms；阈值与动态缩放视角 `κ(t)=θ(t−δ)·e^{−β(t−δ)}` 相关，**κ 先升后降、峰值在碰撞前**——即决定逃逸时机的是「缩放后的视角」而非视角变化率本身。〔A，Preuss 2006〕
- 成鱼斑马鱼模型预测：只有当捕食者逼近速度**慢于约 2 倍猎物逃逸速度**时，视角阈值才能提供有效逃逸。〔A，McKee 2020〕
- dark looming 含**整体扩张**与**整体变暗**两个独立成分，纯几何扩张会丢失 dimming。〔A，Fotowat & Engert 2023，DOI 10.7554/eLife.82916〕
- 威胁响应随强度**连续校准**，支持连续标量而非 0/1。〔A，Bhattacharyya 2017，DOI 10.1016/j.cub.2017.08.012〕

### 1.3 推荐设计（可写进规范的条款）

> **looming_rate** 定义为相对扩张率：`θ_e=2·arctan(l_e/r_e)`（`l_e=s_e/2`），`1/τ = (θ_t−θ_{t−1})/(θ_t·Δt)`，取所有可见天敌的最大值，`looming_rate = clip((1/τ)/R_loom, 0, 1)`；`R_loom` 为 config 参数（建议 2–5 s⁻¹，即 τ_ref=0.2–0.5 s）。

**理由**
1. 无量纲、对目标尺寸/距离尺度近似不变（`r≫l` 时 `1/τ≈v_close/r`），比原始角速度 `θ̇`（rad/s）更易归一化且无需无依据的常数。
2. 非逼近时为 0、逼近时增大、接触附近饱和，天然落在 `[0,1]`（截断后），适合 DanioNet 输入。
3. 角度口径可被实测阈值直接标定，具备跨物种锚点。

**离散实现 + 恒 0 根因修复（伪代码）**

```python
# 常量：LOOM_EPS=1e-3；R_LOOM 来自 config（default 3.0 1/s）
# 每步、实体移动之前执行（保证 prev 与 now 来自相邻两步）
for fish in alive_fish:
    inv_tau_best = 0.0
    for d in alive_predators:
        if not visible(fish, d, radius, fov):
            continue
        r = norm(d.pos - fish.pos)
        l = 0.5 * d.size
        theta_now = 2.0 * atan2(l, r)
        theta_prev = fish._prev_theta.get(d.entity_id, theta_now)
        dtheta = (theta_now - theta_prev) / dt
        inv_tau = max(0.0, dtheta / max(theta_now, LOOM_EPS))
        inv_tau_best = max(inv_tau_best, inv_tau)
        fish._prev_theta[d.entity_id] = theta_now
    fish.looming_rate = clip(inv_tau_best / R_LOOM, 0.0, 1.0)
# 然后再推进实体；observe() 中 obs[8] = fish.looming_rate
```

- **恒 0 的根因**：`observe()` 读到的 `pred_rel` 与 `_prev_predator_rel` 由构造来自同一时刻，差分必然为 0（除 reset 首帧）。修法是把 loom 改成 **step() 内每步一次、移动前算、缓存标量**，`observe()` 只读。这是根因修复而非补丁。
- **取 max 而非 nearest**：仅取最近者会在「最近目标切换」时产生伪尖峰；建议对所有可见天敌取 `1/τ` 最大者，并对不可见目标重置其 prev 缓存。

**标定参考（Arena 世界单位，`predator_size=2.0`）**

| r（世界单位） | θ | 对应生物阈值 |
|---|---|---|
| 18（sensing_radius） | 6.4° | 低于成鱼阈值 |
| 5 | 22.6° | 幼虫头固定 21.7° / 金鱼 21° |
| 1.2（capture_radius） | 79.6° | 幼虫自由游动 72° |

即：用**角度阈值**做触发时，通道在 `r≈7–11` 才进入成鱼生物相关区；若要在更远处就有区分度，用 `1/τ` 口径并声明其标定为工程选择。

**风险**
- Arena 是二维俯视图，「视角」是投影宽度而非立体包角，与文献三维刺激只是近似。
- dimming 成分丢失，须声明为工程近似。〔Fotowat & Engert 2023〕
- 阈值随范式剧变（头固定 21.7° vs 自由 72°），选用哪个必须写明。
- `R_loom` 是新的自由参数，需在 `configs/` 与 `docs/参数总表.json` 登记并做敏感性消融。

---

## 主题 2：生长模型（biomass → size）

### 2.1 标准模型

- **von Bertalanffy 1938**：`dL/dt = k·(L∞−L)`，生长=合成−分解；天然产生凹增长与软上限。〔A，JSTOR 41447359〕
- **West/Brown/Enquist 2001**：`dB/dt = a·m^{3/4} − b·m`（获取−维持）。〔A，DOI 10.1038/35098076，cited 1207〕
- **等效性**：VBGF 本身即生物能量学表达。〔A，Essington 2001，DOI 10.1139/f01-151〕
- **能量收支**：`C = R + P + F + U`，`P` 即生长/生产项。〔A，Deslauriers 2017，DOI 10.1080/03632415.2017.1377558〕
- **DEB**：能量在维持/生长/成熟间分配。〔C，Kooijman 2010，DOI 10.1017/CBO9780511805400〕
- **斑马鱼专属先例**：Beaudouin et al. 2015 把斑马鱼 DEB 与 IBMs 耦合，并拟合斑马鱼生长与繁殖数据——落地参数化的最接近起点。〔A，DOI 10.1371/journal.pone.0125841〕
- **体长↔体重**：`W=a·L^b`，跨 1773 种鱼 `b` 中位 = 3.03。〔A，Froese 2006，DOI 10.1111/j.1439-0426.2006.00805.x〕

**决定生长速率的量**：摄食量（C / 比摄食率）、维持代谢（∝ m 或 m^{3/4}）、体重本身（越大比生长率越低）。Checkley 1984 给出生长与摄食的线性关系及饥饿负增长 0.03/d；Björnsson 2001 给出生长率随体重在 log-log 上下降；Hazlerigg 2012 证明斑马鱼生长受食物限制。〔均为 A，替代物种/斑马鱼〕

### 2.2 单局 600 步（30 s）内是否应有可观测生长？

**结论：不应有，且「几乎不动」是正确的生理结论。**

用分期体长 + `W∝L³` 估算比生长速率 SGR（`=ΔlnW/Δt`），再乘 30 s：

| 窗口 | 体长 | SGR（质量）/d | 30 s 内质量相对变化 |
|---|---|---|---|
| 5–21 dpf 幼虫 | 3.9→7.8 mm TL | ≈13.0% | **≈0.0045%** |
| 21–30 dpf | 7.8→10 mm TL | ≈8.3% | ≈0.0029% |
| 30–45 dpf 幼鱼 | 10→14 mm TL | ≈6.7% | ≈0.0023% |
| 45–90 dpf | 12→18 mm SL | ≈2.7% | ≈0.0009% |

数据源：ZFIN staging table（tavily 抓取）+ Singleman & Holtzman 2014（PMC4108942）+ Froese 2006 的 b≈3。

即真实斑马鱼 30 s 内质量相对变化约 **1e-5–5e-5（0.001%–0.005%）**。代码实测 `1.00→1.01`（+1%）已比真实速率大约 **200–400 倍**。所以：
- `size` 在单局内应视为**近似常数**，生长属**跨 episode / 跨世代**（个体发育—演化）尺度；
- 若 demo 需要可见生长，必须**显式声明时间压缩**（例如每 N 个 episode 折算 1 天，或 config `growth.time_compression`），禁止不声明就把 `k_g` 调大。

### 2.3 推荐形式（可写进规范的公式）

**主推荐：让 `biomass` 成为被读取的唯一状态，`size` 由其饱和映射导出**

```
捕获时：  B ← B + s_prey
体型：    size = size_min + (size_max − size_min)·(1 − exp(−B / B_ref))
```

- `B_ref` 为 config 参数（达到约 63% 体型范围所需的累积猎物体量）。反解标定：`B_ref = −N·s̄ / ln(1−p)`（N 次平均捕获后 size 达体型范围的 p 比例）。
- **理由**：① 消除镜像量（当前 `biomass` 与 `size` 是同一输入的平行累加器，等价于 `biomass = size/k_g + const`）；② exp 映射单调、凹、渐近 `size_max`，符合 VBGF 与获取−维持能量学，无需硬 `min()` 截断；③ `B` 对应 `C=R+P+F+U` 的 `P`，与现有 energy 方程的 `R_food` 同源；④ 可复现标定路径明确。

**最小改动备选（不重构时）**

```
size ← min(size_max, size + k_g·s_prey·(1 − size/size_max))
```

并把 `biomass` 明确降级为「展示用累积摄入」、从生长公式解耦（或删除）。**切勿保留两个平行累加器。**

**已有的博弈化耦合（保留）**：体型增大 → 可捕食更大 prey（`size > κ·prey.size`）、转向惯性上升（`ω_eff=ω/(1+k_turn(size−1))`）、代谢代价上升。三项使「大」非单向优势，属可保留的设计。

**风险**
- `B_ref`（或 `k_g`）是新的自由参数，必须登记进 `configs/` 与 `docs/参数总表.json` 并做敏感性/消融。
- 若生长更新跨 episode，需固定种子并持久化跨 episode 状态。
- exp 映射只按累积总量算 size，丢失「一次大猎物 vs 多次小猎物」的构成信息；若要保留可改为 `ΔB = s_prey^α`（设计选择，须文档化）。

---

## 未找到项（不充数）

1. **arXiv 预印本**：本次 arxiv MCP 返回 HTTP 406，未取得任何预印本，故该 JSON 无 arXiv 来源。
2. **可复用的斑马鱼 looming / 12 维视觉编码开源实现**：GitHub 检索 `looming` 命中的全是同名录音软件或 Java Project Loom；`time-to-collision` 命中的是自动驾驶/机器人 TTC 库（`Yiru-Jiao/Two-Dimensional-Time-To-Collision` 64★、`cschwarz68/TimeToCollision` 13★）。**没有**生物编码实现可抄，必须在项目内定为设计选择。
3. **Gabbiani 1999/2001 正文公式逐字核对**：仅取到 OpenAlex 摘要（含公式符号）；引用前应回查正文 Eq. 编号。
4. **Dunn 2016 的 72°/81 ms 原始表**：经 PMC4742414 + McKee 2020 双源二手交叉验证，未从正文表直接取。
5. **斑马鱼物种特异 `W=a·L^b` 参数**：未定位到斑马鱼专属 LWR 参数表；质量换算用 Froese 2006 跨物种 `b≈3` 近似。

## 需进一步验证的风险点

1. Gabbiani 1999/2001 正文 Eq.（本次仅摘要级核对）。
2. Dunn 2016 原始阈值表（本次为二手）。
3. Froese 2006 是否含斑马鱼物种特异 `b`。
4. `R_loom` 与 `B_ref` 的取值必须在 demo 运行中做方差/敏感性消融后才能冻结——目前只给形式与标定路径，不给「已定稿」数值。
5. 现行 `looming_threshold_adult` / `looming_threshold_larval`（`docs/参数总表.json`）的「口径二选一」应与本文件的「角度 vs 相对扩张率」裁决同步，避免阈值口径与通道口径错配。
