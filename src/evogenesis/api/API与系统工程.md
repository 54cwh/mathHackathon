# 系统工程与接口规范

> **实现状态（2026-09-26）**：`api/` 下的 Python 实现（`app.py` / `schemas.py` / `session.py` / `stubs.py` / `ws.py`）已移除，待重写；本文档保留为契约草案，其中引用的模块路径在重写前不成立。

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
| `/simulation` | `src/evogenesis/arena/` |
| `/experiments` | `configs/` + `scripts/` + `results/runs/` |
| `/assets` | `artifacts/`（+ `data/`） |
| `/checkpoints` | 冻结→`artifacts/`；实验→`results/runs/<id>/` |
| `/demo` | `frontend/` + `scripts/start_demo.*` |
| `/config` | `configs/` |
| `/docs` `/prompts` `/schemas` | 同名保留 |

目录职责与 `AGENTS.md` 的「项目目录结构」一致。

## 3. 稳定 ID

> **owner 已移出本文件**：`fish_id` / `genome_id` / `generation` / `experiment_id` / `environment_id` 的格式、派生与唯一性域归 `core/核心机制与数据流.md` §3.1（实现 `core/ids.py`）。本表仅列名。

- fish_id
- genome_id
- generation
- experiment_id
- environment_id

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
`sessions`、`genomes`、`mutations`、`developments`、`phenotypes`、`connectomes`、`breedings`、`fish`、`evolutions`、`generations`、`experiments`、`jobs`、`events`、`metrics`、`leaderboard`、`story-mutations`。

### 4.3 端点（草案）
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/v1/sessions` | 创建会话，返回 `session_id` |
| GET | `/v1/sessions/{session_id}` | 会话摘要：代 / 环境 / 种群 / 运行态 |
| POST | `/v1/sessions/{session_id}/reset` | 重置会话 |
| DELETE | `/v1/sessions/{session_id}` | 结束会话 |
| GET | `/v1/story-mutations` | 预验证 SNP 列表 |
| POST | `/v1/genomes/{genome_id}/mutations` | base 编辑，返回新 `genome_id` + diff |
| POST | `/v1/developments` | 发育，返回 `dev_trace` + phenotype |
| POST | `/v1/breedings` | 繁殖，返回 offspring + meiosis trace |
| GET | `/v1/sessions/{session_id}/fish/{fish_id}` | Fish Card |
| POST | `/v1/sessions/{session_id}/release` | 释放鱼进入 Arena |
| POST | `/v1/sessions/{session_id}/pause` | 暂停仿真 |
| GET | `/v1/sessions/{session_id}/snapshot` | 全场快照：fish（transforms + energy）+ prey / predators / obstacles + events |
| POST | `/v1/sessions/{session_id}/evolutions` | 演化，`202` + `job_id` |
| GET | `/v1/sessions/{session_id}/leaderboard` | 排行榜 |
| POST | `/v1/experiments` | 启动正式实验，`202` + `job_id` |
| GET | `/v1/experiments` | 实验列表（分页） |
| GET | `/v1/experiments/{experiment_id}` | 实验元数据 + 指标 |
| GET | `/v1/jobs/{job_id}` | 任务状态 / 进度 |
| POST | `/v1/jobs/{job_id}/cancel` | 取消任务 |

编辑 / 发育 / 繁殖为同步；演化与正式实验为异步 job，进度经 WS `job.progress` 推送。

## 5. WebSocket
端点 `/v1/ws`；消息信封与命名见 §4.1 R11。

实时传：
- fish transforms
- selected-fish neural activation
- energy
- events
- generation progress

不每帧发送全部 48×48 matrix。

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

## 10. Git
开发期 private；提交时按比赛要求 public。schema/config 变更必须双方同步。

## 阅读问题（待确认）

> 逐份阅读本文时发现的未定义点，需与 `AGENTS.md` / `frontend/README.md` / `schemas/` 及既有实现对齐后确认。

1. **稳定 ID 的生成规则与唯一性范围未定义（§3）**：`fish_id / genome_id / generation / experiment_id / environment_id` 的格式、派生方式（哈希 / 单调计数）、唯一性范围（会话内 / 全局）均未写。前端“不得用数组下标”已有约束，但后端如何保证稳定未定。
2. **资源词表与端点不闭合（§4.2 / §4.3）**：词表列 16 个资源，端点仅覆盖约一半；`phenotypes / connectomes / generations / events / metrics` 无任何端点或获取途径。
3. **同步 / 异步边界与超时未定义（§4.3）**：仅声明“编辑/发育/繁殖同步、演化/实验异步”；未给同步操作的最长时限、超时行为，以及 48 个体演化是否必然异步。
4. **暂停缺恢复端点（§4.3）**：`POST /v1/sessions/{session_id}/pause` 没有对应的 `resume / play` 端点。
5. **WS 消息类型词表不完整 + 语义缺失（§4.1 R11 / §5）**：R11 只举例四类，§5 还要传 energy / events / generation progress，但未给完整 `type` 词表；`seq` 的作用（排序 / 去重 / 断线补偿）、多客户端订阅、心跳与重连策略均未写。
6. **Seed 派生方法未定义（§6）**：master seed 如何派生成各子 seed（`SeedSequence.spawn` / hash）未写；mutation / crossover / development / Arena spawn 的派生树未给。
7. **CUDA 确定性未定义（§6）**：设置 `torch.cuda` seed 之后是否强制 `cudnn.deterministic`、是否接受非确定性算子未写。
8. **结构映射表不完整（§2）**：任务层中的 `core / evolution / learning / experiment / viz` 未出现在映射表里。
9. **Offline 缺前端侧检查项（§7）**：禁止远程 CDN，但未写前端字体 / 图标 / 资产必须本地打包的检查项（对应 `frontend/README.md` 的离线要求）。
10. **CI 与 Demo 端口/CORS 未写（§9 / §10）**：未提 CI 门禁（`make lint && make test`）；`make demo` 的固定端口、dev 5173 代理、生产由 FastAPI 托管 `frontend/dist` 免 CORS 等约定未写。
