# Arena 设计意见（给李辰钊）

> 收件人：李辰钊
> 用途：池伟豪侧对 `arena/` 的审查意见与检索依据，供你整合进 `arena/Danio_Arena设计与实现说明.md`、`Danio_Arena设计与实现说明.md` 与代码。
> 状态：**意见稿（2026-09-26）**，非契约。我们**不直接改 arena 文档**，避免与你并发冲突；采纳与否由你定。
> 配套：`research/notes/arena-api-决策认领表.md`（待你逐条签 `接受/改 X/说明`）。

## 0. 怎么用
1. 每条意见给：**现状 → 我们的意见 → 依据文件**。
2. 你签"接受/改 X/说明"后，写进设计规范正文（去掉 `【草案待确认】`）+ `docs/参数总表.json`。
3. 涉及代码的条目已在"需动"列标注。

---

## 1. 唯一需要你先拍板：世界尺度约定（world unit ↔ BL）
**根因**：项目从未定义 `world unit` 与斑马鱼体长(BL)的换算，导致 `capture_radius=1.2` / `sensing.radius=18 = 0.067`，与生物学的打击/探测比 0.16–0.41 对不上（`docs/参数总表.json` `citation_risks` 已记）。

| 选项 | 含义 | 后果 |
|---|---|---|
| **A** | 1 wu = 1 BL，字面忠实 | `sensing=18` 缩到 <1 wu，现有 100×60 竞技场基本作废，需整体重标 |
| **B（我们推荐）** | 保留现有尺度，只校准**比率** | 承认本世界是缩放抽象；`capture_radius/sensing≈0.16–0.41`、`κ→2.0–2.5`；改动小、竞技场可用 |
| C | 只登记"尺度待定"占位 | 捕获/感知参数暂留现状并标草案 |

**依据**：`research/reference/zebrafish-escape-capture.json`（T2，幼虫探测 0.34–0.77 BL、打击 0.12–0.14 BL、口裂≈4–5% SL）。

---

## 2. 逐条意见

| 编号 | 现状 | 我们的意见 | 依据（`research/reference/`） | 需动 |
|---|---|---|---|---|
| A1 编码主体 | `sin` 分侧、`1-d/r` 距离核、`rel_size` 分式 | **接受**（属设计选择，可离线核对） | `sensory-encoding-12d.{json,md}` | — |
| A1 looming | `clip(10·Δpred_rel,0,1)`，且**恒 0** | **改为角度口径**：\(\theta=2\arctan(l/r)\)、相对扩张率 \(1/\tau=\Delta\theta/(\theta\Delta t)\)、`clip((1/τ)/R_loom,0,1)`，\(R_{loom}\in[2,5]\ \mathrm{s^{-1}}\)；**根因修恒 0**：`step()` 内、实体移动前计算并缓存，`observe()` 只读；不可见天敌重置 prev、取 max | `looming-and-growth.{json,md}` | `sensing.py`+`env.py` |
| A2 捕食几何 | `r_capture=1.2`（纯距离）、`κ=1.25` | **先定 §1 尺度**；`κ` 由绝对门改**尺寸不对称门 2.0–2.5**；补**朝向锥** + 捕获成功率 \(0.5–0.7\)；`r_capture/sensing` 取 0.16–0.41 | `zebrafish-escape-capture.{json,md}` | `env.py`+config |
| A3 能量系数 | `1.0/0.0008/0.0015/0.12` | **接受并登记**；注意：v≈0.8 持续时总代谢≈1.056 > 起始 1.0 → **进食是存活必需**；`food_reward` 宜随 size 递增（见 §12） | `zebrafish-escape-capture.md`(T3 核算) | 参数总表 |
| A4 生长 | `biomass` 只写不读、size 近乎不动 | **单状态 `biomass`**：\(size=size_{min}+(size_{max}-size_{min})(1-e^{-B/B_{ref}})\)；并**声明**真实鱼 30 s 质量变化仅 \(10^{-5}\) 量级，**局内生长本就不可观测**（现状 +1% 已超真实 200–400 倍），生长属跨 episode/世代尺度 | `looming-and-growth.{json,md}` | `env.py`+规范 |
| A5 actors 12 项 | 代码自定 | **接受并登记**（视为 play-test 旋钮，进 YAML + 参数总表） | `param-basis-biology.{json,md}` | YAML+参数总表 |
| A6 边界 | clamp 贴墙耗能 | **改 `world.boundary` 显式项，正式实验默认 `reflect`**；禁用静默 clamp（隐性耗能、跨 seed 能量不可比） | `arena-boundary-collision.{json,md}` | `entities.py`+config |
| A7 碰撞 | 仅计数、无后果、默认不触发 | **软惩罚+硬不穿透**：投影回障碍表面（零反弹）+ 按穿透深度扣能量 \(c_{pen}\cdot\max(0,r_{obs}+r_{fish}-d)\Delta t\)；`arena.collision` 保留但**不作 headline 指标**（零方差），另建"密集障碍"配置；`c_pen` 标定占位 | `arena-boundary-collision.{json,md}` | `env.py` |
| A8 escape | 换目标即算 | **改威胁结局制**：曾被锁定 + 捕食者放弃后继续存活 \(\ge T_{hold}\)（默认 20 步/1 s，占位）才计；"换目标即算"把捕食者重决策记成猎物功劳，上偏最大 | `zebrafish-escape-capture.{json,md}` | `env.py` |
| A9 团灭结束 | 全灭即提前结束 | **改：一律跑满 600**，个体死亡只冻结该个体；若保留提前结束须落盘 `truncated`+实际 `episode_length` 并做协变量校正 | `episode-termination-fitness.{json,md}` | `env.py` |
| A10 转向量纲 | 5.0 rad/s | **接受**（无歧义） | — | — |
| G4 Expert 权重 | 代码 `1.0/1.8/1.2/0.8` | **接受并写进规范 §11**（非"缺参数"，是未落文档） | — | 规范 §11 |
| §12 prey | 不重生；"高价值"未定义 | **开放再生**补至 \(K=24\)；高价值按 \(V=e_{prey}/(1+h_{prey})\) top 分位；`food_reward` 随 size 递增（现状常数=宣称所有 prey 等价，自相矛盾） | `zebrafish-escape-capture.{json,md}`(T3) | `env.py`+config |
| fitness S | 未定 | \(S=survival_{steps}/600\)（固定分母、线性）；加权前**显式尺度归一化**；分量相关需诊断 | `episode-termination-fitness.{json,md}` | `evolution` 文档 |

**保留为标定占位（不得冻结）**：\(c_{pen}\)、\(R_{loom}\)、\(B_{ref}\)、\(T_{hold}\)、捕获成功率。

## 3. 相关资料记录地址（全部在 `research/reference/`）
- `arena-boundary-collision.{json,md}` —— 边界策略、碰撞语义（22 条）
- `zebrafish-escape-capture.{json,md}` —— 逃脱判定、捕食几何、prey 守恒与价值（24 条）
- `looming-and-growth.{json,md}` —— looming 定义与神经编码、生长模型（27 条）
- `episode-termination-fitness.{json,md}` —— episode 终止、survival 归一化、多分量加权（17 条）
- 既有锚点：`sensory-encoding-12d.{json,md}`、`param-basis-biology.{json,md}`、`design-basis-connectome.{json,md}`、`design-basis-neuro.{json,md}`
- 综合：`docs/参数总表.json`（`citation_risks`）、`docs/设计依据审计.md`

> ⚠️ 上述 4 组新文献**尚未登记** `research/notes/bibliography.md`：另一条 lane 正在追加 RGCD 文献（已用 #111+），编号会撞；须协调后再统一登记。

## 4. 我方已做的对齐（无需你处理，知会）
- `§18 实现映射`：参数总表计数 43+11→46+14；`§4.3` core §5.1 改"设计参考"；`§4.4` 实例差异表按现状重写；`§2.2` `capture_size_ratio` 性质改 `status=proposed_change`。
- `arena-api-决策认领表.md`：A7 实测 84 次→0 次（旧基线失效）。
- `设计规范`：已重构为 v0.9 契约骨架（正文写清、条款带 `【已定稿】/【草案待确认】`、§17 待裁决清单），编号 `§4.1`/`§14` 保留。

## 5. 未涉及
- `认领表 B1–B7`（api 语义）本轮未研究，仍待你决定。
- `configs/default_arena.yaml` 无代码读取（B7/M8）为冻结阻断项，建议优先修 loader。
