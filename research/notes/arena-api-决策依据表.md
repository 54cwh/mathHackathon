# arena / api 决策依据表

> 收件人：李辰钊（业主）
> 目的：对 `research/notes/arena-api-决策认领表.md` A / B 两节共 **17 项**，加业主另问的 **E1–E3 三项**，合计 **20 项**，逐项回答一个问题：**这一项有没有上游依据？**
> 本表**不提供建议、不替业主选择**。每一项只做三件事：① 指出依据在哪（文件 § / 行号 / commit）；② 若无依据，明确宣告"无依据"；③ 若有依据而代码不符，指出不符在哪。
> 基准提交：`main` @ `d414e05`。工作区有未提交改动时，本表明确区分 HEAD 版与工作区版。
> 编制时间：2026-09-26。本文件为只读审计产物，未修改任何既有文件。

---

## 0. 判据、标签与证据分级

### 0.1 三种标签（严格三选一，不混用）

| 标签 | 判定条件 | 含义 |
|---|---|---|
| **有依据，代码一致** | 上游文档（或已入库契约文件）对该项有明文规定，且代码/文件与之一致 | 无需认领 |
| **代码偏离依据，属缺陷** | 上游文档有明文规定，代码/文件与之**不符** | 比"无依据"更严重：不是没定，是定了没做 |
| **无依据，需认领** | 上游文档对该项**没有任何规定** | AI/实现者自选，需业主认领 |

### 0.2 混合项的处理规则

一项常由若干子项组成（例如 A2 = 半径 + κ + 角度口径）。**混合项在"本项性质"栏按主标签填，但必须在"细分"栏逐子项写明各自状态**，尤其要区分：

- **框架有依据、系数无依据** —— 文档给了公式/机制，但没给数值（A3、A4 属此类）；
- **部分子项有依据且一致、其余无依据**（A1、A2、A7、A9、A10、B5、B6、E1 属此类）。

不允许因为"框架有依据"就笼统写"有依据"。

### 0.3 证据分级（决定一条依据算不算依据）

| 级 | 文件 | 可否作为依据 |
|---|---|---|
| **A 级** | `src/evogenesis/arena/Danio_Arena设计规范.md`、`src/evogenesis/api/API与系统工程.md`、`docs/参数总表.json`、`docs/验收清单.md`、`src/evogenesis/experiment/实验与评价体系.md`、`src/evogenesis/connectome/DanioNet设计规范.md`、`src/evogenesis/core/核心机制与数据流.md`、`src/evogenesis/development/RGCD数学模型.md`、`src/evogenesis/evolution/遗传繁殖与演化模型.md`、`src/evogenesis/EvoGenesis项目总纲.md`、`src/evogenesis/问题定义与研究假设.md`、`docs/赛题补充说明.md`、`configs/*.yaml`、`schemas/*.schema.json` | **可以**。其中 A 级文档末尾的 `## 阅读问题（待确认）` 小节是**高价值证据**（设计者自陈未定义） |
| **B 级** | `archive/DNA2Brain_项目交接稿_v0.1.md` | **只能作旁证**。属被取代的 v0.1 交接稿，不在现行设计包内；本表凡引用均标注"B 级" |
| **C 级** | `src/evogenesis/arena/Danio_Arena实现说明.md`（**未入库 `??`**）、`src/evogenesis/api/API接口.md`（含未提交改动）、`research/notes/arena-api-决策认领表.md` | **不可以作依据**。这三份文件自我声明"描述**现在怎样**（实现），不等于**设计已如此规定**"（`Danio_Arena实现说明.md` L6、L15；`API接口.md` L6–8）。它们只能证明"代码现在是什么样"。**若用它们论证设计，等于用实现论证实现** |

### 0.4 三个必须先知道的"依据自身有问题"的发现

1. **`src/evogenesis/core/核心机制与数据流.md §5.1` 的工作区版本是未提交改动，且是为对齐代码而改写的。**
   `git diff` 显示：HEAD（`d414e05`）版的 §5.1 标题是「事件类型（**草案，待冻结**）」，只有 6 行、事件名为 `spawn / prey_captured / escape / energy_depleted / capture_attempt / episode_end`，且 `escape` 一行的载荷写「威胁源、**反应时延**」。工作区版被改成「**v1 定稿，待池伟豪确认**」的 8 行表，事件名改为 `arena.*`，`escape` 触发改为「换掉已锁定目标且旧目标仍存活」，并新增 §10 待办 #4。
   该改写与 `Danio_Arena实现说明.md §4.2/S17` 完全同源，而后者是 C 级实现文档。
   ⇒ **工作区版 §5.1 不能作为 A8 / A9 / A2 的"上游依据"**。本表凡涉及 §5.1 均标注版本。
2. **`docs/参数总表.json` 与 `arena/config.py` docstring 自称的 "frozen values" 有落差。**
   `config.py` L3 写「Defaults mirror `configs/default_arena.yaml` (frozen values, `docs/参数总表.json`)」，但 `docs/参数总表.json` 全文 42 行**只收录 Arena 的 10 个量**：`world_width / world_height / sim_hz / episode_seconds / episode_steps / live_fish / live_prey / live_predators / live_obstacles / capture_size_ratio`（L24–33、L40）。`sensing.*`、`energy.*`、`growth` 除 `capture_size_ratio` 外的 4 项、`actors.*` 全部 12 项**均未收录**。
   ⇒ 凡本表写"参数总表无此行"，即该值**不是冻结量**，不得作为"冻结参数"引用。
   （同类落差已有先例：`EvoGenesis项目总纲.md` 阅读问题 #5 L149 就指出「§6 给范围 10%–20%，`docs/参数总表.json` / config 为单值 0.15」——即本项目已有"文档范围 vs 参数表单值"的记录习惯。）
3. **`configs/` 与代码之间没有任何加载通路，且 `core/` 缺少文档承诺的 `config` 模块。**
   全仓 `grep -rn "yaml\.\|safe_load\|load_config"` 在 `src/ tests/ scripts/` 内**零命中**；`yaml` 一词的全仓唯一出处是 `api/schemas.py` L28–29 的两个默认值字符串。`src/evogenesis/core/` 只有 `__init__.py`（0 字节）与 `seed.py`（251 字节），而 `核心机制与数据流.md §1` L3 明文把「`config`（配置加载）、`logging`、`tracking`、`registry`、`io`」列为 `core/` 必须提供的模块。
   ⇒ 这是 B7 的直接实证（见 B7 行）。

---

## 1. 汇总统计（20 项，逐项已给结论，无"待查"）

### 1.1 按"本项性质"主标签

| 标签 | 项数 | 项号 |
|---|---:|---|
| **有依据，代码一致** | **1** | E2 |
| **有依据，且不一致已被登记为待办**（既非无依据、亦非新缺陷） | **1** | E3 |
| **代码偏离依据，属缺陷** | **3** | B1、B3、B7 |
| **无依据，需认领** | **15** | A1–A10（10 项）、B2、B4、B5、B6、E1 |
| 合计 | **20** | — |

### 1.2 "无依据"15 项的内部再分（判断严重程度用）

| 细分 | 项数 | 项号 |
|---|---:|---|
| **完全无依据**（整项没有任何子项可引上游） | **5** | A5、A6、A8、B2、B4 |
| **含部分有依据**（至少一个子项能引到上游且已一致，其余无依据） | **10** | A1、A2、A3、A4、A7、A9、A10、B5、B6、E1 |

### 1.3 20 项的"依据来源"总览

| 项 | 主标签 | 依据来源（或无） |
|---|---|---|
| A1 | 无依据 | 顺序 ← `DanioNet设计规范.md §2` L13–25 + `验收清单.md` L15；公式 ← **无**（`设计规范 §4` 阅读问题 A1 L176–178） |
| A2 | 无依据 | κ ← `设计规范 §8` L106–110 + `参数总表.md` L40；`r_capture` ← **无** |
| A3 | 无依据 | 公式 ← `设计规范 §6` L71–81；四系数 ← **无** |
| A4 | 无依据（+1 偏离点） | 机制 ← `设计规范 §7` L83–91；三系数 ← **无**；`biomass` 只写不读 ← **偏离 §7** |
| A5 | 无依据 | **无**（`设计规范 §9/§10` 只有定性；`阅读问题 C11` L196） |
| A6 | 无依据 | **无**（`设计规范 阅读问题 B2` L181–182 明写未定义） |
| A7 | 无依据 | 记录要求 ← `设计规范 §13` L157–169；后果 ← **无**（`阅读问题 B3` L183） |
| A8 | 无依据 | **无**（`设计规范 阅读问题 B6` L186–187 明写未定义） |
| A9 | 无依据 | 600 步 ← `设计规范 §2` L19–23 + `参数总表.md` L27–28；团灭即结束 ← **无**（`阅读问题 B7` L188–189） |
| A10 | 无依据 | 鱼 ω ← `设计规范 §5` L52–53（含 Δt，间接）；天敌/猎物 ← **无**（`阅读问题 C8` L192） |
| B1 | **代码偏离** | `API与系统工程.md §4.3` L80「释放鱼进入 Arena」 |
| B2 | 无依据 | **无**（`API与系统工程.md 阅读问题 #4` L141） |
| B3 | **代码偏离** | `API与系统工程.md §3` L39–46 列为稳定 ID |
| B4 | 无依据 | **无**（`§4.1 R8` L60 只有 5xx 桶） |
| B5 | 无依据 | `sys.error` ← `§4.1 R11` L63；`sys.hello`/`sys.echo` ← **无**（`阅读问题 #5` L142） |
| B6 | 无依据 | **无**（`§4.3` L85 无请求体；两份已入库契约冲突） |
| B7 | **代码偏离** | `参数总表.md` L42 + `核心机制与数据流.md §7` L162 + `§1` L3 |
| E1 | 无依据 | 三档名称 ← 5 处文档；差异方向 ← `archive` B 级 §12 L596–610；旋钮映射 ← **无** |
| E2 | **有依据，一致** | `核心机制与数据流.md §4.5` L107 + `§10 #1` L201 + `examples/README.md` L17 |
| E3 | **有依据（已登记待办）** | `examples/README.md` L18 + `核心机制与数据流.md §10 #4` L204 |

---

## 2. 主表

| 项 | 事项 | 上游文档是否有规定 | 依据（文件 § / 行 / commit） | 原文要点 | 本项性质 | 细分 |
|---|---|---|---|---|---|---|
| **A1** | 12 维感官编码归一化公式（强度衰减 `1−d/radius`、`prey_relative_size`、`predator_relative_size` 的 `/2.5`、`looming ×10`、左右按 `sin(bearing)` 分侧） | **部分**：只有"12 维的名字与顺序"有规定；**全部归一化公式无规定** | **顺序有依据**：`src/evogenesis/connectome/DanioNet设计规范.md §2` L13–25（12 个名字按 1–12 列出）；`docs/验收清单.md` L15「12 维输入顺序固定」（硬性验收项）；代码 `arena/sensing.py` L25–38 `DIM_NAMES` 与 §2 **逐项同名同序 → 一致**。**公式无依据**：`arena/Danio_Arena设计规范.md` 阅读问题 A1 L176–178「12 维 sensory 如何由视野算出**未定义**……left/right channel 如何编码（距离、方位、对象类型、相对朝向）以及如何拼成 12 维向量**未写**」；`connectome/DanioNet设计规范.md` 阅读问题 #1 L115 同向；`设计规范 §4` L33–40 只说 finite radius / finite FOV，未给衰减函数 | `设计规范 §4` L40：「FOV/radius **为 config 参数**，不作为真实斑马鱼解剖测量值」——只授权"它们是 config 参数"，未授权取值或公式；阅读问题 L177 自陈「config 已给 `sensing.radius=18`、`fov_degrees=220`，但……未写」 | **无依据，需认领** | 顺序＝有依据且一致（唯一约束来自 `验收清单.md` L15「顺序冻结」，改动须双方同步）；五个公式＝AI/实现者自选。⚠️ `sensing.radius=18`/`fov_degrees=220` 只存在于 `configs/default_arena.yaml` L13–14，**不在 `docs/参数总表.json`**（对照 §0.4-2）。代码位置：`sensing.py` L68（强度）、L69–72（分侧）、L110（`/2.5`）、L136（`min(size/fish.size,1)`）、L142–143（`×10`） |
| **A2** | 捕食几何：`capture_radius=1.2`；`capture_size_ratio κ=1.25`；有无朝向/口部角度判定 | **部分**：κ 有；`r_capture` 无；角度口径无（但 §8 也**未要求**） | **κ 有依据**：`设计规范 §8` L106–110「初始 κ=1.25」；`docs/参数总表.json` L40「capture_size_ratio \| 1.25」→ 代码 `arena/config.py` L49 = 1.25，**一致**，且已进冻结表。**`r_capture` 无依据**：全仓 grep，`capture_radius` 在设计侧只出现在 `设计规范` L184（阅读问题，以符号引用）与 §8 L96–98 的符号 `r_capture`（**无值**）；`参数总表.md` 无此行；唯一写值处是 `configs/default_arena.yaml` L24 `capture_radius: 1.2`。**角度**：§8 L93–104 只给两条必要条件（距离 + 尺寸比），**未要求**朝向/口部角度 → 「无角度判定」与 §8 字面一致 | `设计规范 §8` L112：「最终通过 play-test 校准」（对 κ 的保留）；判据仅 `d<r_capture` 与 `size_hunter>κ·size_target`（L96–104）；阅读问题 #4 L184 另声明「**捕食关系是否双向未定义**：predator(3) 能否吃 Danio fish、被吃鱼的后果（死亡或扣分）未写」 | **无依据，需认领** | κ＝冻结量、有依据一致（认领时应答"是否继续由 play-test 校准"，§8 L112 预留了口子）；`r_capture=1.2`＝实现者自选（`env.py` L199 鱼、L300 天敌）；"无角度判定"＝§8 未要求，**不构成缺陷**。⚠️ 代码另实现了**双向捕食**（`env.py` L266–314 天敌吃鱼），而 §8 阅读问题 #4 L184 明写双向性未定义 → 该子项亦**无依据** |
| **A3** | 能量四系数 `e_max=1.0` / `base_cost_per_step=0.0008` / `movement_cost_scale=0.0015` / `food_reward=0.12` | **框架有依据、系数无依据** | **框架有依据**：`设计规范 §6` L71–79 给 `E_{t+1}=clip(E_t−C_base−C_move·v_t²+R_food, 0, E_max)`、`H_t=1−E_t/E_max`，L81「energy=0 时死亡」→ 代码 `arena/env.py` L240–251 与之一致（含 `v²`、clip 到 `[0,e_max]`、H 公式、E≤0 判死）→ **一致**。**系数无依据**：`docs/参数总表.json`（全文 42 行）**不含**这四个键；`设计规范` 里它们只以符号 `C_base / C_move / R_food / E_max` 出现，无值 | `设计规范 §6` L71–81 只给公式与符号，符号之外**无任何取值** | **无依据，需认领**（框架有依据且一致） | 公式＝有依据；四个数＝AI/实现者自选。代码位置：`config.py` L39–42。⚠️ `e_max` 另在 §6 L78 作为 `H` 的分母出现、`food_reward` 另在（工作区）`核心机制与数据流.md` L121 作为 payload 名出现——**这两处都是符号/字段名，都不是取值依据** |
| **A4** | 生长 `initial_size=1.0` / `max_size=2.5` / `biomass_to_size_gain=0.02`；`biomass` 是否被读取 | **框架有依据、系数无依据、且 `biomass` 语义偏离依据** | **框架有依据**：`设计规范 §7` L83–84「吃到 prey 增加 biomass，**biomass 使 size 缓慢增长并设上限**」+ L86–91（体型增大带来「可捕食更大 prey / metabolic cost ↑ / turning inertia ↑」，「因此'大'不是单向优势」）。**系数无依据**：`参数总表.md` 无 `initial_size`/`max_size`/`biomass_to_size_gain`；§7 未给任何数值。**偏离**：`arena/env.py` L206 `fish.biomass += prey.size` **只写**；L207–210 `fish.size = min(max_size, size + gain*prey.size)` 用 `prey.size` 而非 `biomass`；全仓**无任何读取 `biomass`** 之处 → §7 的「biomass **使** size 增长」因果链在代码里不成立 | §7 L84「缓慢增长并设上限」（"缓慢"无量化）；`config.py` L52 自注 `# MVP calibration knob (play-test later)`；§7 L86–91 只列三条后果，未给数值 | **无依据，需认领**（系数）；**`biomass` 只写不读＝代码偏离 §7，属缺陷** | 三个数＝实现者自选；`biomass` 镜像量＝偏离。注：认领表 A4 与 `实现说明.md §7` 均记"实测单局 size 1.00→1.01"，但 §7 的"缓慢"**无上界**，故"几乎不动"是否满足 §7 **无法由 §7 判定**——这本身也说明该系数需业主给定标定目标。代码位置：`config.py` L47–48、L52 |
| **A5** | `actors` 整组（`prey_speed` / `prey_size_min,max` / `predator_size` / `cruise` / `chase` / `detection_radius` / `release_radius` / `obstacle_radius_min,max` / `wander_turn_std` / `predator_turn_rate`，共 12 项） | **无** | `设计规范` 阅读问题 C11 L196：「**PredatorPolicy / PreyPolicy / ExpertPolicy 参数缺失**：巡游与追踪速度、避障半径，以及 ExpertPolicy 的 `w_p0 / k_H / w_d / w_o` 均**未落在 config**」；§9（L114–119）与 §10（L121–125）只有行为描述；§3（L25–31）只给对象数量；`参数总表.md` 无 `actors.*` 任何一行；**全仓 grep：`prey_speed` / `prey_size` / `predator_size` / `cruise` / `chase` / `detect` / `release` / `obstacle_radius` / `wander_turn_std` 在设计文档里一次都没有出现**（只在认领表出现） | §9 L115–119：巡游 → 发现合法目标后追踪 → 避障 → 丢失目标后恢复巡游；§10 L122–125：stochastic wander / obstacle avoidance / proximity avoidance——**全是定性，无一个数** | **无依据，需认领** | 12 项全为 AI/实现者自选。代码位置：`config.py` L56–70。⚠️ `configs/default_arena.yaml` L1–26 **完全没有 `actors:` 段**（只有 world / live_demo / sensing / energy / growth）。⚠️ 邻域两项同属本组且同样无依据：§12 L195「**'高价值 prey' 未定义**」（阅读问题 C10）、§10 的 proximity avoidance（`实现说明.md` M5 记未实现） |
| **A6** | 边界策略（clamp 到 `[0,W]×[0,H]`） | **无** | `设计规范` 阅读问题 B2 L181–182：「**边界行为未定义**：100×60 空间内个体到边界如何处理（**wrap / reflect / clamp / 惩罚**）未写，**config 无 boundary 项**」；`参数总表.md` 无 boundary 项；`configs/default_arena.yaml` 无 boundary 键。代码 `arena/entities.py` L24–25 `self.pos[0]=min(max(self.pos[0],0.0),world_w)` 等 | 阅读问题 L181 把 clamp 与 wrap / reflect / 惩罚**并列为四个候选**——即设计者本人不认为已选定 | **无依据，需认领** | clamp＝实现者自选。⚠️ 注意排除一条伪依据：`Danio_Arena实现说明.md §3.1 §2` 写「位置裁剪到 [0,W]×[0,H]」并挂在「规范 §2」名下，但 `设计规范 §2`（L6–23）**只给世界尺寸、Hz、步数，没有边界规则**；该句出处是 C 级实现文档，**不构成依据** |
| **A7** | 碰撞语义（仅鱼–障碍；每步 +1；无后果；可否穿模） | **部分**：只规定"要记录 collisions"；**后果无规定** | **有依据部分**：`设计规范 §13` L157–169 把 `collisions` 列入每鱼记录；`docs/验收清单.md` L27「event log」。**无依据部分**：`设计规范` 阅读问题 B3 L183：「**碰撞 (collision) 后果未定义**：§13 记录 collisions，但撞 obstacle / 边界 / 同类后发生什么（**穿模、反弹、扣 energy**）未写」；`参数总表.md` 无碰撞参数。代码 `arena/env.py` L183–191：`o.contains(fish.pos, 0.1)` → `collisions += 1` + 发事件 + `break`，**无位移、无能量后果** | 阅读问题 L183 把「穿模、反弹、扣 energy」并列为未定义候选 | **无依据，需认领**（§13 只要求"记录"，未规定"后果"） | 后果语义＝实现者自选；"每步 +1 / 每鱼每步最多一条"的计数口径也是自选。另注：`§13` 只列 `collisions` 一个字段，**未规定碰撞对象是否仅限障碍**——"仅鱼–障碍"亦属自选。⚠️ C 级旁证（供对照，非依据）：`实现说明.md §7 A7` + 附录记「`d414e05` 默认场景 5 seed×600 步 `arena.collision` 全为 0」，该事件当前近乎不触发 |
| **A8** | `arena.escape` 判定口径（换目标即算 vs 逃出 `release_radius` 才算） | **无** | `设计规范` 阅读问题 B6 L186–187：「**escape success 判定未定义**：§13 记录 escape successes，但'怎样算一次成功逃脱'（**脱离 radius、保持 N 步、存活至 episode 结束**）未定义。影响：直接决定 `evolution/遗传繁殖与演化模型.md` fitness 的 E 分量」；§13 L157–169 只列出 `escape successes` 字段名；`遗传繁殖与演化模型.md §6` L60 只写「E=escape success」，其阅读问题 #2（L104–106）另声明分量归一化方式未定。**⚠️ 关键**：工作区**未提交**的 `核心机制与数据流.md §5.1` L122 写「捕食者换掉已锁定目标，且旧目标仍存活」，但 **HEAD（`d414e05`）版该表标题是「草案，待冻结」**、`escape` 载荷写「威胁源、**反应时延**」（见 `git diff`）→ 该改写是为对齐代码而做的记录，**不是上游规定**（见 §0.4-1） | 阅读问题 L186 明列三个候选口径（脱离 radius / 保持 N 步 / 存活至 episode 末）——**未选任何一个** | **无依据，需认领**（且它是 fitness E 分量的直接上游） | 上游把三案并列；`release_radius` 这个具体半径本身也无依据（见 A5）。代码位置：`arena/env.py` L274–284（换目标且旧目标存活时发事件 + `escape_successes += 1`）+ `policies.py` L78–81（滞回）。⚠️ C 级旁证：`实现说明.md S17` 记死鱼不再计数（`99fda0d`）、附录记默认场景 `arena.escape` 5 seed×600 步**全为 0**——即认领前该口径对 E 分量几乎无影响，但"几乎无影响"不等于"已定义" |
| **A9** | 团灭提前结束（`step_idx>=600` **或** 全部鱼死） | **部分**：600 步有规定；"全鱼死即结束"无规定 | **600 步有依据**：`设计规范 §2` L19–23「标准 episode：30s = 600 steps」；`参数总表.md` L27–28 `episode_seconds 30` / `episode_steps 600`；`验收清单.md` L26「30s episode」→ 代码 `env.py` L339 与 `config.py` L16 一致。**提前结束无依据**：`设计规范` 阅读问题 B7 L188–189「**episode 结束与 survival 判定未定义**：30s/600 步结束后 survival 如何定义、与 energy=0 死亡如何交互、survival steps 如何归一化进 S 未写。影响：`遗传繁殖与演化模型.md` 的 S 分量与跨 episode 可比性」；§13 未给 survival 归一化 | 阅读问题 L188 明说"未定义"，并已指出影响 S 分量与跨 episode 可比性 | **无依据，需认领**（"全鱼死即结束"部分） | 600 步上限＝冻结量、有依据且一致；提前结束条件＝实现者自选。代码位置：`env.py` L338–351。⚠️ 工作区未提交的 §5.1 L126（「`step_idx >= 600` 或全部鱼死亡」）同 A8 的问题，不能作依据。⚠️ `实现说明.md S22` 另记「`bool(self.fish)` 使空种群不判团灭」也是自选（且其自陈无专项测试） |
| **A10** | 天敌/猎物转向量纲（`predator_turn_rate=5.0 rad/s`、`wander_turn_std` 单位） | **无**（但"鱼的 ω 是 rad/s"可从 §5 间接推出） | **无依据**：`设计规范` 阅读问题 C8 L192：「**Δt 与 ω 单位未定**：hz=20 可推 Δt=0.05s，但 **ω 是 rad/s 还是 rad/step 未写明**；公式含 Δt 但未给值」；`参数总表.md` 无 `predator_turn_rate` / `wander_turn_std`；§9/§10 无任何转向速率。**鱼的 ω 有间接依据**：§5 L52–53 `θ_{t+1}=θ_t+ω_t·Δt` 含 Δt ⇒ ω 量纲须为 rad/s 才自洽；代码 `env.py` L179 `fish.heading += _omega_eff(...)*dt` 与之一致 | 阅读问题 L192 明说"未写明"，并把它列入参数缺失（C11 L196 亦列"巡游与追踪速度"） | **无依据，需认领**（天敌/猎物的量纲）；鱼的 ω=rad/s 有 §5 的间接依据 | 天敌：`env.py` L288–290 用 `predator_turn_rate * dt`；猎物：`env.py` L321 `prey.heading += omega * dt`、`policies.py` L47 `rng.normal(0, turn_std)`。`5.0` 是 `99fda0d` 为"等价原硬编码 0.25 rad/step"反推的量（`实现说明.md S14`），**等价性有据、数值本身无据**；`wander_turn_std=0.8` 同理。⚠️ 另注 `policies.py` L51 的 `clip(omega,-3.0,3.0)` 与 `PreyPolicy.avoid_gain=2.5` 亦无依据（后者为死参数，`实现说明.md F2`） |
| **B1** | `release` 语义（"推进 N 步" vs "分批放鱼"） | **有规定，且代码与依据不符** | **依据**：`src/evogenesis/api/API与系统工程.md §4.3` L80：「POST `/v1/sessions/{session_id}/release` \| **释放鱼进入 Arena**」。**代码**：`api/session.py` L216–220 → `Session.advance(steps, use_expert)`（L45–59）只做 `k` 次 `arena.step()`，**不产生任何新实体**（鱼在 `reset()` 时已全部生成，`env.py` L70–79）。C 级旁证：`API接口.md` L120 自认「当前实现为'推进/播放'，与 `API与系统工程.md §4.3` 中'释放鱼进入 Arena'的措辞**不一致**，待认领」 | §4.3 用词是"**释放鱼进入** Arena"（实体进入），非"推进仿真" | **代码偏离依据，属缺陷** | 依据与实现是**互斥语义**（"产生新实体" vs "只推进时间"），不是措辞宽严问题。⚠️ 认领时须一并裁定的**依据源内部冲突**：`§4.1 R3`（L56，属"命名规范"冻结表）要求「**路径零动词**；动作以产物名词作子资源」，而 §4.3 自身就有 `/release` `/pause` `/reset` 三个动词路径 —— 两条规定在同一份文档内互相矛盾 |
| **B2** | `pause` toggle 兼 resume（无独立 resume 端点） | **无** | `API与系统工程.md` 阅读问题 #4 L141：「**暂停缺恢复端点（§4.3）**：`POST /v1/sessions/{session_id}/pause` 没有对应的 `resume / play` 端点」；§4.3 L81 只列 `pause`「暂停仿真」。代码 `api/session.py` L223–227：「`s.running = not s.running`」（toggle）；L49–50「`if not self.running: return`」 | §4.3 L81 的说明是单一动作"暂停仿真"；阅读问题 L141 承认**缺少**恢复端点 | **无依据，需认领** | resume 语义＝实现者自选（toggle）。**本项不判为"偏离"**：文档字面只说"暂停"，未禁止 toggle；但"第二次调用即恢复"这一语义在文档里**没有任何一句可引**。⚠️ 与 B1 同源问题：`/pause` 也是动词路径，与 `R3`（L56）冲突 |
| **B3** | `generation` / `environment` 是稳定 ID 还是标量 | **有规定（列为"稳定 ID"），且代码与依据不符** | **依据**：`API与系统工程.md §3` L39–46：「稳定 ID：`fish_id` / `genome_id` / **`generation_id`** / `experiment_id` / **`environment_id`**；前端不得使用数组下标当 identity」（同表在 `AGENTS.md`「项目目录结构」与 `API接口.md` L21 重复）。**代码**：`api/schemas.py` L34 `generation: int = 0`（计数器）、L36 `environment: str`（`Environment = Literal["food_rich","predator_rich","resource_scarce"]`，L11）；`api/session.py` L23 `ENV_KEYS`、L33 `self.generation = 0` | §3 里是 `generation_id` / `environment_id`（**ID 命名**），代码里是 `generation` / `environment`（**标量命名**）。§3 自身亦有缺口：阅读问题 #1（L138）「稳定 ID 的**生成规则与唯一性范围未定义**（§3）：…格式、派生方式（哈希 / 单调计数）、唯一性范围（会话内 / 全局）均未写」 | **代码偏离依据，属缺陷** | **两层问题须分开认领**：(a) 形态/命名（`*_id` vs 标量）与 §3 L39–46 不符 → 偏离；(b) §3 **自身未定义** ID 的生成规则与唯一性范围（阅读问题 #1 L138）→ 这一层是**无依据**。仅当业主认定"枚举字符串与整代次本身就是稳定标识"时，(a) 才可降级为"改文档"，但那是业主的判断，不由本表代作。代码位置补充：`session.py` L155 `session_id = f"session_{uuid.uuid4().hex[:12]}"`（`session_id` 有生成规则，但 §3 未列它、也未规定该格式） |
| **B4** | 未实现模块统一返回 501 + 归属说明 | **无** | `API与系统工程.md` **§4.1 R8**（L60）只给状态码桶：「`201` 建、`202` 异步受理、`204` 无体、`4xx` 客户端、`5xx` 服务端」—— 501 落在"5xx 服务端"里，但**"用 501 + 归属说明表达未实现"这一约定全文没有**；§4.3 端点表（L68–91）的 10 个未实现端点也没有状态列；阅读问题 1–10（L138–147）未涉及。代码：`api/stubs.py` L27–32 单一 `_NOT_IMPL = HTTPException(501, detail="Pipeline not implemented yet -- owned by 池伟豪 (genome/development/breeding/evolution).")`，10 个 stub **共用同一对象** | R8 只给状态码分类，**未给"未实现"的表达方式** | **无依据，需认领** | 501 + 归属说明＝实现者自选。唯一"有依据"的相邻部分是**错误体形状**：R10（L62）要求 RFC 7807 `type/title/status/detail/instance`，`api/app.py` L31–49 `_problem()` 已实现且一致 —— 但 R10 未要求 501 也纳入，也未要求"归属"这一字段。⚠️ 另一处依据冲突：R8 说 `202 异步受理`，而 `stubs.py` L55/L60 的 `status_code=202` 与"实际永远 501"不符（`API接口.md` L300 / L7 已记），须一并裁定 |
| **B5** | WS 词表（`sys.hello` / `sys.echo`，以及 `sys.error`） | **部分**：`sys.error` 有；`sys.hello` / `sys.echo` 无 | **有依据**：`API与系统工程.md §4.1 R11`（L63）：「`type` 用点分层（`arena.fish_state`、`brain.activation`、`job.progress`、**`sys.error`**）」→ `sys.error` 属 R11 明列。**无依据**：R11 其余三例是 `arena.fish_state` / `brain.activation` / `job.progress`，`sys.hello` / `sys.echo` **不在其中**；同文件阅读问题 #5（L142）：「**WS 消息类型词表不完整 + 语义缺失**（§4.1 R11 / §5）：R11 只举例四类，§5 还要传 energy / events / generation progress，但**未给完整 `type` 词表**；`seq` 的作用（排序 / 去重 / 断线补偿）…均未写」。代码 `api/ws.py` L30 / L41 / L43 | 阅读问题 L142 明说词表不完整、未给完整词表 | **无依据，需认领**（`sys.hello` / `sys.echo`）；`sys.error` 有依据且一致 | `sys.echo` 的定位是"契约演示"（`ws.py` L4–6 docstring）。⚠️ `seq` 的作用域（进程级 vs 连接级）也被阅读问题 L142 明列为未定义（`ws.py` L19–22 用模块级全局）。⚠️ §5（L93–103）列的 5 类业务推送（fish transforms / selected-fish neural activation / energy / events / generation progress）在 `ws.py` **一条都未实现** —— 这一层属"未做"而非"自定"，不在本项认领范围内，但直接卡 §5 与 `验收清单.md` L17「selected fish 实时 activation」 |
| **B6** | experiment 契约分裂（`schemas/experiment.schema.json` 的 `seed` + `*_config` vs `api/schemas.py` 的 `seeds:list[int]` + `name` + `generations`） | **无**（无设计文档规定 `POST /v1/experiments` 的请求体；两份已入库契约冲突且**无优先级规则**） | **无依据部分**：`API与系统工程.md §4.3` L85 只写「POST `/v1/experiments` \| 启动正式实验，`202` + `job_id`」，**无请求体字段**；全仓无任何设计文档规定 experiment 请求体。**冲突两侧**：`schemas/experiment.schema.json` L5–11 `required: [experiment_id, seed(integer), model_config, arena_config, evolution_config]`（另有 `git_commit` / `environment`），vs `api/schemas.py` L129–133 `ExperimentCreate{name, seeds:list[int], environment, generations}` —— **字段集不相交**。**有依据的旁证**：`schemas/` 是"跨语言数据契约"，`核心机制与数据流.md §7` L166 与 `API与系统工程.md §10` L132 均要求 schema/config 变更双方同步；且 `experiment/实验与评价体系.md §11`（L113–123）给出 Run 目录 `metadata.json / config_snapshot / metrics.csv / population.jsonl / seed.txt / git_commit.txt / plots/`，其阅读问题 #10（L138）指出「`schemas/experiment.schema.json` 仅覆盖 `experiment_id / seed / *_config / git_commit / environment`，**未覆盖本文 `results/runs/<id>/` 的…字段**」 | 阅读问题 #10 L138 只指出 schema 与 Run 目录未对齐，**未裁定**两者关系 | **无依据，需认领** | 两份文件都在 `schemas/` + `api/` 已入库，属"契约对契约冲突"。有依据的线索只到"schema 更像 **Run 记录**、api 模型更像 **创建请求**"这一步（旁证：schema 的 `seed` + `*_config` + `git_commit` 与 `实验与评价体系.md §11` 的 Run 目录字段同构），**但"二者是否同一对象、若是以谁为准"没有任何文档写过**。⚠️ 另一条**倾向性线索（非裁定）**：`实验与评价体系.md` 阅读问题 #1（L129）指出正式种子清单实际在 `configs/experiment_seeds.yaml`（`seeds: [1103, 2207, 3301]`、`minimum_formal_replicates: 3`），其"复数种子"形态与 api 的 `seeds:list[int]` 同向、与 schema 的 `seed:int` 反向 |
| **B7** | config 未接线（无 loader 读 `configs/default_arena.yaml`；`SessionCreate.arena_config_path` 被忽略；yaml 无 `actors` 段、无 `biomass_to_size_gain`；`live_demo` 键名与 dataclass 不一致） | **有规定（"必须由 config 读取"是明文要求），且代码与依据不符**；yaml 键名部分**无规定** | **依据（三项明文）**：① `docs/参数总表.json` L42（末行）：「**所有数值必须由 config 读取，报告记录实际版本**」；② `core/核心机制与数据流.md §7` L162：「`configs/*.yaml` \| 全部参数与种子的**唯一事实来源**…『所有数值必须由 config 读取』\| ✅ \| 冻结后不改」，同文件 §1 L3 更把「**`config`（配置加载）**、`logging`、`tracking`、`registry`、`io`」列为 `core/` 必须提供的模块；③ `API与系统工程.md §10` L132：「schema/config 变更必须双方同步」。**代码事实**：全仓 `yaml.` / `safe_load` / `load_config` 在 `src/ tests/ scripts/` 内**零命中**，`yaml` 一词唯一出处是 `api/schemas.py` L28–29 两个字符串默认值；`src/evogenesis/core/` **只有** `__init__.py`（0 字节）与 `seed.py`（251 字节），**没有 `config` 模块**（§1 L3 承诺的 5 个模块只落地 1 个）；`DanioArena.__init__`（`env.py` L41）`config or ArenaConfig()` → 硬编码默认值；`SessionCreate.arena_config_path`（`schemas.py` L28）在 `Session.__init__`（`session.py` L29–37）**完全未被读取**。**无依据部分（yaml 键名）**：`configs/default_arena.yaml` L7 用 `live_demo:`，dataclass 用 `PopulationConfig(n_fish…)`，`参数总表.md` L29–32 又用 `live_fish/live_prey/live_predators/live_obstacles` —— **三套命名并存，无任何文档裁定键名**；yaml L1–26 无 `actors:` 段、无 `biomass_to_size_gain` | `参数总表.md` L42 是明文契约；`核心机制与数据流.md §1` L3 是模块职责契约 | **代码偏离依据，属缺陷**（loader 缺失 / `core/config` 模块缺失 / `arena_config_path` 被静默忽略）；**yaml 键名无依据，需认领** | 本项是这次审计中**唯一同时命中"明文要求"与"实现完全缺失"**的一项：其后果"**改 config 不影响实验**"直接违反 `参数总表.md` 末行与 `核心机制与数据流.md §7`。⚠️ 附带的第二处缺陷：`arena/config.py` L1–6 docstring 自称「Defaults mirror `configs/default_arena.yaml` (**frozen values**, `docs/参数总表.json`)」，而 `参数总表.md` 只收录 Arena 的 10 个量（见 §0.4-2）→ **docstring 与 `参数总表.md` 的落差本身也是缺陷**（同一落差在 `EvoGenesis项目总纲.md` 阅读问题 #5 L149 已有先例记录） |
| **E1** | `environment` 三档（`food_rich` / `predator_rich` / `resource_scarce`）是否被规定过差异、差异应体现在哪些旋钮 | **三档名称有；差异方向只有定性一处（且在 archive）；旋钮映射无** | **名称有依据（5 处，均只列名字）**：`experiment/实验与评价体系.md §7` L70–74；`core/核心机制与数据流.md §6` L154「环境对照三组：Food Rich / Predator Rich / Resource Scarce」；`evolution/遗传繁殖与演化模型.md §9` L80–84；`EvoGenesis项目总纲.md` L82（生态层）；`docs/验收清单.md` L44「Environment selection」。**差异方向（B 级唯一出处）**：`archive/DNA2Brain_项目交接稿_v0.1.md §12` L596–610：「Food Rich：**食物多 / 捕食者少**；Predator Rich：**捕食者多 / 生存压力高**；Resource Scarce：**食物少 / 能量压力高**」——**archive 属被取代的 v0.1 交接稿，不在现行设计包内**。**旋钮映射：无**。**局部线索**：`arena/Danio_Arena设计规范.md §12` L149–155「resource-scarce 时 **hunger 提升 prey attraction**」，只覆盖 resource_scarce 一档的一环，且依赖 §11 L137–141 的 `w_p = w_p0 + k_H·H`（`w_p0 / k_H` **无值**，见 A5）。**代码**：`api/session.py` L23 `ENV_KEYS` 只有三键、L31 只存 `self.environment`，不改变任何参数 | `问题定义与研究假设.md` 建模假设 12（L80）「environment 在**单 episode 内固定，代际之间可切换**」是全仓对 environment 唯一的行为性规定 —— 它规定的是"何时可变"，**不是"变什么"**；`实验与评价体系.md` 阅读问题 #2–#9 无一条涉及环境差异 | **无依据，需认领**（旋钮映射）；三档名称有依据一致；差异方向仅有 B 级 archive | 认领时必须给出**每档对应哪些 config 键、方向是什么**。archive §12 **只给定性方向（食物/捕食者数量多少），未给任何倍数或数值**；`设计规范 §12` 也只对 resource_scarce 的一环给了方向。⚠️ C 级旁证：`API接口.md §7.2` L333 记「`environment`…**仅存储回显**…`food_rich` / `predator_rich` / `resource_scarce` **三档行为完全一致**（实测三档位的 `population` / `prey_remaining` 与初始世界完全相同）」 |
| **E2** | `schemas/trajectory.schema.json` 的字段表是否已定稿、示例实例是否已产出 | **有** | `core/核心机制与数据流.md §4.5` L107：「⚠️ 对应的 `schemas/trajectory.schema.json` **尚未冻结**——按 `api/API与系统工程.md §10`「schema/config 变更必须双方同步」，字段定稿前需池伟豪确认。**字段草案即 §4.2 表格**」；同文件 §10 待冻结项 #1（L201）：「`schemas/trajectory.schema.json` 本体待起草（§4.2 字段表草案已由 `c44c4ca` 产出示例实例 `schemas/examples/trajectory_example.jsonl`）\| 李辰钊起草，池伟豪确认 \| ExpertPolicy 接口定型（**已由 `954aca7` 满足**）」；§7 表 L166「`schemas/` \| …（genome / fish / experiment；**trajectory 待冻结**）」。**示例已产出**：`schemas/examples/trajectory_example.jsonl`（8 行，commit `c44c4ca`「examples: add schema-contract example instances」），键为 `step / fish_id / observation[12] / expert_action[2]`，与 §4.2 L81–87 字段表**逐项一致**；`schemas/examples/README.md` L17 记其状态「draft，待冻结」 | §4.5 L107「尚未冻结」+「字段草案即 §4.2 表格」；§10 #1「本体待起草、示例已产出」 | **有依据，代码一致**（无需认领） | "未定稿"是**已被明文规定**的状态（"尚未冻结"），不是疏漏：`schemas/trajectory.schema.json` **文件不存在**与 §4.5 的"尚未冻结"**一致**。唯一未闭环项也在文档里写清：§4.5「字段定稿前需池伟豪确认」、§10 #1 责任栏「李辰钊起草，池伟豪确认」→ **归口与前置条件均已确定**。字段表的 12 维语义另有 `schemas/examples/README.md` L34–43 的索引表与 `DanioNet设计规范.md §2`、`验收清单.md` L15 三方互证 |
| **E3** | `schemas/examples/event_log_example.jsonl` 与实现不一致（写成 `"too_far"` 等实现发不出的值）——上游是否规定过该文件的性质 | **有（该文件的"性质"与"处置"都已被规定）** | **性质有依据**：`schemas/examples/README.md` L18「`event_log_example.jsonl` \|（草案）`data-pipeline.md §5.1` 事件词表 \| **draft，待冻结**」，L1–5 状态行「示例数据（**draft**）…**冻结前不可被代码依赖**」；**处置有依据**：`core/核心机制与数据流.md §10` 待冻结项 **#4**（L204）「`schemas/examples/event_log_example.jsonl` **按 v1 词表重生成** \| 李辰钊 \| 词表确认」；`§7` L166「变更须双方同步」。**不一致是已登记的**：README L22–23 记生成基线「生成日期 2026-09-25、生成基线 commit `b0886f0`」（`docs: 数据全流程规范 v1.0 草案`），而实现落在 `954aca7` / `99fda0d`（更晚）⇒ 实例**先于实现**产生；C 级旁证 `实现说明.md §4.4` 逐行给出差异（`arena.spawn` 的 `entity` 应为 `entity_id`、坐标/尺寸已移出事件；`capture_attempt.result: "too_far"` → 实现只会发 `"too_small_to_eat"`；`escape.reaction_latency_steps` → 实现无此字段；缺 `collision` / `energy_depleted` / `fish_captured` / `episode_end` 四类） | 核心机制 §10 #4 是明文待办（含责任人与前置条件）；README 是明文 draft 声明 | **有依据（性质已被规定为"草案、待冻结、不得被代码依赖"；且"与实现不一致"正是该依据所预言的状态）**；不一致属**已登记欠账**，**非新缺陷、亦非未认领** | **本项不需要业主做设计选择**：处置已由文档给出（`实现说明.md §4.4` 列为"重生成 v1 词表"或"降级为形状示意 + 免责标注"二选一），责任人（李辰钊）与前置条件（词表确认）均已写明。⚠️ 唯一真实缺陷是**路径过期**：`schemas/examples/README.md` L17–18 仍写 `data-pipeline.md §4.2 / §5.1`，该文档已更名为 `src/evogenesis/core/核心机制与数据流.md`（文档搬迁遗留，非数值决策） |

---

## 3. 三类以外：5 个必须提醒业主的"依据侧"问题

以下不是 20 项中的任何一项，但会**影响认领本身的效力**，故单列。

| # | 问题 | 证据 |
|---|---|---|
| **G1** | **工作区版 `核心机制与数据流.md §5.1` 是被改写成跟随代码的，不能当依据** | `git diff` 显示 HEAD 版标题为「草案，待冻结」、6 行、事件名无 `arena.` 前缀、`escape` 载荷含"反应时延"；工作区版改为「v1 定稿，待池伟豪确认」的 8 行表。改写文本与 C 级 `实现说明.md §4.2` 同源。**A8 / A9 / A2 若引此表作依据，等于引实现** |
| **G2** | **`docs/参数总表.json` 与 `arena/config.py` docstring 的 "frozen values" 落差** | `config.py` L3 自称 mirror frozen values；`参数总表.md` 实际只收录 Arena 10 个量。凡写"参数总表无此行"者，该值即**非冻结量**。同类落差已有先例（`EvoGenesis项目总纲.md` 阅读问题 #5 L149） |
| **G3** | **`core/` 缺少文档承诺的 `config` 模块** | `核心机制与数据流.md §1` L3 承诺 `core/` 提供 `config/logging/tracking/registry/io`；实际 `src/evogenesis/core/` 只有 `__init__.py`（0 字节）+ `seed.py`（251 字节）。这是 B7 的"职责级"缺陷，不只是"忘了调 loader" |
| **G4** | **C 级文件不得当依据** | `Danio_Arena实现说明.md`（**未入库 `??`**）L6/L15 与 `API接口.md`（含未提交改动）L6–8 均自我声明"描述实现，不等于设计已如此规定"。它们**只能证明代码事实**；`实现说明.md §7` 与 `API接口.md §11` 也确实把 A/B 各项标为 `草案待确认` |
| **G5** | **依据源内部自相矛盾一处（须一并裁定）** | `API与系统工程.md` 的 **R3**（§4.1 L56，「路径零动词」）与 **§4.3 端点表**（L73/L80/L81 的 `/reset` `/release` `/pause`）互相矛盾。B1、B2 的裁定时会撞上这一条 |

---

## 4. 无依据项速览（15 项，按"是否含部分有依据"分组）

**A. 完全无依据（5 项）——整项没有任何子项可引上游**

| 项 | 事项摘要 |
|---|---|
| A5 | `actors` 整组 12 项（`prey_speed` / `prey_size_min,max` / `predator_size` / `cruise` / `chase` / `detection_radius` / `release_radius` / `obstacle_radius_min,max` / `wander_turn_std` / `predator_turn_rate`） |
| A6 | 边界策略 clamp 到 `[0,W]×[0,H]` |
| A8 | `arena.escape` 判定口径 |
| B2 | `pause` toggle 兼 resume |
| B4 | 未实现模块统一 501 + 归属说明 |

**B. 含部分有依据（10 项）——"框架/名称/顺序"有据，"系数/映射/公式"无据**

| 项 | 有依据的子项 | 无依据的子项 |
|---|---|---|
| A1 | 12 维**顺序**（`DanioNet设计规范.md §2` + `验收清单.md` L15） | 五个归一化公式 |
| A2 | **κ=1.25**（§8 L106–110 + `参数总表.md` L40，且代码一致） | `capture_radius=1.2`、双向捕食 |
| A3 | §6 **能量公式**（代码一致） | 四个系数 |
| A4 | §7 **生长机制框架**（代码一致） | 三个系数；且 `biomass` 只写不读＝**偏离** |
| A7 | §13 **要求记录 collisions** | 碰撞**后果**、计数口径、"仅鱼–障碍" |
| A9 | §2 **30s / 600 步**（代码一致） | "全鱼死即结束" |
| A10 | §5 含 Δt ⇒ **鱼的 ω=rad/s**（代码一致） | 天敌/猎物转向量纲与数值 |
| B5 | `sys.error`（R11 L63，代码一致） | `sys.hello` / `sys.echo`；`seq` 作用域 |
| B6 | `schemas/` 的"跨语言契约"地位（`核心机制与数据流.md §7` L166） | 请求体字段；两契约的优先级 |
| E1 | 三档**名称**（5 处文档） | **旋钮映射**；差异方向仅有 B 级 archive |

---

## 5. 本表实际读过的文件清单

标注：**通读** = 全文读；**定点读** = 只读相关节/行 + 全仓 grep 命中行。所有行数为 `wc -l` 结果。

### 5.1 A 级依据（上游设计文档 / 已入库契约）

| 文件 | 行数 | 读法 | 用于 |
|---|---:|---|---|
| `src/evogenesis/arena/Danio_Arena设计规范.md` | 196 | 通读 | A1–A10 全部；§2/§4/§5/§6/§7/§8/§9/§10/§11/§12/§13 + 阅读问题 A1/B2/B3/B4/B5/B6/B7/C8/C9/C10/C11 |
| `src/evogenesis/api/API与系统工程.md` | 147 | 通读 | B1–B7 全部；§3/§4.1 R1–R11/§4.2/§4.3/§5/§6/§7/§10 + 阅读问题 #2/#4/#5/#8 |
| `docs/参数总表.json` | 42 | 通读 | 冻结量判定（A2/A3/A4/A5/A9/B7）；末行 L42 |
| `docs/验收清单.md` | 53 | 通读 | A1（L15 顺序冻结）、A7（L27 event log）、A9（L26）、B5（L17）、E1（L44） |
| `src/evogenesis/experiment/实验与评价体系.md` | 138 | 通读 | E1（§7 L70–74）、B6（§11 L113–123 + 阅读问题 #1/#10） |
| `src/evogenesis/connectome/DanioNet设计规范.md` | 122 | 通读 | A1（§2 L13–25 + 阅读问题 #1 L115） |
| `src/evogenesis/core/核心机制与数据流.md` | 204 | 通读 + `git diff` 对照 HEAD 版 | §1 L3（B7）、§4.2/§4.5（E2）、§5.1（A8/A9，**须区分版本**）、§7 L162/L166（B6/B7/E2）、§10 #1/#2/#4（E2/E3）、§5.1 改动（G1） |
| `src/evogenesis/development/RGCD数学模型.md` | 267 | 定点读 | 确认其中**无 Arena 参数**（A1–A10 无依据的排除性核对） |
| `src/evogenesis/evolution/遗传繁殖与演化模型.md` | 119 | 通读 | A8/A9（§6 Fitness L49–60 + 阅读问题 #2）、E1（§9 L80–84） |
| `src/evogenesis/EvoGenesis项目总纲.md` | 149 | 定点读 | E1（L82 生态层）、§0.4-2 与 G2 的先例（阅读问题 #5 L149） |
| `src/evogenesis/问题定义与研究假设.md` | 90 | 通读 | E1（建模假设 12，L80） |
| `docs/赛题补充说明.md` | 20 | 通读 | 赛题侧：确认**无任何 Arena/API 数值规定**；唯一相关为"核心设计与创造应由参赛者完成"（二·一） |
| `configs/default_arena.yaml` | 25 | 通读 | A2/A3/A4/A5/B7（`live_demo` L7、无 `actors`） |
| `configs/default_model.yaml` | 30 | 通读 | 排除性核对（不含 Arena 参数） |
| `configs/experiment_seeds.yaml` | 3 | 通读 | B6（`seeds: [1103, 2207, 3301]`） |
| `configs/demo_seed.yaml` | 3 | 通读 | 排除性核对 |
| `schemas/experiment.schema.json` | 34 | 通读 | B6 |
| `schemas/examples/README.md` | 63 | 通读 | E2（L17）、E3（L18、L22–23）、A1（L34–43 12 维语义表） |
| `schemas/examples/event_log_example.jsonl` | 4 | 通读 | E3（逐行核对 provider 值） |
| `schemas/examples/trajectory_example.jsonl` | 8 | 通读 | E2（键与 §4.2 逐项比对） |

### 5.2 B 级（旁证）

| 文件 | 行数 | 读法 | 用于 |
|---|---:|---|---|
| `archive/DNA2Brain_项目交接稿_v0.1.md` | 1196 | 定点读（§12 L590–625 + 全仓 grep 参数名，零命中） | E1 的差异方向（**B 级**） |

### 5.3 C 级（实现侧文档，**只能证明代码事实**）

| 文件 | 行数 | 读法 | 用于 |
|---|---:|---|---|
| `src/evogenesis/arena/Danio_Arena实现说明.md`（**未入库 `??`**） | 377 | 通读 | §2.1/§2.2/§2.3（A2–A5/B7 的代码事实）、§3.2 S1–S23、§4.2/§4.4（E3）、§5 D1–D7、§6、§7 A1–A10、§8 M1–M14、附录实测 |
| `src/evogenesis/api/API接口.md`（含未提交改动） | 467 | 通读 | §1.6/§1.7（B1/B2 的代码事实）、§7.2（B7/E1）、§8（B5）、§11 B1–B7/L1–L10 |
| `research/notes/arena-api-决策认领表.md` | 115 | 通读 | 项清单与项号对齐（**案卷本身，非依据**） |

### 5.4 代码（被审计对象）

| 文件 | 行数 | 文件 | 行数 |
|---|---:|---|---:|
| `src/evogenesis/arena/config.py` | 80 | `src/evogenesis/api/schemas.py` | 171 |
| `src/evogenesis/arena/env.py` | 372 | `src/evogenesis/api/session.py` | 245 |
| `src/evogenesis/arena/sensing.py` | 165 | `src/evogenesis/api/stubs.py` | 82 |
| `src/evogenesis/arena/entities.py` | 69 | `src/evogenesis/api/ws.py` | 53 |
| `src/evogenesis/arena/policies.py` | 95 | `src/evogenesis/api/app.py` | 66 |
| `src/evogenesis/arena/__init__.py` | 0 | `src/evogenesis/core/__init__.py` / `seed.py` | 0 / 8 |

### 5.5 辅助（测试与协作文档）

| 文件 | 行数 | 读法 | 用于 |
|---|---:|---|---|
| `tests/test_arena.py` | 212 | 定点读（`KNOWN_EVENTS` L10–19 + 守护测试清单） | E3/G1（词表权威性） |
| `tests/test_api_contract.py` | 106 | grep 命中 | B1/B2/B7 测试覆盖旁证 |
| `docs/项目状态.md` | 33 | 通读 | 排除性核对（"已冻结"清单**不含**任何 Arena 数值）；该文件已于 `5644892` 删除 |
| `docs/开发排期与人员分工.md` | 73 | 定点读（head 40） | 归属确认（Arena/API = 李辰钊；genome/evolution = 池伟豪） |
| `docs/directory-structure.md` | 130 | grep 命中 | B3（L126 重复的稳定 ID 列表）；该文件已于 `ae9c0c3` 并入 `AGENTS.md`「项目目录结构」 |

**未读全文而仅在全仓 grep 中命中的文件**（未作为依据引用）：`docs/AI工作流.md`、`docs/局限与未来路线.md`、`docs/路演与答辩.md`、`frontend/README.md`、`frontend/src/api/arena.ts`、`frontend/交互与可视化.md`、`AGENTS.md`。这些均只在 grep 关键词时命中，**本表未据其下任何结论**。

---

## 6. 自检

### 6.1 项数与覆盖率

| 组 | 项号 | 项数 |
|---|---|---:|
| arena | A1、A2、A3、A4、A5、A6、A7、A8、A9、A10 | **10** |
| api | B1、B2、B3、B4、B5、B6、B7 | **7** |
| 业主另问 | E1、E2、E3 | **3** |
| **合计** | — | **20** |

**20 项逐项有结论；主表内**无**"待查"、"大致上"、"通常"字样。**

### 6.2 三类统计（含第 4 类"已登记待办"）

| 标签 | 项数 | 项号 |
|---|---:|---|
| 有依据，代码一致 | **1** | E2 |
| 有依据，不一致已被登记为待办（非无依据、非新缺陷） | **1** | E3 |
| **代码偏离依据，属缺陷** | **3** | B1、B3、B7 |
| **无依据，需认领** | **15** | A1–A10、B2、B4、B5、B6、E1 |
| 合计 | **20** | — |

其中"无依据"15 项再分：**完全无依据 5 项**（A5、A6、A8、B2、B4）；**含部分有依据 10 项**（A1、A2、A3、A4、A7、A9、A10、B5、B6、E1）。

另有 **2 个"代码偏离依据"的子项**落在主标签非"偏离"的行内，已在该行"细分"栏标注：
- **A4**：`biomass` 只写不读 → 偏离 `设计规范 §7` L84 的"biomass **使** size 增长"；
- **B5**：`ws.py` 5 类业务推送全缺 → 非"自定"而是"未做"，已在行内标注但不计入本项认领。

### 6.3 最严重的 3 个「代码偏离依据」项（按严重度）

1. **B7 config 未接线** —— 唯一同时命中**明文契约**（`docs/参数总表.json` L42「所有数值必须由 config 读取」+ `核心机制与数据流.md §7` L162「唯一事实来源」+ `§1` L3「`core/` 提供 `config`（配置加载）」）与**实现完全缺失**（全仓零 loader；`core/` 无 `config` 模块；`arena_config_path` 被静默忽略）的一项。后果是"**改 config 不影响实验**"，直接使 `参数总表.md` 末行失效。
2. **B1 `release` 语义** —— 上游写"**释放鱼进入 Arena**"（实体进入），实现是"推进 N 步"（不产生实体），二者**互斥**。且认领时会撞上依据源内部冲突（§4.1 R3「路径零动词」vs §4.3 的 `/release` `/pause` `/reset`）。
3. **B3 `generation`/`environment` 形态** —— `API与系统工程.md §3` 明文列为 `generation_id` / `environment_id` 稳定 ID，代码是 `int` 计数器与枚举字符串。评判决时需要业主区分两件事：形态不符（偏离）与 §3 自身未定义 ID 生成规则（无依据，阅读问题 #1 L138）。

### 6.4 业主应先看的 4 项（不按严重度，按"卡住下游"）

| 顺序 | 项 | 为什么先看 |
|---|---|---|
| 1 | **B7** | 它使"参数总表 = 冻结量"这一整套机制失效；不修，其余任何"写进参数总表"的认领结论都无法被实验读取 |
| 2 | **A8** | escape 口径是 `遗传繁殖与演化模型.md §6` fitness **E 分量**的直接上游；不裁定，E 分量无定义（同一链条上 A9 决定 S 分量、A3/A4 决定 Q 分量） |
| 3 | **B1** | 决定 demo 叙事与 §4.3 端点表能否自洽；且必须与 G5（R3 冲突）一并裁定 |
| 4 | **E1** | 三档环境是 `验收清单.md` L44「Environment selection」与 `实验与评价体系.md §7` 的承载项，而**旋钮映射完全没有依据**（仅有 archive 的定性方向）；不认领则该验收项无法通过 |

### 6.5 硬约束遵守情况

| 约束 | 状态 |
|---|---|
| 只新建 `research/notes/arena-api-决策依据表.md` 一个文件 | ✅ 本表是该文件 |
| 未修改任何既有文件（`.md` / `.py` / `.yaml` / `.json` / `.jsonl`） | ✅ 全程只用 Read / Grep / `git diff` / `git log` / `wc` / `grep`，未用 Edit / Write 于任何既有文件 |
| 未提交、未 push | ✅ 只读审计 + 一次 Write |
| 引用文档用当前真实路径 | ✅ 全文路径为 `src/evogenesis/...` / `docs/...` / `configs/...` / `schemas/...`，未使用已废弃的 `docs/design/...` 形态；并已标注一处**仍在使用过期路径**的上游文件（E3 行：`schemas/examples/README.md` L17–18 的 `data-pipeline.md`） |
| 不替业主提建议 | ✅ 未给任何"建议改成 X"。凡 `实现说明.md` / `API接口.md` 里带倾向的措辞（如"推荐"），本表只作为"该文件怎么说"引述并标明其为 C 级，未据以作结论 |
| 区分"框架有依据、系数无依据" | ✅ A3、A4 明确如此标注；另有 10 项按子项拆分标注 |
| 工作区未提交改动须与 HEAD 区分 | ✅ 见 §0.4-1 与 G1；A8、A9、E3 行内均标版本 |
