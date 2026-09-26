# API 接口参考（api/）

> **实现状态（2026-09-26）**：`api/` 已按本契约**重写并接线**（`app.py` / `schemas.py` / `session.py` / `stubs.py` / `ws.py`；Arena 会话端点 functional、模型/实验端点 501、WS 仅 `sys.hello` / `sys.error`）。§0–§5 为契约，§6–§11 的现状表已按重写后实现回填。

> **管辖范围**：逐端点接口参考（请求/响应/错误/实现细节）。（层级与归属见 `AGENTS.md`「文档层级与优先级」。）

> 状态：v1.2 接口参考（**契约**）。§6–§11「实现现状」已按 2026-09-26 重写后的实现回填。
> 归属：池伟豪（`api/` 全部端点；2026-09-26 裁定，见 §6）
> 上游契约：同目录 `API与系统工程.md`（命名规范 R1–R11、系统与部署约定）、`../arena/Danio_Arena设计与实现说明.md`、`../core/核心机制与数据流.md`、`../../../docs/参数总表.json`
> ⚠️ 本文件 **§0–§5 讲"接口是什么"（契约参考）**，**§6–§11 讲"实现现在是什么样"（现状与契约边界）**。
> 凡上游文档未定义的数值与语义，状态一律为 `草案待确认`，逐条列在 `research/notes/arena-api-决策认领表.md`，须经双方认领后写进上游文档才能升为契约。
> **未认领的数值不得进论文与正式实验。**

> `api/` 的接口文档：逐个端点说明路径、参数、请求、响应、错误与代码位置。
> 命名规范 R1–R11 与系统约定见同目录 `API与系统工程.md`；契约模型见 `src/evogenesis/api/schemas.py`。
> 状态图例：**已实现** ｜ **实现中（语义待定）** ｜ **未实现（返回 501）**。

## 0. 通用约定

- Base path `/v1`；请求与响应 `Content-Type: application/json`。
- 错误统一为 RFC 7807（`application/problem+json`）：`{type, title, status, detail, instance}`。
- 成功状态码：`201` 创建、`200` 读取、`204` 无响应体；异步任务用 `202`。
- 未实现的模块统一返回 `501`，`detail` 指明归属。
- 分页：`?limit=&cursor=` → `{items, next_cursor}`。
- 稳定 ID：`session_id` / `fish_id` / `genome_id` / `generation` / `experiment_id` / `environment_id`；前端不得用数组下标当 identity。
- WebSocket `/v1/ws`，信封 `{v, type, seq, ts, payload}`，`type` 为点分层。

---

## 1. Arena 会话接口（契约；已实现）

> 本节 §1.1–§1.10 为**接口契约**（路径/参数/响应/错误）；`api/session.py` 已按本节实现（2026-09-26 重写），前端契约满足。

### 1.1 POST `/v1/sessions` — 创建会话

创建一个内存中的 Arena 会话（后端权威），初始化种群并返回摘要。

- **请求体**：无。

- **成功响应** `201` → `SessionSummary`

  | 字段 | 类型 | 说明 |
  |---|---|---|
  | `session_id` | string | 会话 ID，形如 `session_<12hex>` |
  | `generation` | int | 代次，新会话为 `0` |
  | `environment` | string | `default` / `food_rich` / `predator_rich` / `resource_scarce`（owner：`experiment §4`） |
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
- **语义（已定稿）**：**推进仿真前进 `steps` 步**（`B1` 已闭合）；上游 `API与系统工程.md §4.3` 措辞已同步为「推进 `steps` 步」。
- `use_expert=false` 时不注入动作（每条存活鱼按 `(ω,v)=(0,0)`），仅环境规则推进。
- **代码位置**：`session.py` → `release`。

### 1.7 POST `/v1/sessions/{session_id}/pause` — 暂停 / 恢复仿真

翻转会话的 `running` 标志：暂停后 `release` 不再推进；再次调用恢复。

- **路径参数**：`session_id`（string，必填）。
- **成功响应** `200` → `SessionSummary`（`running` 反映新状态）。
- **错误**：`404` —— 会话不存在。
- **语义（已定稿）**：`pause` 为 **toggle**（暂停 / 恢复同一端点），不另开 `resume` 端点（`B2` 已闭合；`API与系统工程.md §4.3`）。
- **代码位置**：`session.py` → `pause`。

### 1.8 GET `/v1/sessions/{session_id}/snapshot` — 快照

返回当前帧的**全场实体**（鱼 + 猎物 + 捕食者 + 障碍）与最近事件。

- **路径参数**：`session_id`（string，必填）。
- **成功响应** `200` → `Snapshot`

  | 字段 | 类型 | 说明 |
  |---|---|---|
  | `session_id` | string | 会话 ID |
  | `step` | int | 当前步 |
  | `fish` | object | key 为 `fish_id`，值见下 |
  | `prey` | object | key 为 `prey_id`，值 `{x, y, size, alive}` |
  | `predators` | object | key 为 `predator_id`，值 `{x, y, size}` |
  | `obstacles` | array | 元素 `{x, y, radius}` |
  | `events` | array | 最近 200 条事件 |

  `fish[<id>]` 字段：`x`、`y`、`heading`、`speed`、`energy`、`size`、`alive`。

  > ⚠️ **`prey` / `predators` / `obstacles` 不可省**：前端渲染**硬依赖**这三个键（`frontend/src/panels/DanioArenaPanel.tsx` 对 `snap.obstacles` 直接 `for...of`、对 `snap.prey` / `snap.predators` 直接 `Object.values`，**无 `undefined` 保护**）；缺任一键会抛 `TypeError` 致画布全黑。数据来源 = `DanioArena.prey` / `.predators` / `.obstacles`（`arena/env.py`），与 `API与系统工程.md §4.3` 的「全场快照」一致。

  示例：
  ```json
  {"session_id":"session_e31164c2b25c","step":300,
   "fish":{"fish_00":{"x":10.639,"y":37.117,"heading":6.589,
                      "speed":0.54,"energy":0.742,"size":1.008,"alive":true}},
   "prey":{"prey_00":{"x":22.301,"y":12.874,"size":1.0,"alive":true}},
   "predators":{"predator_00":{"x":80.0,"y":30.0,"size":2.4}},
   "obstacles":[{"x":50.0,"y":30.0,"radius":4.0}],
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

## 2. 模型与实验接口（契约已定；当前返回 501）

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
| `/v1/experiments` | POST | 启动正式实验 | `ExperimentLaunch` | `202` `JobStatus` |
| `/v1/experiments` | GET | 实验列表（分页） | — | `Page[ExperimentSummary]` |
| `/v1/experiments/{experiment_id}` | GET | 实验元数据 + 指标 | — | `ExperimentDetail` |
| `/v1/jobs/{job_id}` | GET | 任务状态 / 进度 | — | `JobStatus` |
| `/v1/jobs/{job_id}/cancel` | POST | 取消任务 | — | `JobStatus` |

**请求/响应模型字段**（`schemas.py`）：

- `StoryMutation`：`genome_id`、`position`、`from_base`、`to_base`、`tag`
- `MutationRequest`：`position`(int ≥0)、`base`(`A|C|G|T`)；`MutationResult`：`genome_id`、`new_genome_id`、`diff`
- `DevelopmentRequest`：`genome_id`、`seed`；`DevelopmentResult`：`genome_id`、`dev_trace`、`phenotype`
- `BreedingRequest`：`genome_a`、`genome_b`、`n_offspring`；`BreedingResult`：`offspring`、`meiosis_trace`
- `ExperimentLaunch`（**实验启动请求**：一请求展开为 N 个 `ExperimentRun`，见下）：`name`、`seeds`(int[])、`environment`、`generations`；`ExperimentSummary`：`experiment_id`、`name`、`status`、`seeds`
- `JobStatus`：`job_id`、`status`(`queued|running|done|failed|cancelled`)、`progress`(0–1)、`detail`
- `Page[T]`（分页泛型，R9）：`items`、`next_cursor`；`GET /v1/experiments` 为 `Page[ExperimentSummary]`

> ✅ **两对象并存（B6 已闭合，2026-09-26）**：本层 `ExperimentLaunch`（多 `seeds` × `generations` → `202` job，展开为 N 个 run）与 Tier3 `schemas/experiment.schema.json` 的 **`ExperimentRun`**（单 `seed` + 三条 config 路径，**单 run 元数据**，已定稿）是**不同物**，非同一契约的两版。`environment` 枚举统一为 `default / food_rich / predator_rich / resource_scarce`（owner：`experiment §4`）。

- **代码位置**：`stubs.py`（各同名函数）。

---

## 3. WebSocket `/v1/ws`

长连接；所有消息为同一信封：`{v, type, seq, ts, payload}`。

> `sys.hello` 与 `sys.error` 已实现（`ws.py`）；`sys.echo` **未实现**（待认领，`§11` B5）；业务推送（`arena.*` / `brain.*` / `job.*`）仍未定义（阻塞：采样率与推送清单未定）。

| type | 方向 | payload | 触发 | 状态 |
|---|---|---|---|---|
| `sys.hello` | 服务端 → 客户端 | `{note}` | 连接建立时一次 | 已实现 |
| `sys.echo` | 服务端 → 客户端 | `{echo}` | 每收到一条合法消息 | **未实现**（B5 待认领） |
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
| 2026-09-26 | 追加 §6–§11「实现现状与契约边界」：端点 functional / 501 × 归属一览、纯内存会话、未生效字段、`release` / `snapshot.events` 口径、WS 现状 vs §5 目标、RFC 7807 覆盖边界、测试覆盖、未认领的实现决定。与 `../arena/Danio_Arena设计与实现说明.md` §18 同源 |

---

## 6. 端点总览：functional / 501 × 归属

> **本表已按 2026-09-26 重写回填**：Arena 会话端点（含 WS）**functional**、模型/实验端点 **501 stub**，与 `session.py` / `ws.py` / `stubs.py` 一致；计数仍为 11 functional + 10 stub。
> **归属（2026-09-26 裁定）**：`api/` **全部端点由池伟豪负责实现**；表内「李辰钊」列为历史协作者记录。

§1 / §2 按端点逐个说明；本表给出**实现状态 × 归属**的一览，用于快速判断"某端点现在归谁、能不能用"。

状态口径：**functional** = 真实读写 `DanioArena` / 内存会话并返回真实数据；**501 stub** = 已声明请求 / 响应形状（`schemas.py`），调用即抛 `HTTP 501`（响应体为 RFC 7807，见 §4 与 §9）。

| 方法 | 路径 | 状态 | 归属 | 实现位置 |
|---|---|---|---|---|
| POST | `/v1/sessions` | **functional**（`201`） | 李辰钊 | `session.py::create_session` |
| GET | `/v1/sessions/{session_id}` | **functional** | 李辰钊 | `session.py::get_session` |
| POST | `/v1/sessions/{session_id}/reset` | **functional** | 李辰钊 | `session.py::reset_session` |
| DELETE | `/v1/sessions/{session_id}` | **functional**（`204`） | 李辰钊 | `session.py::delete_session` |
| GET | `/v1/sessions/{session_id}/fish/{fish_id}` | **functional** | 李辰钊 | `session.py::fish_card` |
| POST | `/v1/sessions/{session_id}/release` | **functional** | 李辰钊 | `session.py::release` |
| POST | `/v1/sessions/{session_id}/pause` | **functional** | 李辰钊 | `session.py::pause` |
| GET | `/v1/sessions/{session_id}/snapshot` | **functional** | 李辰钊 | `session.py::snapshot` |
| GET | `/v1/sessions/{session_id}/leaderboard` | **functional** | 李辰钊 | `session.py::leaderboard` |
| GET | `/v1/health` | **functional** | 李辰钊 | `app.py::health` |
| WS | `/v1/ws` | **functional**（仅信封契约） | 李辰钊 | `ws.py::ws_endpoint`（见 §8） |
| GET | `/v1/story-mutations` | **501 stub** | 池伟豪 | `stubs.py::list_story_mutations` |
| POST | `/v1/genomes/{genome_id}/mutations` | **501 stub** | 池伟豪 | `stubs.py::mutate_genome` |
| POST | `/v1/developments` | **501 stub** | 池伟豪 | `stubs.py::develop` |
| POST | `/v1/breedings` | **501 stub** | 池伟豪 | `stubs.py::breed` |
| POST | `/v1/sessions/{session_id}/evolutions` | **501 stub** | 池伟豪 | `stubs.py::evolve` |
| POST | `/v1/experiments` | **501 stub** | 池伟豪 | `stubs.py::start_experiment` |
| GET | `/v1/experiments` | **501 stub** | 池伟豪 | `stubs.py::list_experiments` |
| GET | `/v1/experiments/{experiment_id}` | **501 stub** | 池伟豪 | `stubs.py::get_experiment` |
| GET | `/v1/jobs/{job_id}` | **501 stub** | 池伟豪 | `stubs.py::get_job` |
| POST | `/v1/jobs/{job_id}/cancel` | **501 stub** | 池伟豪 | `stubs.py::cancel_job` |

**计数**：functional **11**（9 个会话端点 + `/v1/health` + WS），501 stub **10**，合计 **21**。

**§2 的 10 个 stub 共享同一个异常实例**：`stubs.py::_NOT_IMPL = HTTPException(501, detail="Pipeline not implemented yet -- owned by 池伟豪 (genome/development/breeding/evolution).")`，全部 `raise` 同一对象。其中 `evolutions` 与 `experiments` 的装饰器带 `status_code=202`，但**因为一开始就 `raise`，实际永远返回 501** —— `202` 只出现在 OpenAPI（`/openapi.json`）里，见 §11 L7。

---

## 7. 会话存储与端点实现细节

### 7.1 会话存储：纯内存，无持久化

| 项 | 实现事实 |
|---|---|
| 存储结构 | `SessionManager._sessions: dict[str, Session]`（模块级单例 `_manager = SessionManager()`） |
| 持久化 | **无**。无磁盘、无 DB、无快照 |
| TTL / 淘汰 | **无**。不设过期、不设上限、不 LRU |
| 进程重启 | **全部会话丢失**。这是 MVP 的明确取舍（`SessionManager` docstring："Holds live sessions in memory (MVP; no persistence)"） |
| 并发 | 每个 `Session` 持 `threading.Lock`，`advance` / `reset` / `snapshot` / `fish_card` / `leaderboard` / `summary` 串行化；`SessionManager` 表本身无锁。uvicorn 默认单 worker 安全；多 worker（`--workers >1`）会让同一 `session_id` 落到不同进程而表现为随机 404 |
| `session_id` 规则 | `f"session_{uuid.uuid4().hex[:12]}"` —— 前缀 `session_` + **12 位十六进制**（48 bit 随机）。**不是顺序号**；调用方**不得据其结构推断顺序或身份**，仅可作展示用途剥离前缀（`frontend/src/panels/DanioArenaPanel.tsx` 即仅做前缀剥离 + 截断展示）。注意这是**运行期会话令牌**，与 `core §3.1` 的稳定 ID（`fish_id` / `genome_id` …）不是同一物 |
| 不存在时行为 | 所有 `/v1/sessions/{session_id}/*` 端点走 `_get_session()`，未命中抛 `HTTPException(404, detail=f"session {session_id} not found")`，响应体为 RFC 7807（见 §4） |

### 7.2 `SessionCreate`：被接收但未生效的字段

```python
class SessionCreate(BaseModel):
    environment: Environment = "food_rich"
    master_seed: int = 0
    arena_config_path: str = "configs/default_arena.yaml"
    model_config_path: str = "configs/default_model.yaml"
```

> ⚠️ §1.1 的「请求体：无」只说明该 body **可省略**（4 个字段全有默认值），并不表示不存在请求体模型 —— `create_session` 的形参就是 `create: SessionCreate`。下表列出全部 4 个字段的实际效果。

| 字段 | 是否生效 | 说明 |
|---|---|---|
| `master_seed` | ✅ 生效 | 经 `arena_seeds_for(master_seed, session._SESSION_ARENA_INDEX)`（`=0`）派生 `spawn_seed` / `dynamics_seed` 传入 `DanioArena`（`core §3`）；是**唯一的复现开关** |
| `environment` | ⚠️ **仅存储回显** | 写入 `Session.environment` 并在 `SessionSummary` 回显；**不改变任何 Arena 参数** —— `food_rich` / `predator_rich` / `resource_scarce` 三档行为完全一致（实测三档位的 `population` / `prey_remaining` 与初始世界完全相同）。场景布置见 `../arena/Danio_Arena设计与实现说明.md` §12 |
| `arena_config_path` | ✅ 生效 | `Session.__init__` 经 `arena.config.load_arena_config` 读取（相对路径按仓库根解析），Arena 实际取值以该文件为准 |
| `model_config_path` | ❌ **未生效** | Demo 用 `ExpertPolicy` 驱动，不加载 DanioNet，故接收但不参与本层行为（`API与系统工程.md` §4.3）；接入模型驱动时生效 |

**结论：`master_seed` 与 `arena_config_path` 生效，`model_config_path` 暂不参与（Demo 走 `ExpertPolicy`）。** 前端只发 `master_seed` + `environment`，均兼容。

### 7.3 `release` 的实现细节

- `steps` / `use_expert` 是 **query 参数**（不是请求体）：`POST /v1/sessions/{sid}/release?steps=30&use_expert=true`。
- **`steps` 无上界校验** —— 实测 `steps=100000` 被接受并同步跑完（止步于 `episode_steps = 600`）。
- 端点是**同步阻塞**的：`release` 在请求线程内跑完 N 步仿真后才返回；无 `202`、无 job、无后台任务。
- `pause` 后 `release` 会整段短路（首行 `if not self.running: return`），仍返回 `200` + `SessionSummary`（`step` 不变）—— 调用方无法从状态码区分"推进了"与"被暂停"。
- episode 到达 `episode_steps` 时 `StepResult.done=True`（A9：跑满全程，个体死亡**不**结束 episode），`advance()` 随即 `break`；`snapshot.step` 上限即 `episode_steps`（默认 600），`events` 末尾有 `arena.episode_end`。

### 7.4 `snapshot.events` 的口径

`events` 是 **`arena.events[-200:]`** —— **整局累积事件的最后 200 条**，**不是"本步事件"**。

- 刚创建 / 刚 `reset()` 时恰为 **39 条** `arena.spawn`（12 fish + 24 prey + 3 predator；障碍不发事件）。
- 推进到第 600 步时最多 200 条且**跨越很多步**。
- 调用方若要"本步新增事件"，须自行 diff `seq`。
- `200` 为模块常量 `session._EVENTS_TAIL`，见 §11 L5。

逐事件语义与 8 项事件词表见 `../arena/Danio_Arena设计与实现说明.md` §18 实现映射。

---

## 8. WebSocket 现状 vs `API与系统工程.md` §5 目标推送清单

### 8.1 现状（`ws.py`）

| 项 | 实现事实 |
|---|---|
| 端点 | `@router.websocket("/v1/ws")` |
| 连接建立 | `await ws.accept()` 后**立即**下发一条 `sys.hello`，payload `{"note": "EvoGenesis WS contract v1 (R11 envelope)"}` |
| 收消息 | 循环 `receive_text()`；`WSMessage.model_validate_json(raw)` 失败 → `sys.error`（成功则忽略，无 `sys.echo`） |
| 回消息 | 无论 echo 还是 error，**都回同一条** `WSMessage`，`payload` 恒为 `{"echo": <原始字符串>}` |
| `sys.error` 不回原因 | `except Exception:` 只改 `reply_type`，`payload` 仍是 `{"echo": raw}`。违规**原因**（缺 `v` / 缺 `seq` / 非 JSON / `type` 非字符串）既**不回给客户端**，也**不写日志**（无 `logger`、无 `print`）⇒ 服务端无痕迹，客户端只能自行回读 `payload.echo` 猜 |
| `seq` | 模块级全局 `_ws_seq` 自增（`global`），**按进程而非按连接**计数；跨连接共享，且**与 `Event.seq`（arena 事件序）无关** |
| `ts` | `time.time()`（Unix 秒，float） |
| 断开 | 无清理、无连接注册表 |

### 8.2 差距（现状 vs §5 目标）

`API与系统工程.md` §5 列出的是**目标推送清单**（"实时传"），`ws.py` 的 docstring 亦写明 "real arena.brain/job broadcasts land in later iterations"。逐项对照：

| §5 目标 | 现状 | 差距 |
|---|---|---|
| fish transforms | 无推送。客户端只能轮询 `GET .../snapshot` | ❌ 硬缺口 |
| selected-fish neural activation | 无。依赖 DanioNet 接入与"选中鱼"的服务端状态 | ❌ 双重缺口 |
| energy | 无推送；只能随 snapshot 的 `fish[].energy` 被动取到 | ❌ 缺口 |
| events | 无推送；只能随 snapshot（末 200 条）被动取到 | ❌ 缺口 |
| generation progress | 无。`generation` 可由构造注入、代循环（`experiment/evolution_run.py`）逐代推进；API 层尚未暴露 | ❌ 缺口 |
| 不每帧发送全部 48×48 matrix | ✅ 已满足（因为**什么都不发**，天然不违规） | ⚠️ 空集意义上的满足；`../core/核心机制与数据流.md` §5.2 的"矩阵只存在于发育产物与落盘记录"须在实现推送时保持 |
| `type` 点分层命名 | ✅ `sys.hello` / `sys.echo` / `sys.error` 遵守 R11 | ✅ |
| 信封 `{v,type,seq,ts,payload}` | ✅ 已实现并被 `test_ws_envelope_contract` 守护 | ✅ |

**现状只有 `sys.hello` / `sys.error` 两条系统消息，没有任何业务广播，也没有广播机制**（无连接注册表、无 `broadcast()` 函数）。§5 的 5 类业务推送一条都还没有。

---

## 9. RFC 7807 的覆盖边界

§4 的 RFC 7807（R10）已在 `app.py` 落地，但**只覆盖两类异常**，边界如下。

| 项 | 内容 |
|---|---|
| 挂载点 | `@app.exception_handler(HTTPException)` → `_problem(...)`；`@app.exception_handler(RequestValidationError)` → `_problem(request, 422, str(exc.errors()))` |
| 覆盖 ① | **处理器内部显式抛的 `HTTPException`**（404 会话 / 鱼不存在；501 stub） |
| 覆盖 ② | **`RequestValidationError`**（`422`） |
| **未覆盖**：路由级 404 / 405 | Starlette 路由层抛的是 `StarletteHTTPException`，**不经过**上面注册的 `fastapi.HTTPException` 处理器。实测 `GET /v1/nope` → `404`、`content-type: application/json`、`{"detail":"Not Found"}`；`POST /v1/health` → `405`、`{"detail":"Method Not Allowed"}` |
| **未覆盖**：OpenAPI 不文档化错误体 | `Problem` 模型**没有任何** `response_model=` / `responses=` 引用它，实测 `/openapi.json` 的 `components.schemas` 里**没有 `Problem`**。OpenAPI 消费者看不到错误体形状 |
| `422` 的 `detail` 是 repr 字符串 | `str(exc.errors())` 产出**单引号列表串**（Python repr），非结构化 JSON；机器消费方须自行解析 |
| 实测汇总 | 404（会话不存在）/ 501 / 422 三者的 `content-type` 均为 `application/problem+json`，五字段齐全（`type` = `about:blank`、`title` 取 `HTTPStatus(status).phrase`、`instance` = `request.url.path`） |
| 前端兼容 | 前端只读 `body.detail`；RFC 7807 **保留** `detail`，且 `res.json()` 不校验 content type ⇒ 前端无需改动 |

---

## 10. 测试覆盖（`tests/test_api_contract.py`）

> ✅ `tests/test_api_contract.py` 已随 2026-09-26 重写重建（10 项，`pytest tests/test_api_contract.py` → 10 passed）；下表为**旧实现的历史记录（9 项）**，保留以对照。

**旧实现 9 项**（`d894cbb` 移除前；`pytest tests/test_api_contract.py` → 9 passed）。

| # | 测试 | 覆盖的契约 |
|---|---|---|
| 1 | `test_health` | `GET /v1/health` → 200 且 body 恰为 `{"status": "ok"}` |
| 2 | `test_create_session_and_snapshot` | `POST /v1/sessions` → `201`、`fish_alive == 12`；`GET .../snapshot` → `step == 0`、`len(fish)==12`、`len(prey)==24`、`len(predators)==3`、`len(obstacles)==6` |
| 3 | `test_release_advances_arena` | `POST .../release?steps=30` → 200，随后 snapshot 的 `step == 30` |
| 4 | `test_fish_card_and_leaderboard` | `GET .../fish/fish_00` → 200 且 `fish_id` 回显；`GET .../leaderboard` → `entries` 长度 12 |
| 5 | `test_reset_session` | 推进 50 步后 `reset` → 200，snapshot 的 `step == 0` |
| 6 | `test_missing_session_404` | 未知 `session_id` → 404，body 为 **RFC 7807 五字段**（`type` / `title` / `status` / `detail` / `instance`） |
| 7 | `test_stubs_return_501` | `POST /v1/developments`、`POST /v1/breedings` → 501（10 个 stub 中抽 2 个代表） |
| 8 | `test_ws_envelope_contract` | WS 连上收到 `v==1`、`type=="sys.hello"`、含 `ts` / `seq`（新实现另测非法消息 → `sys.error`） |
| 9 | `test_pause_blocks_advance` | `pause` → `running is False`；`release(steps=5)` 后 `step` 仍为 0；再 `pause` → `running is True`；`release(steps=5)` 后 `step == 5` |

**未覆盖（已知缺口）**：

- `DELETE` / `204` 无响应体路径无测试
- 10 个 stub 中只测了 2 个
- WS 的 **`sys.error` 非法分支**无测试
- `SessionCreate.arena_config_path` / `model_config_path` **被接收但未生效**这件事无测试守护（静默行为）
- `release` 的 `use_expert=false` 分支、团灭后空转分支无测试
- **路由级 404 / 405 不走 RFC 7807**（§9 边界）无测试

---

## 11. 未认领的实现决定

> 以下语义由实现先于设计落地，`API与系统工程.md` 未定义或与实现不一致；在 `research/notes/arena-api-决策认领表.md` 被回答、结论写进上游文档之前，状态一律为 **`草案待确认`**，**不得写进论文与正式实验**。（B1 / B2 已于 2026-09-26 闭合，见下表。）

| 认领编号 | 未认领的内容 | 实现现状 |
|---|---|---|
| **B1** | `release` 到底是什么：实现是"驱动仿真前进 N 步"（`steps` 参数，不产生新实体），而上游 §4.3 写"释放鱼进入 Arena" | ✅ **已闭合（2026-09-26）**：定为「推进 `steps` 步」，上游 §4.3 已同步 |
| **B2** | 暂停 / 恢复语义：`pause` 是 **toggle**（兼作 resume），已真正阻塞 `release`；上游无 resume 端点 | ✅ **已闭合（2026-09-26）**：保留 toggle，不另开 `resume`；上游 §4.3 已同步 |
| **B3** | `generation` / `environment` 是"稳定 ID"还是标量：上游 §3 列为稳定 ID，代码是 `int` / 字符串枚举 | 实现为标量；改文档还是改代码待认领 |
| **B4** | 未实现模块的统一约定：501 + "owned by 池伟豪 …" 是否正式写进上游文档 | 已实现共享 `_NOT_IMPL` 单例；响应体已是 RFC 7807 |
| **B5** | WS 词表：`sys.hello` / `sys.echo`（后者仅为契约演示）是否正式纳入 R11 词表 | `sys.hello` / `sys.error` 已实现；`sys.echo` **未实现**，去留待认领 |
| **B6** | experiment 契约分裂 | ✅ **已闭合（2026-09-26，方案 C）**：承认两对象——API 侧更名为 `ExperimentLaunch`（多 seed，展开为 N 个 `ExperimentRun`），Tier3 `schemas/experiment.schema.json` 维持单 run `ExperimentRun`；`environment` 枚举统一 |
| **B7** | config 未接线：无 loader 读 yaml；`arena_config_path` 被静默忽略；yaml 键名（`live_demo`、缺 `actors` / `biomass_to_size_gain`）与 dataclass 不匹配 | 未变；见 `../arena/Danio_Arena设计与实现说明.md` §18 参数映射 |

**认领表编号之外的新增待决项**（非认领表原有编号，同样不得在未确认前用于指标）：

| # | 待决项 | 说明 |
|---|---|---|
| **L1** | 会话纯内存 | 无持久化 / TTL / 淘汰；进程重启全丢；唯一释放途径是 `DELETE`。多 worker 会表现为随机 404 |
| **L2** | `model_config_path` 接收但未生效（`arena_config_path` 已生效） | Demo 走 `ExpertPolicy`，不加载 DanioNet；已回写 §7.2；接入模型驱动时生效 |
| **L3** | `release` 的 `steps` 无上界、端点同步阻塞 | 实测 `steps=100000` 被接受并同步跑（止步 600，但仍占满请求）；慢客户端会阻塞 worker |
| **L4** | 暂停无调度器 | `pause` 真的阻塞 `release`，但服务端仍**无调度器 / 无后台推进 / 无独立 resume 端点**；前端仍须自停轮询 |
| **L5** | `snapshot.events` 的 `200` 是无文档魔数 | 后改它无从知晓影响面；建议提为模块常量并纳入本文档 |
| **L6** | WS 无广播、无连接注册表；`seq` 为进程级全局 | §8.2 的 5 类推送全部缺失；`seq` 需从进程级改为每连接或全局带来源标识 |
| **L7** | 501 上挂了 `202` 状态码声明 | `/docs` / `/openapi.json` 与实际行为不符（实测实际 501）。有意为之（表意"将来是异步"），可在 `responses=` 里同时声明 202 与 501 |
| **L8** | `FishCard.fitness` / `cell_counts` 恒 `null` / `{}`；`generation` / `genome_id` 恒 `0` / `"unknown"`；`viable` 恒 `True` | 由池伟豪的 genome / development / evolution 落地后填充。**`viable` 的语义是"发育可行性"，不是存活**（源码注释：`# developmental viability; arena survival is in metrics`）；要看存活请读 `metrics.alive` 或 snapshot 的 `fish[].alive` |
| **L9** | `leaderboard` 含已死鱼且长度恒等于 `population` | 与"排行榜"直觉不符；`entries` 不因死亡而缩短（实测恒 12 条） |
| **L10** | RFC 7807 未全覆盖 | 路由级 404 / 405 仍是 `{"detail": ...}`；`Problem` 未进 OpenAPI（§9 边界） |

**事实来源优先级：代码 > 本文档。** 与代码冲突以代码为准（发现冲突请直接改本文档）。
