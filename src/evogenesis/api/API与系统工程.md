# 系统工程与接口规范

> **实现状态（2026-09-26）**：`api/` 已按契约重写并接线（`src/evogenesis/api/`）；`make demo` 与 `scripts/start_demo.sh` / `scripts/serve_api.py` 已恢复。

> **管辖范围**：技术栈、稳定 ID、命名规范、WS/系统约定、Seed Manager、Offline 红线。（层级与归属见 `AGENTS.md`「文档层级与优先级」。）

## 1. 技术栈
### Backend / Model
- Python 3.12（uv 管理，`requires-python >=3.12`）
- PyTorch
- FastAPI
- NumPy
- Pydantic

### Frontend
- Vite 5 + React 18 + TypeScript 5
- Tailwind 3.4 + shadcn/ui + lucide-react
- Canvas 2D（Arena 渲染）、Cytoscape.js 3（脑图）、ECharts 5（图表）
- zustand 4、原生 WebSocket / fetch
- npm + package-lock.json；版本清单与主题见 `frontend/README.md`

要求 CPU 可运行，GPU 有则加速。

## 2. 仓库结构映射

项目采用单包 + 任务分层的仓库；设计包目录与之映射如下：

| 设计包目录 | 本项目 |
|---|---|
| `/frontend` | `frontend/` |
| `/backend` | `src/evogenesis/api/` + `scripts/` |
| `/model` | `src/evogenesis/genome/`、`development/`、`connectome/` |
| `/core` | `src/evogenesis/core/`（机制底座：config / seed / ids / tensors / logging / tracking / registry / io） |
| `/evolution` | `src/evogenesis/evolution/`（繁殖 / 选择 / drift） |
| `/learning` | `src/evogenesis/learning/`（Behavior Cloning） |
| `/experiment` | `src/evogenesis/experiment/`（指标 / run / 代循环编排） |
| `/viz` | `src/evogenesis/viz/`（出图） |
| `/simulation` | `src/evogenesis/arena/` |
| `/experiments` | `configs/` + `scripts/` + `results/runs/` |
| `/assets` | `artifacts/`（+ `data/`） |
| `/checkpoints` | 冻结→`artifacts/`；实验→`results/runs/<id>/` |
| `/demo` | `frontend/` + `scripts/start_demo.*` |
| `/config` | `configs/` |
| `/docs` `/prompts` `/schemas` | 同名保留 |

目录职责与 `AGENTS.md` 的「项目目录结构」一致。

## 3. 稳定 ID 与标量

> **owner 已移出本文件**：稳定 ID 的格式、派生与唯一性域归 `core/核心机制与数据流.md §3.1`（实现 `core/ids.py`）；本表仅列名。

**稳定 ID**（前端不得用数组下标当 identity）：

- `fish_id` — `str`，`<experiment_id>:g<generation>:fish<index:04d>`
- `genome_id` — `str`，`<experiment_id>:g<generation>:genome<index:04d>`
- `experiment_id` — `str`（run 目录名）
- `environment_id` — `str`（由实验对照配置给定，本模块不铸造）

**标量（非 ID）**（B3 定稿，2026-09-27）：

- `generation` — `int`（≥ 0），演化代数；**不**铸造为 ID（`core §3.1`）。
- `environment` — 枚举标量 `default` / `food_rich` / `predator_rich` / `resource_scarce`（owner：`experiment §4`）。

> `environment`（枚举标量，会话/请求用）与 `environment_id`（`str`，事件 header 用）是两个不同的量，不可互相替代。

前端不得使用数组下标当 identity。

## 4. API

### 4.1 命名规范
| # | 规则 | 约定 |
|---|---|---|
| R1 | 版本前缀 | HTTP 路由挂 `/v1`；WS 为 `/v1/ws` |
| R2 | 资源名 | 小写复数名词，多词用 kebab-case（`story-mutations`）；固定单例用单数（`/v1/health`） |
| R3 | 路径 | 零动词；动作以产物名词作子资源（`POST /v1/genomes/{id}/mutations` → 新 genome） |
| R4 | 嵌套 | ≤ 2 层；跨资源以 `session` 为作用域 |
| R5 | 路径参数 | snake_case：`{session_id}` / `{genome_id}` / `{fish_id}` |
| R6 | JSON 字段 | snake_case（与 `schemas/` 一致）；查询参数同 |
| R7 | 方法 | GET 读 / POST 建或触发 / PATCH 局部改 / DELETE 删；动作不走 GET |
| R8 | 状态码 | 201 建、202 异步受理、204 无体、4xx 客户端、5xx 服务端 |
| R9 | 分页 | `?limit=&cursor=`；返回 `{items, next_cursor}` |
| R10 | 错误体 | RFC 7807：`type/title/status/detail/instance` |
| R11 | WS 消息 | 信封 `{v,type,seq,ts,payload}`；`type` 用点分层（`arena.fish_state`、`brain.activation`、`job.progress`、`sys.error`） |

### 4.2 资源词表
`sessions`、`genomes`、`mutations`、`developments`、`phenotypes`、`connectomes`、`breedings`、`fish`、`evolutions`、`generations`、`experiments`、`environmental-selections`、`jobs`、`events`、`metrics`、`leaderboard`、`story-mutations`。

### 4.3 端点（草案）
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/v1/sessions` | 创建会话，返回 `session_id` |
| GET | `/v1/sessions/{session_id}` | 会话摘要：代 / 环境 / 种群 / 运行态 |
| POST | `/v1/sessions/{session_id}/reset` | 重置会话 |
| DELETE | `/v1/sessions/{session_id}` | 结束会话 |
| GET | `/v1/story-mutations` | 预验证 SNP 列表（**未实现：`501`**，见 §4.3 约定） |
| POST | `/v1/genomes` | **创建随机基因组（已实现）**，返回 `genome_id` |
| GET | `/v1/genomes/{genome_id}` | **取回基因组（已实现）** |
| POST | `/v1/genomes/{genome_id}/mutations` | **base 编辑（已实现）**，返回新 `genome_id` + diff |
| POST | `/v1/developments` | **发育（已实现）**，返回 `dev_trace` + phenotype |
| POST | `/v1/breedings` | **繁殖（已实现）**，返回 offspring + meiosis trace |
| GET | `/v1/sessions/{session_id}/fish/{fish_id}` | Fish Card |
| POST | `/v1/sessions/{session_id}/release` | **推进仿真 `steps` 步**（query `steps`/`use_expert`，默认 `ExpertPolicy` 驾驶），返回 `SessionSummary`（B1 定稿） |
| POST | `/v1/sessions/{session_id}/pause` | **暂停 / 恢复开关**（toggle `running`，暂停后 `release` 不推进；无独立 `resume` 端点）（B2 定稿） |
| GET | `/v1/sessions/{session_id}/snapshot` | 全场快照：fish（transforms + energy）+ prey / predators / obstacles + events |
| POST | `/v1/sessions/{session_id}/evolutions` | **会话内演化（过渡：复用环境选择 job，已实现）**，`202` + `job_id` |
| GET | `/v1/sessions/{session_id}/leaderboard` | 排行榜 |
> **通用多协议实验资源 `/v1/experiments` 不在端点草案**（已由 `/v1/environmental-selections` 取代；无消费者、`protocol` 契约未定）。如需通用启动器，须先定义 `protocol` 参数与各协议参数契约再引入。
| POST | `/v1/environmental-selections` | **启动环境选择实验（Experiment F，已实现）**，`202` + `job_id` |
| GET | `/v1/environmental-selections` | 环境选择实验列表（分页，已实现） |
| GET | `/v1/environmental-selections/{experiment_id}` | 环境选择实验详情（已实现） |
| GET | `/v1/jobs/{job_id}` | 任务状态 / 进度 |
| POST | `/v1/jobs/{job_id}/cancel` | 取消任务 |

编辑 / 发育 / 繁殖为同步；演化与正式实验为异步 job，进度经 WS `job.progress` 推送。

**未实现端点的统一约定（B4 定稿，2026-09-27）**：对尚未实现的端点统一返回 **`501` + RFC 7807 `Problem`**，`detail` 注明 owner（如 `stubs.py`）；不返回 `404`、不用空 200 占位。当前唯一此类端点 = `GET /v1/story-mutations`。

## 5. WebSocket
端点 `/v1/ws`；消息信封与命名见 §4.1 R11。可选订阅：`/v1/ws?session_id=<session_id>`。

**推送清单（已定稿，2026-09-26 用户确认）**：

| `type` | payload | 触发 | 状态 |
|---|---|---|---|
| `sys.hello` | `{note, session_id}` | 连接建立一次 | 已实现 |
| `sys.error` | `{echo}` | 收到非法信封 | 已实现 |
| `arena.fish_state` | `{session_id, step, fish:{fish_id:{x,y,heading,speed,energy,size,alive}}}` | 订阅会话每次 `release` 推进后 | 已实现 |
| `arena.events` | `{session_id, events:[{seq,type,step,payload}]}` | 同上（本次新增事件） | 已实现 |
| `job.progress` | `{job_id, status, progress}` | 实验/任务进度或状态变化 | 已实现 |
| `brain.activation` | `{session_id, step, fish:{fish_id: activation[]}}` | **模型驱动会话**（`model_driven=true`）`release` 后；选中鱼由客户端按 `fish` 键取 | 已实现（仅模型驱动会话） |

- **采样率**：**事件驱动**，不做定时采样 —— `arena.*` 由订阅会话的 `release` 触发；不每帧发送全部 48×48 matrix（保持）。
- **`seq`**：**每连接**单调递增（原进程级全局已废弃）。
- **订阅**：`?session_id=` 只收该会话的 `arena.*` + 全局 `job.progress`；未提供者只收 `job.progress` / `sys.*`。
- **心跳/重连**：服务端不发心跳；客户端负责断线重连并重新订阅（服务端不保存订阅）。

## 6. Seed Manager
统一设置：
- Python random
- NumPy
- PyTorch CPU
- PyTorch CUDA

mutation / crossover / development / Arena spawn 全部由 master seed 派生。

## 7. Offline
现场不得依赖：
- OpenAI API
- external model API
- remote DB
- remote asset CDN

## 8. Docker（押后）
当前以 `uv sync` + 版本清单（`frontend/README.md`）复现；Docker 作为外部机器复现的 P1 项，待有需求再补。现场优先直接本机运行。

## 9. One-click Demo
```bash
make demo          # 等价于 ./scripts/start_demo.sh
```

构建前端（若 `frontend/dist` 缺失）并启动服务，浏览器打开 `http://127.0.0.1:8000`。

**端口 / CORS / 托管约定（对齐已交付前端）**：
- **生产（`make demo`）**：由 FastAPI **单 worker** 托管 `frontend/dist`（同源，免 CORS）；固定端口 `8000`。
- **开发**：`npm run dev` 起 vite `5173`，经 `vite.config.ts` 的 proxy 把 `/v1 → http://127.0.0.1:8000`（dev 期同源 `/v1`）。
- **单 worker 为硬约束**：会话为纯内存（`API接口.md §7.1`），多 worker 会使同一 `session_id` 落到不同进程而随机 `404`（单 worker ≠ 单线程，会话内已加锁）。
- **可覆盖参数**：`scripts/serve_api.py` 支持 `--host`（默认 `127.0.0.1`）/ `--port`（默认 `8000`）/ `--reload`；`scripts/start_demo.sh` 尊重环境变量 `EVOGENESIS_PORT`。

## 10. Git
开发期 private；提交时按比赛要求 public。schema/config 变更必须双方同步。

## 阅读问题（2026-09-27 核对）

> 首版列 10 条未定义点；本轮逐条对照实现与上游文档核对，**9 条已闭合**，1 条为已知限制。

| # | 问题 | 现状 |
|---|---|---|
| 1 | 稳定 ID 规则 / 唯一性域 | **已闭合**：格式、派生与唯一性域 owner 移至 `core/核心机制与数据流.md §3.1`（实现 `core/ids.py::mint_id`，`<exp>:g<gen>:<role><index>`，确定性纯函数，实验内唯一）；本文件 §3 仅列名。 |
| 2 | 资源词表与端点不闭合 | **已澄清**：`§4.2` 词表为规划用语、非端点承诺；已有端点者见 `§4.3`，无消费者的资源（`phenotypes` / `connectomes` / `generations` / `events` / `metrics`）按需再引入、不预建。 |
| 3 | 同步 / 异步边界与超时 | **已闭合**：编辑 / 发育 / 繁殖为**同步**（进程内 CPU、即时返回，无超时逻辑）；演化 / 环境选择为**异步**（`202` + `job_id`，后台线程 + `job.progress`），`evolutions` 复用该异步路径。 |
| 4 | 暂停缺恢复端点 | **已闭合**：`pause` 定为 toggle（§4.3）。 |
| 5 | WS 词表 / `seq` / 多订阅 / 重连 | **已闭合**：完整 `type` 词表与语义见 §5 与 `API接口.md §3`（`sys.hello` / `sys.error` + `arena.*` + `job.progress` + `brain.activation`）；`seq` 为**每连接**单调；多订阅按 `?session_id=`；心跳 / 重连属客户端（前端）。 |
| 6 | Seed 派生树 | **已闭合**：由 `core §3` 的 `SeedManager` 命名空间统一派生（Python / NumPy / Torch CPU / CUDA）；Arena 例外经 `pipeline::arena_seeds_for` 传整数子种子（`core §3` 例外条款）。 |
| 7 | CUDA 逐位确定性 | **未闭合（已知限制）**：`core/seed.py` 已设 `torch.cuda.manual_seed_all`，但**未**强制 `cudnn.deterministic` / 确定性算子 ⇒ GPU 结果不保证逐位可复现；复现以固定 device 为准（`core §3`）。 |
| 8 | 结构映射表不完整 | **已闭合**：§2 已补 `core` / `evolution` / `learning` / `experiment` / `viz` 行。 |
| 9 | Offline 前端检查项 | **已闭合**：检查项归 `frontend/README.md`（字体 / 图标 / 资产本地打包），本文件 §7 只定红线。 |
| 10 | CI 与 Demo 端口 / CORS | **已闭合**：CI 门禁 `make lint && make test`（`AGENTS.md`）；`make demo` = 8000、dev vite 5173 代理 `/v1`、生产 FastAPI 托管 `frontend/dist` 免 CORS（§9 / §10）。 |
