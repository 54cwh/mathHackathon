# 最低测试计划

1. Mendelian segregation statistical test
2. mutation determinism
3. crossover determinism under seed
4. GRN shape/range
5. neuron count ≤48
6. all six fates in viable fish
7. no self-loop
8. density sanity
9. Dale sign
10. sensory→motor reachability
11. zero-input dynamical stability
12. population size preserved
13. same config + seed → same results
14. mutation API changes downstream development

---

## 实现落地补充（李辰钊，2026-09-26）

> 本节是对上面「最低测试计划」14 项的**补充**，不是替换：14 项的编号、措辞与地位**原样保留**，仍是最低门槛。下表两套测试已随实现落地（Arena 侧 `tests/test_arena.py`、API / WS 侧 `tests/test_api_contract.py`），作用是把 14 项里的机制性要求、以及冻结的 HTTP / WS 契约，钉成可执行的断言。

### Arena 实现（`tests/test_arena.py`，15 项）

| # | 测试 | 守护的性质 |
|---|---|---|
| 1 | `test_reset_deterministic_same_seed` | 同一 seed 下两次 `reset()` 后，每条鱼的位置/朝向与每个猎物的位置/size 完全一致 —— 钉住「种子 → 初始世界」逐位可复现（对应最低计划第 13 项）。 |
| 2 | `test_reset_different_seed_differs` | seed 7 与 8 下 `fish_00` 的初始位置必须不同 —— 防止种子被忽略、所有 run 静默退化成同一个世界。 |
| 3 | `test_obs_shape_and_ranges` | 每条鱼的观测向量是 12 维、全为有限值且已归一化到 `[0,1]` —— 钉住策略网络输入的形状与数值域。 |
| 4 | `test_population_counts_match_frozen_defaults` | `reset()` 后恰为 12 鱼 / 24 猎物 / 3 捕食者 / 6 障碍，与 `configs/default_arena.yaml` 的 `live_demo` 冻结值一致（对应最低计划第 12 项「population size preserved」）。 |
| 5 | `test_capture_grants_food_reward` | 把猎物放进捕获半径 1.2 内必须发出 `arena.prey_captured`、猎物置亡、`captures` 加一，且能量精确由 0.5 变为 0.6192（`-0.0008` 基础消耗 `+0.12` 食物奖励）—— 一次锁死捕获判定与能量账本的具体数值。 |
| 6 | `test_too_small_to_eat_attempt_logged` | 猎物 size 1.5（`1.0/1.5 = 0.667 < κ = 1.25`）时不可食：仍记录 `arena.capture_attempt` 且 `payload["result"] == "too_small_to_eat"`、猎物存活 —— 保证「想吃但吃不下」可观测，且不改写世界状态。 |
| 7 | `test_starvation_death_event` | 能量降到 0.0005（低于每步基础消耗）时鱼在本步死亡并发出带 `fish_id` 的 `arena.energy_depleted` —— 钉住饿死判定与死亡事件。 |
| 8 | `test_episode_terminates_at_max_steps` | 空动作连跑 600 步后 `done=True`，且 `arena.episode_end` 的 `payload["steps"] == 600` —— 与 `episode_steps: 600` 冻结值一致，保证回合必然终止、不会无限跑。 |
| 9 | `test_turn_inertia_reduces_bigger_fish_turning` | 同一转舵指令下 `_omega_eff(size=2.0) < _omega_eff(size=1.0)` —— 把「体型越大转向越钝」的惯量缩放（`turn_inertia_scale`）固化为断言，而非仅写在设计文档里。 |
| 10 | `test_all_events_in_known_vocabulary` | 跑 120 步后所有事件的 `type` 都以 `arena.` 开头且落在 `KNOWN_EVENTS` 白名单内 —— 防止拼错或新造事件名破坏前后端事件契约。 |
| 11 | `test_per_fish_log_completeness` | `per_fish_log()` 的每条鱼都含 10 个必需字段，且 `energy_trajectory` 长度等于 `survival_steps` —— 保证每鱼日志完整、可对齐，能支撑基因型 × 表现型的统计关联。 |
| 12 | `test_reset_idempotent_on_same_instance` | 同一实例连续两次 `reset()` 后，每条鱼的位置与每个障碍的位置**及半径**完全一致 —— 钉住「同 seed 反复 reset 得到同一初始局面」，这是复现性判据成立的前提（障碍就地逐个生成、`reset` 先清空：同 seed 反复 `reset` 布局不漂移）。 |
| 13 | `test_step_after_episode_end_is_inert` | 跑满 600 步后再 `step()`：仍 `done`、`step_idx` 保持 600、`arena.episode_end` 计数不增 —— 保证 episode 结束后不再推进、结束事件不重复发。 |
| 14 | `test_dead_fish_not_credited_escape` | 把捕食者目标指向一条已死鱼后推进：该鱼 `escape_successes` 保持 0 且本步无 `arena.escape` —— 钉住「逃脱只记活鱼」，避免被吃掉的鱼反过来抬高逃脱指标。 |
| 15 | `test_predator_encounter_recorded_on_acquisition` | 捕食者从「无目标」切换到目标鱼的下一步，该鱼 `predator_encounters >= 1` —— 让该字段可观测，并把口径钉在「目标获取」而非「近距接触」。 |

### API / WS 契约（`tests/test_api_contract.py`，9 项）

| # | 测试 | 守护的性质 |
|---|---|---|
| 1 | `test_health` | `GET /v1/health` 返回 200 且 body 恰为 `{"status":"ok"}` —— 最小存活探针，也是前端与 CI 在做任何会话操作前的连通性前置。 |
| 2 | `test_create_session_and_snapshot` | `POST /v1/sessions`（`master_seed=250927`、`environment=food_rich`）返回 201 且 `fish_alive == 12`；紧随其后的 snapshot `step == 0` 且 fish/prey/predators/obstacles 恰为 12/24/3/6 —— 一次钉住会话创建与初始世界快照两端。 |
| 3 | `test_release_advances_arena` | `release(steps=30)` 后 snapshot 的 `step` 恰为 30 —— 证明步进严格按请求步数推进，既不空转也不超额。 |
| 4 | `test_fish_card_and_leaderboard` | 推进 10 步后 `GET /v1/sessions/{id}/fish/fish_00` 返回 `fish_id == "fish_00"`，且 `.../leaderboard` 的 `entries` 恰为 12 条 —— 钉住单鱼详情卡与排行榜这两个只读视图的可用性与规模。 |
| 5 | `test_reset_session` | 推进到 `step == 50` 后 `POST /v1/sessions/{id}/reset` 返回 200，且 snapshot 的 `step` 归 0 —— 保证会话可**原地**重置，不必删除重建（前端另走 delete+create，此端点仍需可用）。 |
| 6 | `test_missing_session_404` | 不存在的 session id 返回 404，且 body 为 **RFC 7807 问题详情**（`type` / `title` / `status` / `detail` / `instance` 五字段齐备，`instance` 回显请求路径）—— 钉住错误契约，避免前端拿到裸 500 或非结构化 body 而无法提示。 |
| 7 | `test_stubs_return_501` | `POST /v1/developments` 与 `POST /v1/breedings` 返回 501 —— 明确「契约已冻结、实现未到」的占位语义，使前端既不会误判为可用，也不会误判为 404 路径不存在。 |
| 8 | `test_ws_envelope_contract` | 连上 `/v1/ws` 先收到 `v == 1`、`type == "sys.hello"` 且带 `ts`/`seq` 的问候帧；再发一个 `arena.fish_state` 信封会收到 `sys.echo` —— 钉住 WS 信封形状与当前 MVP 回显行为（真正的 `arena.*` 推送流尚未实现）。 |
| 9 | `test_pause_blocks_advance` | `pause` 后 `running is False`，`release(steps=5)` **不推进**（`step` 仍为 0）；再 `pause` 恢复后 `release(steps=5)` 推进到 `step == 5` —— 证明暂停真的阻塞推进，而不是只翻一个没人读的布尔。 |

### 说明

- 事件名的**权威名单**是 `tests/test_arena.py::KNOWN_EVENTS`（`arena.spawn` / `arena.prey_captured` / `arena.capture_attempt` / `arena.escape` / `arena.energy_depleted` / `arena.episode_end` / `arena.fish_captured` / `arena.collision`）；新增事件必须先改该集合。**8 项，不多不少。**
- 回归与契约加强用例：Arena 侧 #12–#15 与 API 侧 #9 共 5 个测试函数，分别覆盖 reset 幂等 / episode 幂等 / 死鱼不计逃脱 / 目标获取计数 / pause 阻塞推进；API 侧 #6 断言 RFC 7807 五字段（`type` / `title` / `status` / `detail` / `instance`）。
- Arena 的完整契约与实现映射见 `src/evogenesis/arena/Danio_Arena设计与实现说明.md`；API 实现说明见 `src/evogenesis/api/API接口.md`。合并稿的前半部分描述规范，§18 描述实现现状与契约状态。
