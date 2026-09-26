# EvoGenesis 前端

演示 UI：实时渲染 Danio Arena、交互式 DNA 编辑、脑网络与演化 dashboard。后端为 Python 权威仿真，前端只负责**渲染 + 交互**，不重写物理/动力学。

## 技术栈（版本已锁定）

> 规则：`package.json` 写**精确版本**（不用 `^`/`~`），提交 `package-lock.json`。升级须显式改版本并重测。

| 类别 | 依赖 | 版本 |
|---|---|---|
| 运行时 | Node（nvm LTS） | 22.23.3 |
| 包管理 | npm（随 Node） | 10.9.9 |
| 构建 | vite | 5.4.21 |
| 构建 | @vitejs/plugin-react | 4.7.0 |
| 框架 | react / react-dom | 18.3.1 |
| 类型 | typescript | 5.9.3 |
| 类型 | @types/react / @types/react-dom | 18.3.31 / 18.3.7 |
| 样式 | tailwindcss | 3.4.19 |
| 样式 | postcss / autoprefixer | 8.5.28 / 10.6.1 |
| 样式 | tailwindcss-animate | 1.0.7 |
| 样式 | class-variance-authority | 0.7.1 |
| 样式 | clsx / tailwind-merge | 2.1.1 / 2.6.1 |
| 图标 | lucide-react | 1.48.0 |
| 状态 | zustand | 4.5.7 |
| 图表 | echarts | 5.6.0 |
| 脑图 | cytoscape | 3.34.3 |
| 3D | three | 0.186.1 |
| 3D | @react-three/fiber | 8.18.0 |
| 3D | @react-three/drei | 9.122.0 |

- **组件层**：shadcn/ui。它不是 npm 包，组件源码落在 `src/components/ui/`，用 CLI 添加（`npx shadcn@latest add <name>`）。
- **Arena 渲染**：原生 **Canvas 2D**（不用 WebGL/PixiJS）。
- **实时传输**：原生 `WebSocket` + `fetch`，不引 HTTP 客户端库。
- **3D DNA**：**改由 three.js / @react-three/fiber（r3f）渲染**。
  > **2026-09-26 反转记录（辰钊决定）**：本条原写「CSS/SVG 动画（three.js 不做，移至 P1）」，
  > 现改为采用 three.js。**理由**：3D 双螺旋承担 `交互与可视化.md` §2 的视觉冲击，
  > CSS/SVG 难以做出可信的立体与光照；像素风的质感可通过「程序化几何 + 生成的贴图」调和。
  > **约束（一处必须先知道的兼容性）**：本项目锁 **React 18.3.1**，而 **r3f v9 要求 React 19**，
  > 故只能上 **r3f v8.x**（与 React 18 配套）；three 本体版本随 r3f v8 的 peer 约束选。
  > **本反转须按本文件顶部「升级须显式改版本并重测」的规则执行**：
  > 新依赖写入 `package.json`（精确版本）+ 更新 `package-lock.json` + 重测构建与 lint。
  > **不冲突**：下方「Arena 渲染：原生 Canvas 2D（不用 WebGL/PixiJS）」仍然有效 ——
  > 那条约束**只针对 Arena 面板**；WebGL 仅出现在 DNA2Brain 面板。
  > **配套**：ChatGPT 生成的 DNA 素材在本方案下作为**贴图/背景**使用（不是直接当螺旋位图），
  > 因此素材要求为「可平铺的 DNA 纹理 / 碱基符号」而非「螺旋成品图」。
  > **⚠️ 2026-09-26 推迟（用户裁决，见 `交互与可视化.md` §15.1）**：本轮起**暂不引入 three.js**。
  > DNA 视觉改用 **Canvas 像素风**（`src/visuals/DnaHelixVisual.tsx`），理由是项目定位为
  > pixel-art + scientific UI hybrid，PBR / glossy 不属于这套视觉语言。
  > **本条不是删除，是推迟**：`three` / `r3f` 的依赖仍在 `package.json` 里，若将来要做真正的
  > 3D 螺旋再启用本条；届时须按本文件顶部「升级须显式改版本并重测」执行。

## 防坑约定（AI 协作）

1. **不装训练语料外的库**；改 UI 时先读 `src/components/ui/` 里的**本地 shadcn 源码**，按真实 props 写，不凭记忆。
2. **不引 CDN**：字体、图标、资源全部本地打包（现场离线）。
3. **20Hz 热路径不走 React**：Arena 用 `requestAnimationFrame` + Canvas2D，状态放 `useRef`；zustand 只存低频摘要（选中鱼、代、指标），避免每帧 setState。
4. **配置只由官方模板生成**：`vite`/`tsconfig`/`tailwind`/`postcss` 配置不手写，用 `npm create vite@5` + shadcn CLI 产出后再改。
5. **契约同源**：TS 类型对齐 `schemas/`（JSON 字段一律 `snake_case`）。
6. **颜色与圆角走检查**：`npm run lint:design`（`scripts/lint-design.mjs`，**只读**，不改任何文件）。
   硬规则：hex 只允许出现在 `src/design/palette.ts`；禁止 `rounded*`；`--radius` 必须为 `0`；
   色板 `BRAND` 必须恰好 24 项且不含洋红 `#FF00FF`（抠图键控色）；禁阴影 / 模糊 / glass /
   渐变 / opacity 淡出 / `transition` 颜色插值 / 动画 / 颜色透明后缀（`bg-x/50`）。
   另含 **token 漂移守卫**：`index.css` 的生成块必须等于 `src/design/tokens.ts` 的输出
   （不一致就跑 `npm run gen:design`）。
7. **改了后端必须重启 API 进程**：`uvicorn`/`serve_api.py` 只在启动时加载代码；旧进程对**新加的查询参数
   会静默忽略**（FastAPI 不报错），表现为"前端参数发出去了、后端毫无反应"——2026-09-27 实际踩过
   （Manual Control 的 `fish_id/omega/speed`）。本项目已有两道防线：① `/v1/health` 的能力位
   （如 `manual_control`），前端据此提示"后端版本落后"；② 排查时先确认端口上的进程是刚启动的
   （`lsof -ti:8000` 会同时列出持有代理连接的 vite，杀进程要按 `ps` 的 args 过滤，别连带杀掉 dev server）。
   **⚠️ 注释与键名同样会泄漏（实测过三类）**：Tailwind 扫的是**原始文本**（不剥注释），
   凡与工具类同名的**小写单词**都会被切成候选并生成「没人用」的死 CSS —— 命中过
   `DNA.shadow`（属性访问）、`tokens.ts` 的 shell token 键 `ring:`（对象键）、以及英文注释里的
   `rounded to…`。静态检查抓不到这类（它剥注释、也不把属性访问当类名），兜底是
   `tailwind.config.ts` 的 **`blocklist`**。**起键名 / 写注释时别用** shadow、blur、rounded、
   ring、transition、animate 这几个词。
   **两人并行时这是唯一能自动兜住「各改一版颜色」的闸门** —— 提交前必跑。

## 目录规划

> 下图是与 `find frontend/src -type f` 实测一致的**真实结构**。标注 `已存在` 的是当前分支上确有的文件；标注 `规划中` 的是既定方案但**尚未创建**，不要按它写代码。

```text
frontend/
├─ .nvmrc  .gitignore                  # .nvmrc = 22
├─ index.html  README.md
├─ package.json  package-lock.json
├─ vite.config.ts  tsconfig.json  tsconfig.app.json  tsconfig.node.json
├─ eslint.config.js
├─ tailwind.config.ts  postcss.config.js  components.json
├─ types.ts                            # 已存在：手写契约类型（Base / ChromosomePair /
│                                      #   DiploidGenome / CellType / FishSummary /
│                                      #   MutationRequest / MotorAction）—— 非 schemas 生成
├─ public/
│  └─ vite.svg                         # 已存在：仅 Vite 默认图标
│     （public/fonts/ 自托管字体 —— 规划中）
├─ dist/                               # vite build 产物（不入库）
└─ src/
   ├─ main.tsx  App.tsx  index.css  vite-env.d.ts      # 已存在
   ├─ components/
   │  └─ panel.tsx                     # 已存在：自写 Panel 外壳（title/icon/className/children）
   │     （components/ui/ = shadcn 组件源码目录 —— 规划中，尚未建立）
   ├─ panels/
   │  ├─ DNA2BrainPanel.tsx            # 已存在：占位面板（骨架提交 809f860）
   │  ├─ BrainForgePanel.tsx           # 已存在：占位面板（骨架提交 809f860）
   │  └─ DanioArenaPanel.tsx           # 已存在：已接实时会话（cfb3869）
   │     （EvolutionDashboard / FishCard / MendelMode / CompareFish —— 规划中）
   ├─ api/
   │  ├─ arena.ts                      # 已存在：唯一 REST 客户端，并导出 MASTER_SEED
   │  └─ ws.ts                         # 已存在：WsEnvelope + connectWs()
   │     （没有 rest.ts；类型不是 schemas 生成，而是手写在 types.ts 与各 api 模块内 ——
   │       arena.ts 自带 SessionSummary/ArenaSnapshot/FishState/PreyState/PredatorState/
   │       ObstacleState/ArenaEvent，ws.ts 自带 WsEnvelope）
   ├─ lib/
   │  └─ utils.ts                      # 已存在：cn() = twMerge(clsx(...))
   └─ store/
      └─ ui.ts                         # 已存在：zustand（running / sessionId /
                                       #   selectedFishId / resetNonce / stats）
```

**未落地的规划目录**：`src/components/ui/`（shadcn 组件源码）、`src/theme/`、`src/hooks/`、`public/fonts/`。其中 shadcn/ui 仍是既定组件层方案（`components.json` 已配好 `"ui": "@/components/ui"` 别名，可直接 `npx shadcn@latest add <name>`），但**组件源码目录尚未建立，当前 `src/components/` 下只有自写的 `panel.tsx`**；主题也不是独立的 `theme/` 目录，而是 `src/index.css`（CSS 变量）+ `tailwind.config.ts`。

## Live Demo 种子与 Arena 面板实时行为

> 本节记录 `cfb3869`（Arena 面板接入实时会话）的实际行为，作为前端唯一的种子与轮询说明；与 `src/evogenesis/arena/Danio_Arena设计与实现说明.md` 的机制定义配合阅读。

### 种子来源（单一入口）

- `src/api/arena.ts` 导出的 `MASTER_SEED = 250927` 是整个 Live Demo 的**唯一种子来源** —— 前端只此一处硬编码种子，任何面板都不得自带种子。
- 该值必须与后端 Demo 种子 `configs/demo_seed.yaml`（`master_seed: 250927`）一致。
- 三种种子用途**互相隔离**，不得混用：
  - Live Demo：`250927`（本前端 + `configs/demo_seed.yaml`）
  - 正式实验：`1103 / 2207 / 3301`（`configs/experiment_seeds.yaml`）
  - 契约示例：`20260925`（`schemas/examples/README.md`）

### 会话生命周期

- `DanioArenaPanel` 挂载时调用一次 `createSession(MASTER_SEED)`（默认 `environment="food_rich"`），全程**恰好一个**活跃会话，id 存入 `store/ui.ts` 的 `sessionId`。
- `resetNonce` 变化（点底部 Reset → `bumpReset()`，同时清空 `selectedFishId`）与组件卸载都会 `deleteSession(旧 id)` 并 `setSessionId(null)`；创建过程中若已卸载，则把刚建出的会话直接删掉。这样**轮询循环不可能打到已删除的会话**。
- 注意：前端走的是 **delete + create**（不是 `POST /sessions/{id}/reset`）；`arena.ts` 仍导出 `resetSession()`，但面板当前未使用。后端也提供 `POST /v1/sessions/{id}/pause`，前端同样未调用 —— 底部的 Pause 只是停掉前端轮询。

### 轮询与请求面

- `running && sessionId` 时，每 tick 发 **1 次 `release(steps=1)` + 1 次 `getSnapshot()`**；`release` 默认 `use_expert=true`，故请求实际携带 `use_expert=true`。
- 用**自调度的 `setTimeout`**（不是 `setInterval`）：后端变慢时下一次 tick 顺延，而不会堆叠并发请求。`POLL_MS = 100` → 渲染 10 fps，后端仿真 20 Hz。
- 稳态请求面**只有 `release` 与 `snapshot` 两类**（另加创建、删除各一次）。
- 后端报错时立即停止轮询、`setRunning(false)`、把错误显示在面板底部，需用户重新点 Release 才会继续。

### 渲染（Canvas 2D）

- 位图固定 `640×384`，世界 `100×60`，所有坐标经 `sx/sy/sr` **同比例**映射 —— **不得非等比拉伸**，否则鱼会被纵向压扁。
- 配色：背景 `#0B1220`；障碍灰 `#374151`；猎物绿 `#34D399`；捕食者红 `#F87171`；鱼蓝 `#60A5FA`；**选中鱼黄 `#FBBF24` 并叠加外圈能量环**（`energy > 0.3` 绿 `#34D399`，否则红 `#F87171`）。
- 左下角绘制当前 `step`。

### 交互与头部统计

- 点击画布选中最近的鱼（画布坐标距离阈值 **20 px**，经 `getBoundingClientRect()` 换算），点空白处取消选中。
- 头部统计栏（`App.tsx`）的 Generation / Fish / Prey / Step / Seed 由 `store/ui.ts` 的 `stats` 驱动，而 `stats` 每 tick 由**后端会话摘要**（`generation / population / fish_alive / prey_remaining / master_seed`）与 snapshot 的 `step` 写入，**不是前端自算**。
- `Env` 取 `SessionSummary.environment`（经 `store.stats.environment`）；顶栏数值全部来自真实会话摘要，未起会话时显示 `—`。顶栏另有后端健康指示（`GET /v1/health`，10s 轮询）。

### 本机实测记录

2026-09-25，浏览器（后端本地起服）：头部统计由后端会话摘要驱动；点击选鱼正确渲染能量环；稳态下仅 `release` / `snapshot` 两类请求，且**零控制台错误**。

## 主题 token（暗色"实验室"风）

> **本表是镜像，不是 owner**（2026-09-26 起，Q2(c)/Q3 决策）。两份真实 owner：
> - **外壳 token**（下表前 10 行）= `src/index.css` 的 `:root`；
> - **品牌 24 色** = `src/design/palette.ts`（唯一数据源）。
>
> 本表与代码不一致时**以代码为准**，并把本表改回来 —— `npm run lint:design` 会抓
> hex 越界、圆角残留、破坏像素硬度的手段、色板项数，以及 `index.css` 与
> `src/design/tokens.ts` 的 token 漂移（规则见 `scripts/lint-design.mjs` 的 `RULES` / `CSS_RULES`）。
> 品牌色的 Tailwind 用法是 **`brand` 命名空间**：`bg-brand-ink` / `text-brand-foam` /
> `border-brand-stone-shadow`（不是 `bg-ink` —— 那是**错的**，Tailwind 会静默不生成）。

| 语义 | 值 |
|---|---|
| `bg` 背景 | `#0B0F14` |
| `panel` 面板 | `#111823` |
| `border` 边框 | `#1F2A37` |
| `text` 主文字 | `#E6EDF3` |
| `muted` 次文字 | `#8B98A9` |
| `accent` 调控/主色 | `#22D3EE` |
| `accent2` 次色 | `#A78BFA` |
| `success` | `#34D399` |
| `warn` | `#FBBF24` |
| `danger` | `#F87171` |
| 圆角 | `0` —— `R2-4 无圆角`；原 `10px` **已废止**（该值同时被 `index.css` 的 `--radius` 与 `tailwind.config.ts` 的 `borderRadius` 硬零化） |

### 字体（Q4(b)，2026-09-26 落地）

全部**自托管**于 `public/fonts/`（现场离线；见下方防坑约定 2「不引 CDN」）。
文件由 `scripts/fetch-fonts.mjs` 下载、并生成 `src/design/fonts.css`；`index.css` 顶部 `@import` 它。

| 用途 | 字体 | 落地文件 |
|---|---|---|
| 正文 | Inter | `public/fonts/inter-latin.woff2` |
| 数值 / 代码 | JetBrains Mono | `public/fonts/jetbrains-mono-latin.woff2` |
| **英文标签与标题** | Press Start 2P（像素，OFL） | `public/fonts/press-start-2p-latin.woff2` |
| 中文叙述 | 系统字体 | —（像素字体不覆盖 CJK，**不要**给中文套像素字体） |

用法：像素字体只加在**英文**标签/标题上，类名 `font-pixel`（定义在 `src/index.css` 的
`@layer utilities`，它同时关掉抗锯齿）。数值走 `font-mono`。
**许可登记**：Press Start 2P 等第三方字体须登记 `docs/declaration/THIRD_PARTY.md`（`docs/` 归池伟豪）。

## 与后端的接口

- REST 命名规范与端点见 `api/API与系统工程.md §4`（`/v1`、资源式、JSON `snake_case`）。
- 实时流走 `/v1/ws`，消息信封 `{v,type,seq,ts,payload}`，`type` 为点分层（`arena.fish_state` 等）。

### 实现现状（2026-09-25）
> ⚠️ **2026-09-26 状态变更（本节以下内容部分失效）**：用户决定**移除对外服务层**（`d894cbb` 删除 `src/evogenesis/api/{app,schemas,session,stubs,ws}.py` 与 `tests/test_api_contract.py`）。
> 因此「N 个端点已 functional / 其余为 501 占位 / WS 为 MVP 回显」这些**实现状态描述已不再成立**，仅作为**前端契约设计的历史参照**保留；后端需按 `api/API与系统工程.md` 重写。
> 前端 `src/api/arena.ts` / `ws.ts` 的**调用契约本身不变**（资源式 `/v1` 路径、`{v,type,seq,ts,payload}` 信封、错误体取 `body.detail`）——待后端重写后应能直接复用。


- **REST 客户端就是 `src/api/arena.ts`（唯一）**，没有 `rest.ts`。内部统一的 `req()`：失败时抛 `detail`（取后端 body 的 `detail` 字段）或 `HTTP <status>`；**对 204 无响应体返回 `void`**，专门适配 `DELETE /v1/sessions/{id}`。
- **WS 客户端 `src/api/ws.ts`**：`connectWs()` 按当前页面协议自动选 `ws` / `wss`（`location.protocol === "https:"` → `wss`），默认路径 `/v1/ws`；信封类型为 `WsEnvelope<T> { v: 1; type: string; seq: number; ts: number; payload: T }`。
- **端点实现状态（历史；2026-09-26 起失效）**：~~Arena / session 侧 9 个端点已 functional（`src/evogenesis/api/session.py`）~~ —— 该实现层已按用户决定移除，见上方状态变更。当时的清单：
  `POST /v1/sessions`、`GET /v1/sessions/{id}`、`POST /v1/sessions/{id}/reset`、`DELETE /v1/sessions/{id}`、`POST /v1/sessions/{id}/release`、`POST /v1/sessions/{id}/pause`、`GET /v1/sessions/{id}/snapshot`、`GET /v1/sessions/{id}/fish/{fish_id}`、`GET /v1/sessions/{id}/leaderboard`。
  其余端点（developments / breedings / experiments / jobs / mutations 等）当时为 **501 占位**；**当前全部无实现**。
- **WS（历史；2026-09-26 起失效）**：~~当时只是回显契约~~（连上收 `sys.hello`，发任意信封收 `sys.echo`，`arena.*` 推送流从未实现）；实现层已移除，真实推送的契约仍按 `api/API与系统工程.md` §R11 词表设计。
- 端点契约（**设计**，非实现状态）见 `api/API与系统工程.md` 与 `api/API接口.md`；后者已由池伟豪标注「实现层已移除、待重写」。
