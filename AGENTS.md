# 项目公约
- 使用uv, 不使用overleaf，latex写作采用本地编译链+github.
- 如果准备用 AI 写文章，在正式写作前应阅读 `docs/ai-tone-boundaries.md`
- 每次代码写完或改完，提交前按本文件「代码审查」一节做审查；阻断项复验关闭后方可提交。
- 文档修改优先于代码编写，代码不方便审计，文档是审计的硬标准，也是合作与演示的核心，任何超出文档的代码修改，ai应当提醒用户应当修改文档。文档当且仅当用户许可的情况下进行修改，不能”顺便“修改未经许可的文档。
- **禁止 AI 填空**：上游文档未定义的数值、公式、语义，实现者**不得**自行选定并当作既定事实写进代码。必须先回写文档并标注状态（`已定稿` / `草案待确认` / `占位`）；只有 `已定稿` 才能作为契约被依赖，`占位` 的内容不得进论文与正式实验。
- **固定顺序**：`文档 → 代码 → 测试 → 回写文档状态`。反序（代码 → 文档 → 补认领）视为违规，须在 review 中驳回。动手前先答三件事：**做什么**（行为与语义）、**用什么数值**（参数及其来源）、**接口长什么样**（契约字段与状态）；这三项若在上游文档中无定义，**先补文档**，可标 `草案待确认` 并开工，但必须在文档中显式标注「实现已先行、待确认」。
- 赛题补充说明见 `docs/赛题补充说明.md`：作品须给出「原模型→改后模型→结果对比」的可验证证据（准确率 / 参数量 / 速度 / FLOPs / 稳定性等），不能只停留在架构图或产品界面。
- push 之前应当 pull 检查


# 项目目录结构

代码按任务分层：`core/` 是方向无关的机制底座，其余模块（`genome/ development/ connectome/ arena/ evolution/ learning/ experiment/ api/`）各对应一项研发任务，彼此独立、可单独替换。（`api/` 实现层已移除、待重写，仅存契约草案文档。）

**文档随代码**：每个代码集群的文档就放在该模块目录内（如 `arena/Danio_Arena设计与实现说明.md`、`api/API与系统工程.md`），内容为**接口 / 目的 / 用法 + 与代码的映射**，是该模块的审计基准；代码一旦偏离同目录文档即视为缺陷。`docs/` 只放跨模块文档。任何代码改动都应在同一提交里同步对应模块文档。

```text
mathHackathon/
├── src/evogenesis/             # 唯一可导入包（hatchling editable）
│   ├── EvoGenesis项目总纲.md      # 项目总交接 + 模块索引
│   ├── 问题定义与研究假设.md      # 建模总纲
│   ├── core/                   # 机制底座：config / seed / logging / tracking / registry / io
│   │   └── 核心机制与数据流.md
│   ├── genome/                 # 二倍体基因组、motif
│   │   └── 生物学与进化遗传学基础.md
│   ├── development/            # GRN、precursor、RGCD 发育解码
│   │   └── RGCD数学模型.md
│   ├── connectome/             # 连接生成与 DanioNet 动力学
│   │   └── DanioNet设计规范.md
│   ├── arena/                  # 二维生态仿真：感官 / 物理 / 规则 + 实现映射
│   │   └── Danio_Arena设计与实现说明.md
│   ├── evolution/              # 繁殖、选择、drift
│   │   └── 遗传繁殖与演化模型.md
│   ├── learning/               # Behavior Cloning 生命周期学习
│   │   └── 行为克隆学习.md
│   ├── experiment/             # 实验协议、指标、run
│   │   └── 实验与评价体系.md
│   ├── viz/                    # 可视化（论文图、网络图）
│   └── api/                    # 对外服务层（实现层已移除、待重写，仅存契约草案 .md）
│       ├── API与系统工程.md       # 命名/系统/部署约定
│       └── API接口.md            # 逐端点接口参考
├── frontend/                   # 演示 UI（Vite + React）
│   ├── README.md               # 版本锁定与构建
│   └── 交互与可视化.md
├── configs/                    # yaml 实验配置
├── scripts/                    # 薄 CLI 入口
├── notebooks/                  # 探索性分析
├── tests/                      # 冒烟 + 单测
├── paper/                      # LaTeX 论文
├── schemas/                    # JSON Schema（genome / fish / experiment）
├── docs/                       # 跨模块协作文档（AI工作流 / 参数总表 / declaration / 赛题补充说明 / 验收清单 等）
├── archive/                    # 历史版本归档（DNA2Brain v0.1 等）
├── prompts/                    # AI 角色提示词
├── artifacts/                  # 冻结演示资产（入库）
├── results/                    # 实验产物（忽略）
│   ├── figs/                   # 图
│   ├── runs/                   # 每次运行的 config/指标/日志
│   └── tables/                 # 指标表
├── data/                       # 数据
│   ├── raw/                    # 原始数据（忽略）
│   ├── processed/              # 处理后数据
│   └── external/               # 外部数据
└── research/                   # 写代码前的材料
    ├── reference/              # 子代理调研 JSON
    └── notes/                  # 建模推导、符号表、决策记录
```

根文件：`AGENTS.md`（本文件）、`opencode.json`、`README.md`、`LICENSE`、`pyproject.toml`/`uv.lock`/`.python-version`、`Makefile`、`.gitignore`。

`src/evogenesis/` 采用 src-layout：必须 `uv sync`（editable）后才能 `import evogenesis`，导入前缀固定为 `evogenesis.`。依赖方向：`core/` 被所有任务包依赖，任务包彼此尽量不互相依赖，`api/` 为对外服务层（实现层已移除、待重写）。

## 分层与归属

- `core/` 是唯一长期稳定的机制层，任何任务都复用。
- `genome/ development/ connectome/ arena/ evolution/ learning/ experiment/ api/` 按任务划分，各模块彼此独立、可单独替换（`api/` 实现层已移除、待重写）；`viz/` 负责出图。
- 任务与角色对应：`research/notes/` 归建模，`paper/` 归写作，`research/reference/` 归调研，`frontend/` 归展示，`results/` 归实验。
- 文档与代码同目录（见上方树）：每个模块文档是该模块的接口/目的/用法与审计基准，代码偏离即缺陷。`docs/` 只放跨模块文档；`schemas/` 存放跨语言数据契约（JSON Schema）。

## 放什么（速查）

| 你要做的事 | 放哪 |
|---|---|
| 新的基因组 / motif 逻辑 | `src/evogenesis/genome/` |
| GRN、发育、RGCD | `src/evogenesis/development/` |
| 网络结构与神经动力学 | `src/evogenesis/connectome/` |
| 环境、感官、物理、规则 | `src/evogenesis/arena/` |
| 繁殖 / 选择 / drift | `src/evogenesis/evolution/` |
| Behavior Cloning 训练 | `src/evogenesis/learning/` |
| 指标、run、统计 | `src/evogenesis/experiment/` |
| 出图 | `src/evogenesis/viz/` |
| API 路由 / WebSocket | `src/evogenesis/api/`（实现层已移除、待重写） |
| CLI / 一键脚本 | `scripts/` |
| 实验参数 | `configs/` |
| 数据契约 | `schemas/` |
| 冻结演示资产 | `artifacts/` |
| 实验产物（图 / 指标 / run 日志） | `results/` |
| 建模推导 / 符号表 / 决策 | `research/notes/` |
| 调研 JSON | `research/reference/` |
| 模块接口/规格文档 | 对应模块目录（如 `arena/Danio_Arena设计与实现说明.md`） |
| 跨模块文档（工作流 / 排期 / 参数索引 / 验收） | `docs/` |
| 论文 | `paper/` |

## 契约与配置 / 工具

- `configs/`：实验参数（yaml）。所有数值以 config 为准，报告记录实际版本；`demo_seed.yaml` 与 `experiment_seeds.yaml` 分离 demo 与正式种子。
- `schemas/`：跨语言 JSON Schema（`genome` / `fish` / `experiment`），Python 后端与 TS 前端共用；改契约必须双方同步。
- `scripts/`：薄 CLI 入口，只做参数解析与调用包逻辑（`run_experiment.py`），**不放业务逻辑**。
- `tests/`：冒烟 + 单测；`TEST_PLAN.md` 是测试计划，`test_*.py` 是现状。
- `data/`：`raw/`（忽略）、`processed/`、`external/`；`notebooks/` 放探索性分析。

## 文档层级与优先级（冲突裁决）

文档冲突时按**层级**裁决，同一事物由**单一 owner** 定义；低层不得与高层冲突。

| Tier | 文档 | 拥有 |
|---|---|---|
| 0 | 赛题原文、`docs/赛题补充说明.md` | 外部硬约束（只可解释，不可改） |
| 1 | `AGENTS.md` | 项目公约 |
| 2 | `src/evogenesis/问题定义与研究假设.md`、`EvoGenesis项目总纲.md` | 方向与语义 |
| 3 | 跨模块契约：`schemas/`、`docs/参数总表.json`、`docs/验收清单.md`、`research/notes/bibliography.md` | 字段名/类型、参数值与依据状态、完成判据、文献事实 |
| 4 | `src/evogenesis/` 各模块文档（与代码同目录） | 该模块行为/算法/字段 |
| 5 | `configs/*.yaml` | 运行期实际取值 |
| 6 | `research/reference/*`、`docs/相关工作与开源参考.md`、`docs/设计依据审计.md`、`docs/开发排期与人员分工.md` | 证据与过程，不作契约 |

- **属地（单一来源）**：字段名/类型 → `schemas/`；参数取值 → `configs/`，参数依据与状态 → `docs/参数总表.json`（值冲突以 `configs/` 为准，参数总表须同步）；文献 → `research/notes/bibliography.md`（未登记即引用＝缺陷）；验收判据 → `docs/验收清单.md`；API 端点 → `api/API接口.md`、系统约定 → `api/API与系统工程.md`；实验 run 目录与产物布局 → `experiment/实验与评价体系.md`；模块内算法与常量语义 → 该模块文档。
- **数据流产物归属（producer owns）**：流经模块边界的数据对象由**产出方**模块文档定义，消费方只引用，不得改名或另立定义。`core/核心机制与数据流.md` 是数据流总管，拥有管线图与边界清单，不定义模块内算法。
- **禁止循环引用**：边界对象必须指定唯一 owner；owner 未定时登记进 `core/核心机制与数据流.md` §10，不得在两处各写一版。
- **修改启动顺序（沿数据流，上游优先）**：`赛题 → AGENTS → 建模总纲 → core 边界清单 → 产出方模块文档 → 消费方模块文档 → schemas/configs/参数总表 → 代码 → 测试 → 回写 core §10`。改上游必须评估下游；下游不得抢先改；跨语言字段（`schemas/` 与 `configs/` 键名）双方同步。
- **每个文档首行（H1 之下）须写明「管辖范围」**：本文件拥有什么、不拥有什么；JSON 契约用 `meta.owns` 字段。

### `src/evogenesis/` 内部文档关系（随数据流）

模块文档按数据流方向排列，**上游定义、下游引用**（数据流图见下节「数据 / 控制流」）：

| 文档 | 在数据流中的角色 |
|---|---|
| `问题定义与研究假设.md`、`EvoGenesis项目总纲.md` | 方向、语义、模块边界（src 内最高） |
| `core/核心机制与数据流.md` | 数据流总管：管线图、边界清单、seed/ID/存储；不定义模块内算法 |
| `genome/生物学与进化遗传学基础.md` | 产出表达后的基因组 / gene products |
| `development/RGCD数学模型.md` | 产出发育结果 `(A, Z, τ, W⁰, M)`（§1 已声明） |
| `connectome/DanioNet设计规范.md` | 产出每步 activation、动作 `(ω, v)`、当代 `ΔW` |
| `arena/Danio_Arena设计与实现说明.md`（兼容入口：`Danio_Arena设计规范.md`、`Danio_Arena实现说明.md`） | 产出 observation（12 维）、事件日志、每鱼记录；定义动作 `(ω,v)` 如何作用于世界，并映射到当前实现 |
| `evolution/遗传繁殖与演化模型.md` | 产出 fitness、下一代 genome |
| `learning/行为克隆学习.md` | 产出 `ΔW`（横向，接 connectome） |
| `experiment/实验与评价体系.md` | 拥有指标与 run 目录布局（横向） |
| `api/API与系统工程.md`、`api/API接口.md` | 对外：稳定 ID、端点、系统约定（实现层已移除、待重写） |
| `viz/` | 出图（消费 `results/`，不做源定义） |

每个箭头的边界对象由**产出方**文档定义，消费方只引用（见上「producer owns」）。

## 数据 / 控制流

```text
genome ──→ development ──→ connectome ──→ arena ──→ evolution ──┐
  │            │              │            │            │        │
DNA+motif   GRN+RGCD      DanioNet     behavior     fitness      │
  └──────────────────────── 下一代 ───────────────────────────────┘
                    ▲                    ▲
                 learning(BC)        experiment 编排；viz 出图；api 对外（实现层待重写）
```

### 动手前必读（写任一模块代码的固定动作）

写 `src/evogenesis/` 任一模块代码前，按**数据流上游优先**固定查三处；冲突以更高层级/被查文档为准：

1. **本模块文档**（同目录 `.md`）：首行「管辖范围」写明它拥有 / 不拥有什么、指向谁。
2. **`core/核心机制与数据流.md` 的绑定节**：`§0` 模块与契约边界；`§3` 种子派生 + **`§3.1` 稳定 ID**（禁自建随机源、禁空 ID）；`§7` 存储分级 + dtype + **跨框架转换**（NumPy→torch 走 `core/tensors.py::to_float32_tensor`，禁隐式 `float64`）；`§4` 数据流管线与边界对象清单；`§10` owner 登记（新边界对象 owner 未定先登记此处）。config / logging / tracking / io / registry 一律用 `core` 公开 API。
3. **边界两端文档**：上游产出方（对象字段 / 形状由它定义，只引用、不改名）+ 下游消费方（要什么字段 / 形状，对齐 export）。

## 约定

- **稳定 ID**：`fish_id` / `genome_id` / `generation` / `experiment_id` / `environment_id`；前端不得用数组下标当 identity。
- **种子**：所有随机过程由 `core/` 的 seed manager 统一派生（Python `random` / NumPy / PyTorch CPU / PyTorch CUDA）。
- **空目录**：Git 不跟踪空目录，用 `.gitkeep` 占位；被忽略的目录（`data/raw/`、`results/*/`）长期保留。
- **前端**：仅 `frontend/`；技术栈与版本锁定见 `frontend/README.md`。

## 产物分级

- `artifacts/` 入库：固定 seed、demo population、小 checkpoint，保证现场演示可复现。
- `results/` 忽略：实验图、日志、指标表，可随时删除重建。
- `data/raw/` 忽略：原始数据不入库。

## 常用命令

```text
make env    # uv sync，安装 evogenesis（editable）
make test   # 运行测试
make lint   # ruff 静态检查
make fmt    # ruff 格式化
make tree   # 查看目录结构
make frontend  # 构建前端产物到 frontend/dist
make experiment ARGS='--config configs/default_arena.yaml --seed 1 --experiment-id exp-0001'  # 创建实验 run
```

## Git 分支策略

- 两人协作，直接在 `main` 上开发并推送（`git push origin main`）。
- 提交前必须：`make lint && make test` 通过，且按本文件「代码审查」一节完成审查。
- 提交信息遵循 `<type>(<scope>): <summary>`，并保留 `审查：` 留痕行。

### 多人 / 多 AI 共用同一工作区

默认执行者（人 / AI）在**同一工作区**协作，靠纪律而非隔离避免互相覆盖：

- **单写者（硬约束）**：同一文件同一时刻只允许一个写者；跨 lane 只读，不改对方文件。动手前先声明将改动的文件范围。
- **推前一律 rebase**：`git fetch origin && git pull --rebase origin main`；禁用无参数 `git pull`（会触发 `divergent branches` 或产生多余 merge）。
- **推前先看对方提交**：`git log --oneline -5`；若发现同主题提交（同一个决策 / 文档 / 数值），**先对齐再动手**，禁止各写一版。
- **禁止长时间挂未提交改动**：改完即 `make lint && make test` 后提交，避免他人 `git add -A` 把你的 WIP 卷进他的提交、造成归属错乱。
- **身份与归属**：多个执行者可能共用同一 git 账号；提交信息正文须写清模块与主题，便于事后区分。
- 个人 / AI 分支命名 `<name>/dev`（如 `cwh/dev`、`ai2/dev`）。
- 需要真正并行时才用 `git worktree`（各自分支，**不可同一分支被两个 worktree 同时 checkout**）：`git worktree add -b <name>/dev ../<repo>-<name> origin/main`，用完 `git worktree remove`。
- 冲突处理：`git status` 列出冲突文件后逐个人工合并，保持最终态（禁 `rm`，见「根因修复原则」），`make lint && make test` 复验后再提交。


# 技术栈

除「前端 / 演示」外均为已冻结选型；依据 `api/API与系统工程.md`，要求 CPU 可运行、GPU 有则加速。

## 后端 / 模型
- Python 3.12（uv 管理，`requires-python >=3.12`）
- PyTorch（CPU 可运行，GPU 加速）
- FastAPI + Pydantic（API 契约）
- NumPy / SciPy / pandas（数值与数据处理）
- NetworkX（连接组分析）

## 前端 / 演示
- Vite 5 + React 18 + TypeScript 5；Tailwind 3.4 + shadcn/ui + lucide-react
- 渲染：Canvas 2D（Arena）、Cytoscape.js 3（脑图）、ECharts 5（图表）；状态 zustand 4
- 传输：原生 WebSocket / fetch；从 `schemas/` 对齐类型
- 版本锁定与防坑约定见 `frontend/README.md`

## 数据 / 配置
- YAML（`configs/`）
- JSON Schema（`schemas/`，跨语言契约）
- 日志：structlog（JSONL，字段对齐 OpenTelemetry Logs）
- 跟踪：MLflow（本地 file store，现场离线）
- 表格 / 数组：pyarrow（Parquet）、NumPy `npz`（`float32`）

## 训练 / 演化
- Behavior Cloning（Stage 2，`K=20` mini-batch imitation）
- PPO / SAC 仅作 P2

## 质量 / 复现
- pytest、ruff
- seed manager 统一派生（Python `random` / NumPy / PyTorch CPU / PyTorch CUDA）
- uv、Makefile、Docker（复现用；现场优先本机运行）

## 约束
- 现场完全离线：不依赖 OpenAI API、外部模型 API、远程 DB、远程资产 CDN。


# 通用工作原则

1. **先方案后执行**：动手前先给出方案或建模提纲，获用户或主 agent 确认后再展开。

2. **对比公平**：对比实验使用同数据、同预算；报告结果时给出方差或重复次数。

3. **复现纪律**：固定随机种子，记录环境与配置，给出可复跑命令。

4. **不确定性诚实**：找不到就写“没找到”，不用低质结果充数；无法证明的断言标注“猜想/待验证”，不杜撰数字、引用或 API。

5. **最小验证先行**：先跑最小实验验证管线，确认无误后再放大。

6. **只读角色约束**：采集与评审类子代理只做调查和判断，不改动文件（例外：`scout` 在任务明确要求时可**只追加**写 `research/notes/bibliography.md` 登记文献）。

7. **数学表述纪律**：符号表标注单位与维度，量纲一致；显式列出假设及其失效后果；推导不跳步。

# 代码审查

每次写完或改完代码，提交前执行。目的是让"代码写完了"有一个统一、可复跑的判据。

## 自动检查（必须全绿）

```bash
uv run ruff format .
uv run ruff check .
uv run pytest -q
```

## 人工检查清单

逐条对照，命中问题必须修，不得带病提交。

| 维度 | 检查项 |
|---|---|
| 文档先行 | 本次改动有先行文档；该文档覆盖了改动的行为、数值与接口契约；不存在"文档未定义、由实现自行选定"的项。凡有此类项，即属未认领的 AI 填空，须回写文档并标注状态（`已定稿` / `草案待确认` / `占位`）后方可提交；**本项为阻断项**。冻结判据：标 `已定稿` 前须逐项核对文档公式中**每个符号/张量**具备 **定义 + 形状 + dtype + 值域**，缺一不得冻结 |
| 规格一致 | 实现符合任务描述或该模块同目录文档（如 `arena/Danio_Arena设计与实现说明.md`）；函数签名、张量形状等接口未被擅自改动 |
| 可复现 | 随机种子固定；无硬编码绝对路径；给出可复跑命令 |
| 正确性 | 关键逻辑有对应测试；边界情形（空输入、极值、除零）已处理 |
| 数值/设备 | CPU/GPU 上 dtype 一致；无隐式类型提升（本机踩过 Float 与 Double 不一致） |
| 卫生 | 无 `rm`、无明文密钥、无调试残留 `print`、无注释掉的死代码 |
| 可读 | 命名清晰；单个函数职责单一 |

## 结论与返工

结论分 `阻断 / 重要 / 建议` 三级。**阻断项修复后必须重跑自动检查并复验**，确认关闭后再提交。

## 留痕

在提交信息或 PR 描述里写一行：

```
审查：自动检查全绿；人工清单已过；遗留：<无 / 具体项>
```

# 根因修复原则

1. **直接修复，保持最终态**

   发现逻辑错误、冗余功能或设计缺陷时，直接将代码修改为正确的最终实现。避免通过额外的 `if`、兼容分支、临时开关或其他补丁逻辑绕过问题，也不要在错误实现之上继续叠加修复。

2. **保持最终产物自洽**

   修改后的代码、文档和配置必须完整、准确地表达当前设计，并与实际行为保持一致。最终产物应能够独立理解和维护，不依赖历史上下文、提交记录或修复过程才能判断其正确性。

3. **使用正向、面向当前状态的描述**

   注释、提交信息和文档应直接描述当前实现的功能、行为和设计意图。优先使用肯定、明确的表述，避免通过否定历史状态来说明当前状态。

   ❌ `实现功能 A，无功能 B`
   ❌ `禁用功能 B`
   ❌ `移除之前的临时逻辑`
   ❌ `修复之前存在的问题`

   ✅ `实现功能 A`
   ✅ `采用新的处理流程`
   ✅ `使用统一的状态管理机制`

4. **修改即代表最终状态**

   每次代码修改、Commit 或 PR 都应视为对应模块的最终状态描述。提交内容应完整反映当前设计，不应依赖历史提交、Issue 或 PR 讨论来解释当前代码为何如此实现。

5. **优先消除根因，而非控制症状**

   当问题由错误的抽象、数据流、接口设计或状态管理引起时，应修正产生问题的根因，而不是增加额外逻辑限制问题的表现形式。修复完成后，应尽可能使原有错误路径自然消失。

# 搜索任务

委派搜索子代理前，要求其先读 `docs/search-spec.md`，并按其中的 JSON 规范输出到 `research/reference/`。
