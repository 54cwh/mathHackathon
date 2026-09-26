# Danio Arena 边界策略与碰撞后果语义：调研摘要

- 调研时间：2026-09-26
- 对应 JSON：`research/reference/arena-boundary-collision.json`
- 范围：二维 agent/生态仿真的边界处理惯例、斑马鱼贴壁行为依据、碰撞处置范式与碰撞代价经验值
- 说明：本文件只做调研与建议，不修改 `research/reference/` 以外任何文件，不登记 `bibliography.md`

---

## 主题 1：二维仿真边界策略

### 现状

代码将位置 clamp 到 `[0,W]×[0,H]`，贴墙卡住且持续耗能，不反弹、不出界即死。设计规范 §2.1 标为「草案待确认」（A6）。实测后果是：速度为 `v>0` 而位移为 0，能量仍按 `dt` 扣除。

### 常见方案与影响

| 方案 | 定义 | 对行为的影响 | 对可复现性的影响 | 对学习难度的影响 |
|---|---|---|---|---|
| wrap（周期/环面） | 越界坐标环绕到对边 | 消除壁，真实鱼群贴壁行为失去对象；引入远距离伪相邻 | 确定性强，但历史基线口径不同 | 视野有限时影响小 |
| reflect（反射） | 越界位移按边法线镜像，朝向关于法线反射 | 近似弹性壁，保留速度连续 | 确定性强，不新增随机源 | 边界附近出现镜像轨迹，可能高频往返 |
| clamp（裁剪，现状） | 位置钉在边界上 | 贴墙卡死，最不像真实鱼 | 确定，但制造与轨迹相关的隐性能量汇 | 目标值与信用分配被污染 |
| absorb+惩罚 | 越界即死或重罚 | 与任务无关的终止 | 确定 | 归为 truncation 更合适，硬终止会改变 bootstrap |

来源：NetLogo Programming Guide（torus/box/cylinder，非环绕边列出反射、退出即死、隐藏三种处置）；Mesa Spaces（`ContinuousSpace(torus=...)`，非 torus 越界抛异常）；Gymnasium「Handling Time Limits」与 Farama「Terminated–Truncated Step API」（越界属 truncation，不属任务终止）；Vicsek 1995（方盒 + 周期边界的原文表述）。

### 斑马鱼依据能否成立

可以，但只支持「壁必须真实存在且可感知」，不支持某个特定算子。

- Schnörr 等 2011 在斑马鱼幼鱼上量化 thigmotaxis（贴壁偏好），引用 490（OpenAlex，2026-09-26），DOI `10.1016/j.bbr.2011.12.016`。
- Shams 等 2015 显示成年斑马鱼 thigmotaxis 可被社交隔离调制，引用 109，DOI `10.1016/j.bbr.2015.05.061`。
- Walz 等 2015 给出术语规范定义「stay close to walls when exploring an open space」，引用 143，DOI `10.1016/j.biopsych.2015.12.016`。

结论是：wrap 抹掉壁，clamp 让鱼钉在壁上一动不动，两者都与「鱼沿壁游动」的观察相悖；reflect 至少保留了壁的物理存在。

### 推荐设计（可直接写入设计规范的一句话条款）

> 边界策略设为显式配置项 `world.boundary ∈ {reflect, clamp, wrap, terminate}`，正式实验默认 `reflect`：把越界位移按边法线镜像、并把朝向关于该法线反射；禁止在正式实验中静默使用 `clamp`（贴墙卡住且持续耗能）与 `wrap`（环面无壁）。

理由：

1. 真实感：斑马鱼在有限有壁水槽中生活，贴壁是可测且可操纵的行为表型，壁应保留。
2. 结果可比：clamp 造成与初始条件相关的隐性能量汇，跨 seed 能量预算不可比；reflect 无隐性耗散。
3. 工程惯例：NetLogo、Mesa、Gymnasium 都把边界当作显式设置或显式语义，不静默裁剪。
4. 可复现：reflect 是纯几何确定性算子，不改变随机流，历史基线不因算子本身作废。

证据等级：**中**。框架规范（NetLogo/Mesa/Gymnasium 官方文档）与行为学（Schnörr/Shams peer-reviewed）都是强证据；但没有「reflect 与 clamp 对学习难度、可复现性」的直接 A/B 对照实验，因此推荐属证据合成，不是实验定论。

风险：

- 镜面反射仍是理想化，真实鱼临近壁会转向或沿壁游，若要更高真实感，P2 可改为「法向软斥力 + 切向沿壁滑行」。
- 角落处多次反射可能产生非自然的高频往返，需定义角点规则并写入文档。
- 新增枚举值须同步 `schemas/` 与 `docs/参数总表.json`，并标注状态，不得由实现自选默认值。

---

## 主题 2：碰撞后果语义

### 现状

代码仅对「鱼–障碍」重叠做每步 +1 计数（`o.contains(fish.pos, 0.1)`），无位移与能量后果，可穿模。实测默认场景 5 seed × 600 步为 0 次触发（A7）。结构原因：`_steer_away_from_obstacles` 只作用于 prey 与 predator（`env.py` L323、L292），不作用于 fish；障碍稀疏（6 个），鱼为随机游走，碰撞近乎不可达。

### 常见处置与取舍

| 处置 | 代表来源 | 取舍 |
|---|---|---|
| 硬约束求解 | Position Based Dynamics（Müller 2007）；ORCA（van den Berg 2011） | 完全消解穿透、无穿模；但不产生「碰撞次数/深度」这一标量信号，指标会恒 0 |
| 软惩罚扣能量 | CADRL（Chen 2017）；Safe RL 综述（Brunke 2022） | 保留可比较、可学习的代价信号，允许偶发违规；参数需标定 |
| 只记录不干预 | 非标准范式 | 轨迹与流场失真，且事件可穿模而漏检；无选择压力 |

Position Based Dynamics 原文指出：约束可按刚度 `k∈[0,1]` 软化（`k=1` 硬、`k=0` 忽略），也可直接投影位置使「penetrations can be resolved completely」，碰撞约束在求解器循环外生成。CADRL 给出的可复用奖励结构经 arXiv 1609.07845 全文核验：碰撞 `d_min<0` 罚 `−0.25`；近碰撞 `d_min<0.2` 罚 `−0.1−d_min/2`；到达目标 `+1`；否则 `0`。

### 推荐设计（可直接写入设计规范的一句话条款）

> 碰撞采用「软惩罚 + 硬不穿透」：越界至障碍物内部时，沿法线把鱼投影到障碍表面（零反弹），并按穿透深度扣除能量 `c_pen·max(0, r_obs+r_fish−d)·Δt`（`c_pen` 为 config 占位参数），同时保留 `arena.collision` 事件计数；不得继续允许穿模或仅计数不干预。

理由：

1. 「只计数不干预」不属于任何标准范式，是本项目特有缺口；标准做法是在硬投影与软惩罚之间选一个。
2. 纯硬约束不产生碰撞标量，无法作行为评价信号；软惩罚保留信号，硬投影消除穿模。
3. 软惩罚可确定性实现、CPU 可复现，适合演化与 BC 的适应度/代价通道。
4. 碰撞率是导航类任务的标准评价维度（Long 2018；CADRL 2017），计数仍有日志与可视化价值。

证据等级：**中偏强**。碰撞处置范式与奖励结构有同行评审支撑；但鱼类单次碰撞/撞壁的能量代价没有经验值，`c_pen` 只能标占位。

风险：

- `c_pen` 无经验值，须标「占位」，不得作为生物学事实写进论文；建议先做敏感性扫描确认排序稳健。
- 位置投影会带来瞬间位移，对 Behavior Cloning 的 action→next-state 映射引入不连续；若 Stage 2 用 ΔW 学习，需评估是否只扣能量、把投影放到步末统一处理。
- 凹角或障碍重叠处法线可能不唯一，需定义确定性规则，否则破坏可复现性。

### 指标处置（事件默认不触发）

> `arena.collision` 保留在事件 schema 中用于日志，但不作为默认场景的 headline 行为指标；另建一个「密集障碍物」配置用于碰撞事件的触发测试与行为探针，正式比较报告须同时给出所用配置与触发率。

理由：零方差指标不含信息，默认场景无法区分任何策略或个体；事件测试需要把输入推到会触发分支的可达区间，这与软件测试的边界值分析一致；碰撞率只有存在碰撞机会时才有意义，报告必须绑定场景配置。

证据等级：**中**。来自本项目实测与通用评价/测试原则，未见专门讨论「零方差指标如何处置」的文献。

风险：若未来给鱼也加入避障 steering，碰撞会更难触发，该指标可能永久退化，须在认领时明确其定位是测试探针还是评价指标；新增密集障碍场景会改变随机流，须与新 seed 基线绑定。

---

## 未找到项（不用低质结果充数）

1. 斑马鱼/鱼类撞壁的反弹系数（restitution）经验值。
2. 鱼类单次碰撞或撞壁的能量代价经验值。最近似的是鱼类最大代谢率与游泳能量学（Norin & Clark 2015，DOI `10.1111/jfb.12796`；Lauder 2014，DOI `10.1146/annurev-marine-010814-015614`），但不含单次碰撞代价。
3. reflect / clamp / wrap / absorb 对可复现性与学习难度的直接对照实验。
4. 斑马鱼视觉/侧线障碍避让的定量模型参数。OpenAlex 标题检索无匹配；arXiv 检索 API 本轮持续返回 HTTP 406，未能检索。
5. NetLogo bounded「box」下越界究竟是严格 clamp 位置还是停止移动，官方文档表述为「cannot move beyond the edge」，未明确定义，故不作断言。

---

## 依据条目索引

主题 1 关键来源

| 条目 | 类型 | URL / DOI | peer-reviewed |
|---|---|---|---|
| NetLogo 7.0.4 Topology | 官方文档 | https://docs.netlogo.org/7.0.4/programming | 否 |
| Mesa Spaces | 官方文档 | https://mesa.readthedocs.io/en/stable/apis/space.html | 否 |
| Gymnasium Handling Time Limits | 官方文档 | https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits | 否 |
| Farama Terminated–Truncated | 官方博客 | https://farama.org/Gymnasium-Terminated-Truncated-Step-API | 否 |
| Vicsek 1995 | 论文 | 10.1103/PhysRevLett.75.1226 | 是 |
| Schnörr 2011 thigmotaxis | 论文 | 10.1016/j.bbr.2011.12.016 | 是 |
| Shams 2015 thigmotaxis | 论文 | 10.1016/j.bbr.2015.05.061 | 是 |
| Walz 2015 thigmotaxis 定义 | 论文 | 10.1016/j.biopsych.2015.12.016 | 是 |
| mesa/mesa | 仓库 | https://github.com/mesa/mesa | 否 |
| NetLogo/NetLogo | 仓库 | https://github.com/NetLogo/NetLogo | 否 |
| Farama-Foundation/Gymnasium | 仓库 | https://github.com/Farama-Foundation/Gymnasium | 否 |

主题 2 关键来源

| 条目 | 类型 | URL / DOI | peer-reviewed |
|---|---|---|---|
| Müller 2007 PBD | 论文 | 10.1016/j.jvcir.2007.01.005 | 是 |
| van den Berg 2011 ORCA | 论文 | 10.1007/978-3-642-19457-3_1 | 是 |
| Chen 2017 CADRL | 论文 | 10.1109/ICRA.2017.7989037；arXiv 1609.07845 | 是 |
| Long 2018 | 论文 | 10.1109/ICRA.2018.8461113 | 是 |
| Brunke 2022 Safe RL | 综述 | 10.1146/annurev-control-042920-020211 | 是 |
| Dulac-Arnold 2021 | 论文 | 10.1007/s10994-021-05961-4 | 是 |
| Norin & Clark 2015 | 论文 | 10.1111/jfb.12796 | 是 |
| Lauder 2014 | 综述 | 10.1146/annurev-marine-010814-015614 | 是 |

GitHub star 与引用数均为 2026-09-26 实测；未核实项已在 JSON `notes` 中标注。
