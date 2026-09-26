# API 接口参考（api/）

> `api/` 的接口文档：逐个端点说明路径、参数、请求、响应、错误与代码位置。
> 命名规范 R1–R11 与系统约定见同目录 `API与系统工程.md`；契约模型见 `src/evogenesis/api/schemas.py`。
> 状态图例：**已实现** ｜ **实现中（语义待定）** ｜ **未实现（返回 501）**。

## 0. 通用约定

- Base path `/v1`；请求与响应 `Content-Type: application/json`。
- 错误统一为 RFC 7807（`application/problem+json`）：`{type, title, status, detail, instance}`。
- 成功状态码：`201` 创建、`200` 读取、`204` 无响应体；异步任务用 `202`。
- 未实现的模块统一返回 `501`，`detail` 指明归属。
- 分页：`?limit=&cursor=` → `{items, next_cursor}`。
- 稳定 ID：`session_id` / `fish_id` / `genome_id` / `generation_id` / `experiment_id` / `environment_id`；前端不得用数组下标当 identity。
- WebSocket `/v1/ws`，信封 `{v, type, seq, ts, payload}`，`type` 为点分层。

---

## 1. Arena 会话接口（已实现）

### 1.1 POST `/v1/sessions` — 创建会话

创建一个内存中的 Arena 会话（后端权威），初始化种群并返回摘要。

- **请求体**：无。

- **成功响应** `201` → `SessionSummary`

  | 字段 | 类型 | 说明 |
  |---|---|---|
  | `session_id` | string | 会话 ID，形如 `session_<12hex>` |
  | `generation` | int | 代次，新会话为 `0` |
  | `environment` | string | `food_rich` / `predator_rich` / `resource_scarce` |
  | `population` | int | 鱼总数 |
  | `running` | bool | 是否运行中（新会话为 `true`） |
  | `master_seed` | int | 主种子 |
  | `fish_alive` | int | 存活鱼数 |
  | `prey_remaining` | int | 剩余猎物数 |

  示例：
  ```json
  {"session_id":"session_e31164c2b25c","generation":0,
   "environment":"food_rich","population":12,"running":true,
   "master_seed":20260925,"fish_alive":12,"prey_remaining":24}
  ```

- **代码位置**：`session.py` → `create_session`。

### 1.2 GET `/v1/sessions/{session_id}` — 会话摘要

- **路径参数**：`session_id`（string，必填）。
- **成功响应** `200` → `SessionSummary`（字段同 1.1）。
- **错误**：`404` —— 会话不存在。
- **代码位置**：`session.py` → `get_session`。

### 1.3 POST `/v1/sessions/{session_id}/reset` — 重置会话

把 Arena 重置回初始布局，`generation` 归零、`running` 置 `true`。同一 `master_seed` 下重置结果可复现（`reset()` 幂等）。

- **路径参数**：`session_id`（string，必填）。
- **成功响应** `200` → `SessionSummary`（`generation` 为 0）。
- **错误**：`404` —— 会话不存在。
- **代码位置**：`session.py` → `reset_session`。

### 1.4 DELETE `/v1/sessions/{session_id}` — 结束会话

从内存移除会话。

- **路径参数**：`session_id`（string，必填）。
- **成功响应** `204`（无响应体）。
- **错误**：`404` —— 会话不存在。
- **代码位置**：`session.py` → `delete_session`。

### 1.5 GET `/v1/sessions/{session_id}/fish/{fish_id}` — Fish Card

返回单条鱼的卡片。

- **路径参数**：`session_id`、`fish_id`（均必填）。
- **成功响应** `200` → `FishCard`

  | 字段 | 类型 | 说明 |
  |---|---|---|
  | `fish_id` | string | 鱼 ID |
  | `generation` | int | 代次 |
  | `genome_id` | string | 基因组 ID（Arena 直生个体为 `"unknown"`，接入发育后回填） |
  | `viable` | bool | 发育可行性（Arena 个体恒 `true`） |
  | `energy` | float | 当前能量 |
  | `size` | float | 当前体型 |
  | `fitness` | float \| null | 适应度（未接入评价体系时为 `null`） |
  | `cell_counts` | object | 细胞类型计数（未接入发育时为空） |
  | `metrics` | object | 见下 |

  `metrics` 字段：`alive`、`captures`、`encounters`、`predator_encounters`、`escape_successes`、`survival_steps`。

- **错误**：`404` —— 会话或 `fish_id` 不存在。
- **代码位置**：`session.py` → `fish_card`。

### 1.6 POST `/v1/sessions/{session_id}/release` — 释放 / 推进 Arena

驱动 Arena 前进若干步；默认由 `ExpertPolicy` 驾驶每条存活鱼。

- **路径参数**：`session_id`（string，必填）。
- **查询参数**：

  | 名称 | 类型 | 默认 | 说明 |
  |---|---|---|---|
  | `steps` | int | `1` | 前进步数 |
  | `use_expert` | bool | `true` | `true` 时用 ExpertPolicy 驾驶 |

- **成功响应** `200` → `SessionSummary`。
- **副作用**：推进仿真；到 `episode_steps`（默认 600）后不再前进。
- **错误**：`404` —— 会话不存在。
- **语义**：当前实现为"推进/播放"，与 `API与系统工程.md §4.3` 中"释放鱼进入 Arena"的措辞不一致，待认领（`research/notes/arena-api-决策认领表.md` B1）。
- **代码位置**：`session.py` → `release`。

### 1.7 POST `/v1/sessions/{session_id}/pause` — 暂停 / 恢复仿真

翻转会话的 `running` 标志：暂停后 `release` 不再推进；再次调用恢复。

- **路径参数**：`session_id`（string，必填）。
- **成功响应** `200` → `SessionSummary`（`running` 反映新状态）。
- **错误**：`404` —— 会话不存在。
- **语义**：当前用同一端点 toggle 兼作恢复，尚无独立 `resume` 端点，待认领（认领表 B2）。
- **代码位置**：`session.py` → `pause`。

### 1.8 GET `/v1/sessions/{session_id}/snapshot` — 快照

返回当前帧的鱼位姿、能量与最近事件。

- **路径参数**：`session_id`（string，必填）。
- **成功响应** `200` → `Snapshot`

  | 字段 | 类型 | 说明 |
  |---|---|---|
  | `session_id` | string | 会话 ID |
  | `step` | int | 当前步 |
  | `fish` | object | key 为 `fish_id`，值见下 |
  | `events` | array | 最近 200 条事件 |

  `fish[<id>]` 字段：`x`、`y`、`heading`、`speed`、`energy`、`size`、`alive`。

  示例：
  ```json
  {"session_id":"session_e31164c2b25c","step":300,
   "fish":{"fish_00":{"x":10.639,"y":37.117,"heading":6.589,
                      "speed":0.54,"energy":0.742,"size":1.008,"alive":true}},
   "events":[{"seq":1,"type":"arena.spawn","step":0,"payload":{"entity_id":"fish_00"}}]}
  ```

- **错误**：`404` —— 会话不存在。
- **代码位置**：`session.py` → `snapshot`。

### 1.9 GET `/v1/sessions/{session_id}/leaderboard` — 排行榜

按 `(captures, survival_steps)` 降序排列。

- **路径参数**：`session_id`（string，必填）。
- **成功响应** `200` → `Leaderboard`

  | 字段 | 类型 | 说明 |
  |---|---|---|
  | `session_id` | string | 会话 ID |
  | `generation` | int | 代次 |
  | `entries` | array | 排名项 |

  `entries[]` 字段：`rank`、`fish_id`、`captures`、`survival_steps`、`energy`、`fitness`（当前恒 `null`）。

- **错误**：`404` —— 会话不存在。
- **代码位置**：`session.py` → `leaderboard`。

### 1.10 GET `/v1/health` — 健康检查

- **成功响应** `200` → `{"status":"ok"}`。
- **代码位置**：`app.py` → `health`。

---

## 2. 模型与实验接口（契约已定，当前返回 501）

这些端点由 `stubs.py` 定义请求/响应形状（`schemas.py`），在模型与实验管线落地前统一返回：

```json
{"type":"about:blank","title":"Not Implemented","status":501,
 "detail":"Pipeline not implemented yet -- owned by 池伟豪 (genome/development/breeding/evolution).",
 "instance":"/v1/developments"}
```

| 端点 | 方法 | 用途 | 请求体 | 成功响应（计划） |
|---|---|---|---|---|
| `/v1/story-mutations` | GET | 预验证 SNP 列表 | — | `[StoryMutation]` |
| `/v1/genomes/{genome_id}/mutations` | POST | base 编辑 | `MutationRequest` | `201` `MutationResult` |
| `/v1/developments` | POST | 发育解码 | `DevelopmentRequest` | `DevelopmentResult` |
| `/v1/breedings` | POST | 繁殖 | `BreedingRequest` | `BreedingResult` |
| `/v1/sessions/{session_id}/evolutions` | POST | 演化 | — | `202` `JobStatus` |
| `/v1/experiments` | POST | 启动正式实验 | `ExperimentCreate` | `202` `JobStatus` |
| `/v1/experiments` | GET | 实验列表（分页） | — | `Page` |
| `/v1/experiments/{experiment_id}` | GET | 实验元数据 + 指标 | — | `ExperimentDetail` |
| `/v1/jobs/{job_id}` | GET | 任务状态 / 进度 | — | `JobStatus` |
| `/v1/jobs/{job_id}/cancel` | POST | 取消任务 | — | `JobStatus` |

**请求/响应模型字段**（`schemas.py`）：

- `StoryMutation`：`genome_id`、`position`、`from_base`、`to_base`、`tag`
- `MutationRequest`：`position`(int ≥0)、`base`(`A|C|G|T`)；`MutationResult`：`genome_id`、`new_genome_id`、`diff`
- `DevelopmentRequest`：`genome_id`、`seed`；`DevelopmentResult`：`genome_id`、`dev_trace`、`phenotype`
- `BreedingRequest`：`genome_a`、`genome_b`、`n_offspring`；`BreedingResult`：`offspring`、`meiosis_trace`
- `ExperimentCreate`：`name`、`seeds`(int[])、`environment`、`generations`；`ExperimentSummary`：`experiment_id`、`name`、`status`、`seeds`
- `JobStatus`：`job_id`、`status`(`queued|running|done|failed|cancelled`)、`progress`(0–1)、`detail`
- `Page`：`items`、`next_cursor`

> ⚠️ `ExperimentCreate.seeds` 与 `schemas/experiment.schema.json` 的 `seed`(int) + `*_config` 字段集不相交，待认领（认领表 B6）。

- **代码位置**：`stubs.py`（各同名函数）。

---

## 3. WebSocket `/v1/ws`

长连接；所有消息为同一信封：`{v, type, seq, ts, payload}`。

| type | 方向 | payload | 触发 | 状态 |
|---|---|---|---|---|
| `sys.hello` | 服务端 → 客户端 | `{note}` | 连接建立时一次 | 已实现 |
| `sys.echo` | 服务端 → 客户端 | `{echo}` | 每收到一条合法消息 | 已实现（契约演示） |
| `sys.error` | 服务端 → 客户端 | `{echo}` | 收到非法信封 | 已实现 |
| `arena.*` / `brain.*` / `job.*` | 服务端 → 客户端 | 待定 | 实时推送（§5 数据流） | 未实现 |

- `seq`：当前为进程内全局单调递增（非连接内），作用域待认领（认领表 B5）。
- **代码位置**：`ws.py` → `ws_endpoint`。

---

## 4. 错误约定

所有错误体为 RFC 7807，示例（`GET /v1/sessions/nope`）：

```json
{"type":"about:blank","title":"Not Found","status":404,
 "detail":"session nope not found","instance":"/v1/sessions/nope"}
```

| 状态码 | 触发 |
|---|---|
| `404` | 会话 / 鱼不存在 |
| `422` | 请求体校验失败（`RequestValidationError`） |
| `501` | 端点归属的模块尚未实现 |

- **代码位置**：`app.py` → `http_exception_handler`、`validation_exception_handler`。

---

## 5. 变更记录

| 日期 | 改动 |
|---|---|
| 2026-09-25 | 建立逐端点接口文档，覆盖全部 21 个端点与 WS 消息 |
