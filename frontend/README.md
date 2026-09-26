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

- **组件层**：shadcn/ui。它不是 npm 包，组件源码落在 `src/components/ui/`，用 CLI 添加（`npx shadcn@latest add <name>`）。
- **Arena 渲染**：原生 **Canvas 2D**（不用 WebGL/PixiJS）。
- **实时传输**：原生 `WebSocket` + `fetch`，不引 HTTP 客户端库。
- **3D DNA**：CSS/SVG 动画（three.js 不做，移至 P1）。

## 防坑约定（AI 协作）

1. **不装训练语料外的库**；改 UI 时先读 `src/components/ui/` 里的**本地 shadcn 源码**，按真实 props 写，不凭记忆。
2. **不引 CDN**：字体、图标、资源全部本地打包（现场离线）。
3. **20Hz 热路径不走 React**：Arena 用 `requestAnimationFrame` + Canvas2D，状态放 `useRef`；zustand 只存低频摘要（选中鱼、代、指标），避免每帧 setState。
4. **配置只由官方模板生成**：`vite`/`tsconfig`/`tailwind`/`postcss` 配置不手写，用 `npm create vite@5` + shadcn CLI 产出后再改。
5. **契约同源**：TS 类型对齐 `schemas/`（JSON 字段一律 `snake_case`）。

## 目录规划

```text
frontend/
├─ .nvmrc                     # 22
├─ index.html
├─ package.json  package-lock.json
├─ vite.config.ts  tsconfig*.json
├─ tailwind.config.ts  postcss.config.js  components.json
├─ public/fonts/              # 自托管字体（离线）
└─ src/
   ├─ main.tsx  App.tsx  index.css
   ├─ components/ui/          # shadcn 组件（本地可读）
   ├─ panels/                 # DNA2BrainPanel / BrainForgePanel / DanioArenaPanel
   │                          # EvolutionDashboard / FishCard / MendelMode / CompareFish
   ├─ api/                    # rest.ts / ws.ts / 由 schemas 生成的 types
   ├─ store/                  # zustand
   └─ theme/                  # 主题 token 与注册
```

## 主题 token（暗色"实验室"风）

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
| 正文字体 | Inter（自托管） |
| DNA 等宽字体 | JetBrains Mono（自托管） |
| 圆角 | `10px` |

## 与后端的接口

- REST 命名规范与端点见 `api/API与系统工程.md §4`（`/v1`、资源式、JSON `snake_case`）。
- 实时流走 `/v1/ws`，消息信封 `{v,type,seq,ts,payload}`，`type` 为点分层（`arena.fish_state` 等）。
