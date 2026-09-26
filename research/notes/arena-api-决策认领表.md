# arena / api 决策认领表

> 收件人：李辰钊
> 目的：`src/evogenesis/arena/` 与 `src/evogenesis/api/` 的代码**先于文档**落地。审计发现其中大量数值与语义由代码生成工具（提交信息带 `co-author Claude Code`）自行填入，从未进入任何设计文档。本表把这些"未认领的决定"逐条列出，请回答 **接受 / 改成 X / 说明原意**。答案确认后由我们写进 `arena/Danio_Arena设计规范.md`、`api/API与系统工程.md`、`docs/参数总表.json`，作为契约冻结。
>
> 基准：以 `arena/Danio_Arena设计规范.md`、`api/API与系统工程.md`、`docs/参数总表.json` 对照代码。凡"文档没写、代码自定"的，一律不默认正确。

## 怎么填
每条在 `[ ] 接受` / `[ ] 改：____` / `[ ] 说明：____` 上打勾或直接写；不确定写"待定"。

---

## A. 必须认领的"AI 填空"（arena，文档没写、代码自定）

### A1 12 维感官编码的归一化公式 `src/evogenesis/arena/sensing.py`
- 现状：强度 `1 - d/radius`（线性衰减）；`prey_relative_size = min(prey.size/fish.size, 1)`；`predator_relative_size = min(pred.size/fish.size/2.5, 1)`；`looming = clip(10*(pred_rel - prev), 0, 1)`；左右分侧按 `sin(bearing)` 符号。
- 文档：`connectome/DanioNet设计规范.md §2` 只给了 12 个维度名，公式全部未定义。
- 影响：这是 DanioNet 的输入分布，直接决定网络要学什么（属池伟豪 lane）。
- [ ] 接受  [ ] 改：____  [ ] 说明：____

### A2 捕食几何 `arena/env.py`
- 现状：`capture_radius = 1.2`（纯距离判定，无朝向/口部角度）；`capture_size_ratio κ = 1.25`。
- 文档：`arena/Danio_Arena设计规范.md §8` 只写 `d < r_capture`，未给半径值与角度口径。
- [ ] 接受  [ ] 改：____  [ ] 说明：____

### A3 能量四系数 `arena/config.py`
- 现状：`e_max=1.0`、`base_cost_per_step=0.0008`、`movement_cost_scale=0.0015`、`food_reward=0.12`。
- 文档：`arena/Danio_Arena设计规范.md §6` 给了公式，但系数不在 `docs/参数总表.json`。
- [ ] 接受  [ ] 改：____  [ ] 说明：____

### A4 生长 `arena/config.py`
- 现状：`initial_size=1.0`、`max_size=2.5`、`biomass_to_size_gain=0.02`；实现为 `size += gain*prey.size`，`biomass` 是只写不读的镜像量。
- 文档：`arena/Danio_Arena设计规范.md §7` 只说"缓慢增长并设上限"；`docs/参数总表.json` 无 `biomass_to_size_gain`。实测单局 size 几乎不动（1.00→1.01）。
- [ ] 接受  [ ] 改：____  [ ] 说明：____

### A5 actors 整组 `arena/config.py`
- 现状：`prey_speed=0.35`、`prey_size 0.30–0.60`、`predator_size=2.0`、`cruise=0.40`、`chase=0.65`、`detect=15`、`release=22`、`obstacle_radius 1.5–3.5`、`wander_turn_std=0.8`。
- 文档：`arena/Danio_Arena设计规范.md` 说最终值来自 play-test；现全为代码自定，`configs/default_arena.yaml` 里根本没有 `actors` 段。
- [ ] 接受  [ ] 改：____  [ ] 说明：____

### A6 边界策略 `arena/entities.py:24-25`
- 现状：clamp 到 `[0,W]×[0,H]`（贴墙卡住、持续耗能）。
- 文档：`arena/Danio_Arena设计规范.md` 阅读问题说"边界行为未定义"。
- [ ] 接受 clamp  [ ] 改：反弹 / 出界即死 / 其他：____

### A7 碰撞语义 `arena/env.py:167-173`
- 现状：仅"鱼–障碍"，只要重叠就**每步 +1**；无位移、无能量后果；鱼可穿模。prey/predator 有转向避障，鱼没有（鱼由网络驱动）。
- 文档：`arena/Danio_Arena设计规范.md` 阅读问题说"碰撞后果未定义"。实测（当前默认场景，5 seed × 600 步）均为 **0 次**（见 `Danio_Arena实现说明.md` 附录；旧基线"84 次"已失效，因障碍生成方式变更）。
- [ ] 接受  [ ] 改：____  [ ] 说明：____

### A8 escape 判定 `arena/env.py:233-239`
- 现状：捕食者**目标切换**即算被弃目标"逃脱成功"。死亡导致的切换已不再计入（本轮修复，见 C 表）。
- 你的本意：[ ] 切换目标即算逃脱（现行）  [ ] 逃出 `release_radius` 才算  [ ] 其他：____

### A9 团灭提前结束 `arena/env.py`
- 现状：`step_idx>=600` **或** 全部鱼死 → episode 结束。
- 文档：`arena/Danio_Arena设计规范.md` 未定义；提前结束影响跨 episode 可比性（fitness 的 survival 项）。
- [ ] 有意（保留）  [ ] 应固定跑满 600 步  [ ] 其他：____

### A10 天敌/猎物转向量纲 `arena/env.py:243,265`、`config.py`
- 现状：原代码天敌 `heading += clip(diff,-0.25,+0.25)`（rad/step），鱼 `omega*dt`（rad/s），量纲不统一。本轮已把天敌改为 `predator_turn_rate=5.0 rad/s`（等价原值）并修正猎物注释。
- 确认该口径：[ ] 接受 5.0 rad/s  [ ] 改：____

---

## B. 必须定义的语义（api / api/API与系统工程.md）

### B1 `release` 到底是什么 `api/session.py`
- 现状：调用即"驱动仿真前进 N 步"（`steps` 参数），不产生新实体；鱼在会话创建时已全部生成。
- 文档：`api/API与系统工程.md §4.3` 写"释放鱼进入 Arena"。
- 你的本意：[ ] 就是"推进/播放"（改文档措辞）  [ ] 真的分批释放鱼（改代码）  [ ] 其他：____

### B2 暂停/恢复 `api/session.py`
- 现状：`pause` 翻转 `running`（toggle 兼作 resume）；本轮已让它真的阻塞 `release`。`api/API与系统工程.md` 无 resume 端点。
- [ ] toggle 即可（文档补说明）  [ ] 新增 `POST .../resume`  [ ] 其他：____

### B3 `generation` / `environment` 是 id 还是标量
- 现状：`api/API与系统工程.md §3` 把它们列为"稳定 ID"，代码里是 `int` / 字符串枚举。
- [ ] 改成 `generation_id`/`environment_id`  [ ] 承认是标量，改文档  [ ] 其他：____

### B4 未实现模块的统一约定 `api/stubs.py`
- 现状：501 + "owned by 池伟豪 ..."。
- [ ] 正式写进 `api/API与系统工程.md`（501 + 归属说明）  [ ] 改成别的：____

### B5 WS 词表 `api/ws.py`
- 现状：代码新增 `sys.hello` / `sys.echo`（后者仅为契约演示）。
- [ ] 正式纳入词表（`api/API与系统工程.md` R11）  [ ] `sys.echo` 只作临时、后续删  [ ] 其他：____

### B6 experiment 契约分裂 `schemas/experiment.schema.json` vs `api/schemas.py`
- 现状：JSON Schema 要求 `seed:int` + `*_config` 路径；api 模型是 `seeds:list[int]` + `name/generations`，两套字段不相交。
- 以哪个为准？[ ] 以 API（`seeds`）为准、改 schema  [ ] 以 schema（`seed`）为准、改 api  [ ] 其他：____

### B7 config 未接线 `arena/config.py`、`api/session.py`、`configs/default_arena.yaml`
- 现状：没有任何 loader 读 yaml；`SessionCreate.arena_config_path` 被静默忽略；yaml 键名（`live_demo`、缺 `actors`/`biomass_to_size_gain`）与 dataclass 也不匹配。等于"改 config 不影响实验"。
- [ ] 由我们实现 loader 并把 yaml 对齐 dataclass（推荐）  [ ] 你来定 yaml 形态  [ ] 其他：____

---

## C. 已确证 bug —— 本轮已修（无需你认领，仅供知会）

| 现象 | 位置 | 状态 |
|---|---|---|
| 同 seed 二次 `reset()` 布局漂移（摧毁可复现） | `arena/env.py` | 已修 |
| episode 结束后仍可推进（600→602）、`episode_end` 重复 | `arena/env.py`、`api/session.py` | 已修 |
| 死鱼被记 `escape_successes` | `arena/env.py` | 已修 |
| `predator_encounters` 恒 0 | `arena/entities.py`、`arena/env.py` | 已修（口径待 A8 确认） |
| 错误体非 RFC7807（R10），测试把违规锁死 | `api/app.py`、`tests/test_api_contract.py` | 已修 |
| `pause` 不生效（`running` 从不被读） | `api/session.py` | 已修 |
| looming 差分口径错配（最近 vs 最大） | `arena/sensing.py`、`arena/env.py` | 已修 |
| 空 fish 时 `all([])==True` 立即 done | `arena/env.py` | 已修 |
| `viable=f.alive`（语义错位） | `api/session.py` | 已修 |
| 天敌转向量纲混用 | `arena/env.py`、`arena/config.py` | 已修 |

> 说明：以上改动只修"确证缺陷"，未替你做任何设计选择；A/B 两节的答案才是文档冻结的依据。
