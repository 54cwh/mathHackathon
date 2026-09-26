# 前端驱动的 API 实现清单（含"不需要什么"的审计）

**本文角色**：**需求方清单** —— 只写「前端实际需要什么、以及明确不需要什么」，供服务层实现与验收。
**不是** `api/API接口.md` 的替代：端点 **owner 仍是 `api/`**（`AGENTS.md:129`「API 端点 → `api/API接口.md`」）。
出入时**以「前端实际调用面」为准** —— 前端是**已发布的客户端**（29 文件入库、`dist` 可构建），
改它等于作废契约；改服务层不动任何已交付物。

**证据**：`research/notes/前端对接需求清单.md`（逐行测全调用面）为底，本文只做**取舍与分级**。
响应字段真值是 `frontend/src/api/arena.ts` 的 TS 类型（`SessionSummary` / `ArenaSnapshot`…），
本文引用**类型名**而不复制字段表，避免两处漂移。

> **准入标准只有一条**：出现在 `arena.ts` / `ws.ts` 的**真实调用面**，
> 或**冻结设计文档里已定字段**的对应端点。不满足者一律进 §4（不做）。

---

## §1 Demo 必需（4 条）—— 缺任一条，Arena 面板点不动

| # | Method + Path | 请求 | 响应 | 前端消费 |
|---|---|---|---|---|
| 1 | `POST /v1/sessions` | body `{master_seed, environment}` | `201` `SessionSummary` | **只消费 `session_id`** |
| 2 | `DELETE /v1/sessions/{session_id}` | — | **`204` 无响应体** | 卸载 / Reset 时清理 |
| 3 | `POST /v1/sessions/{session_id}/release?steps=1&use_expert=true` | **query 参数（非 body）** | `SessionSummary` | `generation`/`population`/`fish_alive`/`prey_remaining`/`master_seed` |
| 4 | `GET /v1/sessions/{session_id}/snapshot` | — | `ArenaSnapshot` | 渲染硬依赖：`obstacles[].{x,y,radius}`、`prey.{x,y,size,alive}`、`predators.{x,y,size}`、`fish.{x,y,heading,energy,size,alive}`、`step` |

稳态请求面**只有 2 类**：`release` + `snapshot`，每 tick 各 1 次（自调度，`POLL_MS=100`）。
`201` 与 `204` 的取值见 `api/API接口.md` §1.1 / §1.4。

## §2 契约必需（2 条）—— 前端已定义但暂未调用

| # | Method + Path |
|---|---|
| 5 | `GET /v1/sessions/{session_id}` |
| 6 | `POST /v1/sessions/{session_id}/reset` |

**为什么仍必需**：二者在 `arena.ts` 中**已导出**（`getSession` / `resetSession`），只是面板当前未用
（面板走 **delete + create** 做 Reset）。服务层若缺，`arena.ts` 立刻留下 **404 死代码**；
成本极低（`reset` 可复用建会话的实现），应当一并提供。

> **§1(4) + §2(2) = 6，恰好等于 `arena.ts` 导出的 6 个 REST 函数**（`createSession` / `getSession` /
> `resetSession` / `deleteSession` / `release` / `getSnapshot`）—— **不多不少，这是本清单的硬边界**。

## §3 本轮**不做**，但请设计会话状态时预留（2 条）

| # | Method + Path | 对应设计 | 为何本轮不做 |
|---|---|---|---|
| 7 | `GET /v1/sessions/{session_id}/fish/{fish_id}` | `交互与可视化.md` §6 **Fish Card**（13 字段） | 前端**没有** Fish Card 面板（`DanioArenaPanel` 点选鱼只高亮），`arena.ts` 也**没有**该函数 ⇒ 现在实现无人调用。**但要预留**：`snapshot` **不含** genotype / cell composition / edges / fitness / captures / escapes，卡片**无法**只靠 snapshot 渲染，服务层需能从会话取到这些量 |
| 8 | `GET /v1/sessions/{session_id}/leaderboard` | §9 **排行榜**（5 项） | 面板未做。且 §9 的「最异常基因组 / 连接组变化最大」**尚无度量定义**（`交互与可视化.md` 阅读问题 5）⇒ **先定度量再定接口** |

## §4 审计结论：**不要实现**

| 端点 | 结论 | 依据 |
|---|---|---|
| `POST /v1/sessions/{id}/pause` | **不需要** | 前端 Pause **只停自身轮询、不调后端**：`frontend/README.md:116`「后端也提供 `…/pause`，前端同样未调用 —— 底部的 Pause 只是停掉前端轮询」；`arena.ts` **无 pause 导出**。<br>⚠️ **别被 `frontend/README.md:173` 误导**：那份 **9 端点清单是「历史（2026-09-26 起失效）」**、原文带删除线，记录的是**旧后端曾有什么**，**不是需求**。|
| `GET /v1/health` | **可选，非必需** | 前端不调用。仅 `make demo` 起服自检可用 —— 那是给**启动脚本**的，不是给前端的 |
| 模型/实验 **10 个 501 stub**（`/v1/story-mutations`、`/v1/genomes/{id}/mutations`、`/v1/developments`、`/v1/breedings`、`/v1/sessions/{id}/evolutions`、`/v1/experiments`(POST/GET)、`/v1/experiments/{id}`、`/v1/jobs/{id}`、`/v1/jobs/{id}/cancel`） | **本轮不实现** | 与 Arena Demo 无关；只在 §3（Mutation）/§4（发育）/§11（CRISPR）等**模型侧面板**才需要。**重写服务层时不要顺手把它们从 501 变成实现** —— 那是另一个任务 |

## §5 阻塞：契约未定，**先别实现**

| 端点 | 阻塞原因 |
|---|---|
| WebSocket `/v1/ws` | 信封契约**已存在**（`ws.ts` 的 `WsEnvelope {v,type,seq,ts,payload}`、路径 `/v1/ws`、`type` 为点分层），但 `交互与可视化.md` **阅读问题 8** 明写：§7「实时神经活动」的**数据来源与采样率未定义**，未与 `API与系统工程.md` §5 的推送清单对接。`ws.ts` 当前**全仓无人 import**（走 REST 轮询）⇒ **payload 未定就实现 WS，等于赌一个会被推翻的契约**。先定采样率与推送清单，再实现。 |

## §6 归属：**需你二人确认**（本清单无法单方面决定）

- `AGENTS.md` **不按人归属 `api/`**：只规定「API 端点 → `api/API接口.md`」（L129）与
  「`api/` 实现层已移除、待重写」（L14/42/73/75/95）。
- **唯一人名归属在 `api/API接口.md §6`**：Arena 10 条（functional）记 **李辰钊**、
  模型/实验 10 条（501 stub）记 **池伟豪**。
- 用户 2026-09-26 的安排是「**池伟豪写 api**」。
- ⚠️ **二者不一致**：按 §6 的记法，§1/§2 这 6 条（**正是 Demo 必需的**）**原本是李辰钊的**；
  按用户安排则归池伟豪。**请确认后回写本节**，否则改 `session.py` 会踩跨 lane。

## §7 实现时必须保住的不变量（破坏了前端会坏，且不是"小问题"）

1. **`frontend/**` 0 改动** —— 前端即契约；不一致时改服务层。
2. **`204` 必须真的无响应体**：`req()` 对 `204` 有特判，返回体非空会解析失败。
3. **`release` 的 `steps` / `use_expert` 是 query 参数**，不是 body。
4. **坐标系**：世界 `100×60` ↔ 位图 `640×384` 同比例映射（`sx/sy/sr`）；改世界尺寸会拉伸画布。
5. **错误体 RFC 7807**，前端取 `body.detail` 作错误文案（`API接口.md` §4；`arena.ts` 的 `req()`）。
6. **字段命名 `snake_case`**：`frontend/README.md:53`（约定 5「TS 类型对齐 `schemas/`」）+
   `frontend/README.md:161`（REST 命名规范见 `api/API与系统工程.md §4`：`/v1`、资源式）。
7. **不要重复实现前端已实现的降级语义**：错误即停循环、自调度轮询、Reset=delete+create、
   Pause 不动后端 —— 这些都在前端，服务层再做一套会两套语义打架。
8. ⚠️ **不要把 `environment` 当「环境切换」来实现 —— 它现在改了也没用**：
   - `API接口.md §7.2`（对**已被移除的那个实现**的实测）记：`food_rich` / `predator_rich` /
     `resource_scarce` 三档行为**完全一致**，该字段**仅存储回显**；
   - `arena` §12 / 交接表 **D5（环境三组 M4）** 独立记载同一事实：「`environment` 字段
     **不改变任何参数**，「环境选择」尚无实际因果」。
   ⇒ **两处同源，该结论在当前同样成立**：环境对照要真做，得先做**场景布置**（`arena` §12），
   不是接这个字段。
   另：`arena_config_path` / `model_config_path` 在旧实现里**完全不读**（`Session.__init__` 不读
   config 文件；该实现已移除，故当前无实现可读）。新实现**应明确二者是否生效** ——
   `API接口.md §7.2` 称之为「留给后续接入的占位契约」，一旦生效即成为对外契约的一部分
   （改字段集须双方同步）。
9. **`make demo` 承诺必须兑现**：`api/API与系统工程.md:133` 写「等价于 `./scripts/start_demo.sh`，
   浏览器开 `http://127.0.0.1:8000`」，而现 `Makefile` **无 `demo` 目标** ⇒ 文档与实现须收敛到同一事实。
   另 `API与系统工程.md:154` 自认「生产由 FastAPI 托管 `frontend/dist` 免 CORS」**尚未写进文档**，建议一并补。

---

## 附：本清单的审计记录（说明"为什么只有这么几条"）

1. **准入只用「真实调用面」**：以 `arena.ts` 的 6 个导出函数为硬边界。
   设计里提到但无代码承载的（§3 两条）单列，**不混进 §1**。
2. **逐条对照 `api/API接口.md §6` 的 20 条**，把前端不用的全部归 §4（pause / health / 10 stub），
   防"顺手全实现"。
3. **专门核查了两处"看起来该有、实际不该有"的诱饵**：
   - `frontend/README.md:173` 的 9 端点清单**含 `/pause`**，但该段**自标为历史已失效** ⇒ 不作需求依据；
   - `arena.ts` **导出了 `resetSession` 但面板不用** ⇒ 归 §2（契约）而非 §4（不做），
     因为这属于**已发布客户端 API**，删了会留死代码。
4. **契约未定的一律归 §5 并明确"禁止现在实现"**，而不是给一个我会赌错的接口。
5. **实现期陷阱单列 §7**（204 / query 参数 / 坐标系 / `environment` 无效果 / 降级语义重复），
   这些是"照着文档实现却仍然坏掉"的高频原因。
