# EvoGenesis

**Evolutionary-Developmental Neural Networks from Regulatory Genomes**

中文名：**EvoGenesis：基于遗传调控与演化发育的神经网络生成系统**

> Edit DNA. Grow Brains. Evolve Behavior.

EvoGenesis 是一个可离线运行的计算实验平台。它定义一套可编辑、可遗传的人工二倍体 DNA，经统一的调控与发育模型生成 DanioNet；DanioNet 进入 Danio Arena 的闭环生态，在捕食、逃逸、能量管理与繁殖选择中接受评价。仓库包含完整实现、实验管线、离线演示前端与中文论文/技术报告草稿。

## 仓库内容

**后端包 `src/evogenesis/`**（每个模块含同目录的接口 / 目的 / 用法文档）

| 模块 | 内容 |
|---|---|
| `core/` | 机制底座：config 解析、种子派生、稳定 ID、张量转换、日志、跟踪、注册表、IO |
| `genome/` | 二倍体基因组结构、motif 目录与遗传算子（重组、SNP 突变、drift） |
| `development/` | GRN 离散动力学、precursor 分裂与细胞命运、RGCD 连接组解码 |
| `connectome/` | DanioNet 六类神经元网络与神经动力学，以及 MLP / GRU / 固定稀疏 RNN 基线 |
| `arena/` | 连续二维生态：世界、实体、物理、规则与结构化感知编码 |
| `evolution/` | 配子与受精、选择算子、适应度与代际更新 |
| `learning/` | Behavior Cloning 生命周期学习：数据、加权损失、训练与报告 |
| `experiment/` | 实验协议与指标、run 目录布局、代循环编排与各实验 runner |
| `pipeline/` | 模型链装配：config → 种群 → 发育 → DanioNet → Arena |
| `viz/` | 论文图与配套数据表出图 |
| `api/` | FastAPI 对外服务层：会话、基因组实验室、运行记录、环境选择实验与 WebSocket |

**前端 `frontend/`**：Vite + React 演示 UI，含 DNA、Brain、Arena、Evolution 等面板；通过 REST / WebSocket 对接后端，Arena 用 Canvas 2D 实时渲染，资源全本地打包。

**契约与配置**：`schemas/` 为跨语言 JSON Schema（Python 后端与 TS 前端共用），`configs/` 为实验参数 yaml。

**实验与脚本**：`scripts/` 为薄 CLI 入口，`tests/` 为冒烟与单测。

**论文与文档**：`paper/` 为 LaTeX 论文与技术报告；`docs/` 为跨模块文档；`research/` 为调研 JSON 与建模笔记；`AGENTS.md` 为项目公约与目录职责。

**资产与产物**：`artifacts/` 为入库的冻结演示资产；`results/` 为实验产物（忽略，可由 config 与 seed 重生成）；`data/` 为数据。

## 设计

### 数据流

```text
configs → SeedManager → G → D_Θ → (A, Z, τ, W⁰, M) → DanioNet → T → F → P_{t+1}
```

`G` 为人工二倍体基因组；`D_Θ` 为发育算子（GRN → 细胞命运 → RGCD）；`(A, Z, τ, W⁰, M)` 为连接矩阵、细胞身份、时间常数、发育初始权重与活跃神经元掩码；`T` 为行为轨迹；`F` 为适应度；`P_{t+1}` 为下一代种群。所有随机过程由 `SeedManager` 从 master seed 确定性派生。

### 关键设计

- **网络架构由发育过程生成。** 基因组经 motif 匹配驱动 GRN，再经 RGCD 解码为连接组；拓扑与神经元时间常数都是发育产物，基因组不直接存储连接矩阵。因此「换一个碱基」或「换一个随机种子」都能造成可测量的结构差异。
- **当代学习与遗传边界分离。** 学习只在冻结结构上更新权重幅度，并遵守 Dale sign 约束：

  ```text
  W = W⁰(Development) + ΔW(Lifetime Learning)
  W = A ⊙ (sign(W⁰) ⊙ softplus(Θ))
  ```

  增量 ΔW 不进入繁殖通路；后代只继承 DNA，并从发育重新开始。
- **评价走闭环生态仿真。** Arena 是连续二维、感知受限的觅食—避敌环境，行为由感知—动作回路与环境耦合产生，适应度综合生存、捕食、逃脱与能量。
- **种群按有限二倍体演化。** 随机配子、重组、SNP 突变与 fitness-based 选择构成代际更新，同一套机制支持孟德尔分离演示。

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 / 模型 | Python 3.12（uv）、PyTorch、FastAPI + Pydantic、NumPy / SciPy / pandas、NetworkX |
| 前端 / 演示 | Vite + React + TypeScript、Tailwind CSS、Canvas 2D（Arena）、Cytoscape.js（脑图）、ECharts（图表）、zustand；原生 WebSocket / fetch |
| 数据 / 配置 | YAML（`configs/`）、JSON Schema（`schemas/`）、structlog（JSONL）、MLflow（本地 file store）、pyarrow / NumPy `npz` |
| 训练 / 演化 | Behavior Cloning；PPO / SAC 仅作扩展 |
| 质量 / 复现 | pytest、ruff、统一 seed manager、uv、Makefile、Docker（复现用，现场优先本机） |

## 实验与消融

实验协议（A–F 均为必做）由 `src/evogenesis/experiment/实验与评价体系.md` 拥有，指标定义与统计口径同在该文件。

### 实验

- **A 基因组 → 架构**：随机生成一批基因组，各跑完整发育，统计神经元数、细胞类型分布、连接密度与时间常数分布。
- **B 单碱基突变**：对代表性 haplotype 逐位点做替代突变，测表达变化与结构距离（`d_edge` / `d_τ` / `ΔB`），产出基因组敏感性图谱。
- **C 基线对照**：MLP、GRU、固定稀疏 RNN 与 DanioNet 在相同数据、相同预算、参数量同一数量级下比较任务与效率指标。
- **D 消融**：见下。
- **E 鲁棒性**：对已发育网络的活跃支撑边按比例删除，主指标为行为发散，outcome 指标作次要证据。
- **F 环境选择**：同一初始种群分别进入三组环境，跑多代演化，记录等位基因与表型频率、viability、适应度与结构统计。
- **BC 生命周期学习**：训练前 / 后在**同一局与同一网络对象**上对照，并给出 ΔW 不进入遗传通路的证据。
- **penetrance**：以两位点自交的四类基因型为条件，报告观测架构档与期望档的一致率（外显率），暴露「基因型 → 架构」是概率性偏置。
- **孟德尔验证**：AaBb × AaBb 的分离比与 χ² 检验。

### 消融

每个消融臂只改一个变量（实现口径见 `connectome/DanioNet设计规范.md` §9）：

| 臂 | 唯一变量 |
|---|---|
| homogeneous τ | 时间常数改为常数（`tau_min = tau_max`） |
| w/o spatial wiring cost | 空间布线代价系数置 0（`distance_lambda = 0`） |
| BC 有 / 无 Dale 符号约束 | 关闭 Dale 符号约束（`sign_constrained=False`） |
| w/o GRN（可选第 4 臂） | 跳过 GRN 发育，按固定密度随机采样连接 |

### 环境对照

三组环境相对基线**单因子**改变一个驱动，`environment_id` 取值集合为 `default` / `food_rich` / `predator_rich` / `resource_scarce`。

### 统计与产物

- 正式种子与最低重复数见 `configs/experiment_seeds.yaml`；逐级统计为先 seed 内对个体等权、再沿 seed 轴报 mean ± std。
- 每个 run 固定 config / seed / git commit，逐个体原值落盘，任何汇总数字可重算。
- 实验结果与结论见论文 §5 / §6 与 `paper/图表-数据对照表.md`，本文件不复述数值。

## 前端

`frontend/` 是现场演示 UI，把后端仿真的过程可视化并支持交互，让观众直观看到 DNA 经发育生成脑网络、进而产生行为与演化的链路。已实现的功能：

- **DNA2Brain Lab**：查看与编辑个体 DNA，呈现 motif 与调控，提供 Free Edit 与 Story Mutation 两种突变模式，并触发重新发育。
- **Brain Forge**：呈现发育生成的连接组与神经元激活，用于对比不同基因组得到的网络。
- **Danio Arena**：实时渲染生态会话，点选个体查看状态，支持手动控制与逐代推进。
- **Evolution Dashboard**：呈现逐代演化指标与排行榜。
- **Development Pipeline / Playback**：呈现从配置、种子到基因组与发育结果的流程，并支持回放。

**运行**（前置 Node 22）：

```bash
make demo            # 一键：构建前端 + 启动 API，浏览器打开 http://127.0.0.1:8000
```

前端开发（热更新；dev server 在 5173，`/v1` 反向代理到后端 8000）：

```bash
# 终端 A：后端
uv run python scripts/serve_api.py
# 终端 B：前端
cd frontend
npm install
npm run dev          # http://127.0.0.1:5173
```

单独构建静态产物到 `frontend/dist`：

```bash
make frontend        # = cd frontend && npm run build
```

前端检查：`npm run typecheck`、`npm run lint`、`npm run lint:design`。

前端只做渲染与交互，仿真由后端权威运行。

## 环境要求

| 依赖 | 版本 | 用途 |
|---|---|---|
| Python | >= 3.12 | 后端与实验 |
| [uv](https://docs.astral.sh/uv/) | 最新 | 依赖与环境管理 |
| Node | 22 | 演示前端 |

## 安装

```bash
git clone git@github.com:54cwh/mathHackathon.git
cd mathHackathon
make env          # = uv sync，安装 evogenesis（editable）
```

## 快速开始

```bash
make demo         # 构建前端 + 启动 API，浏览器打开 http://127.0.0.1:8000
make experiment ARGS='--config configs/default_arena.yaml --seed 1 --experiment-id exp-0001'
```

编译论文：

```bash
cd paper/latex && ./build.sh          # = latexmk -xelatex main.tex -> main.pdf
```

## 开发

```bash
make test         # 运行测试（pytest）
make lint         # ruff 静态检查
make fmt          # ruff 格式化
make tree         # 查看目录结构
```

提交前须通过 `make lint && make test`，并按 `AGENTS.md`「代码审查」完成人工清单。

## 贡献

- 直接在 `main` 上开发，推前 `git fetch origin && git pull --rebase origin main`。
- 提交前 `make lint && make test` 通过；提交信息遵循 `<type>(<scope>): <summary>`。
- 文档先行、单一来源：改代码须同步同目录模块文档；`schemas/` 与 `configs/` 的键名双方同步。
- 协作与审查约定完整版见 `AGENTS.md`。

## 文档

- `AGENTS.md`：项目公约、目录职责、文档层级与优先级。
- `src/evogenesis/<模块>/<模块文档>.md`：模块接口 / 目的 / 用法与审计基准。
- `paper/latex/README.md`：论文编译、文献生成与投稿模板切换。
- `docs/参数总表.json`：参数依据与状态；`configs/*.yaml` 为运行期取值唯一来源。
- `docs/验收清单.md`：完成判据。
- `docs/declaration/`：AI 使用声明与第三方依赖登记。

## 复现

- 正式种子与 run 布局：`configs/experiment_seeds.yaml`、`src/evogenesis/experiment/实验与评价体系.md`。
- 全流程命令链：`paper/latex/sections/07-reproducibility.tex` 与 `scripts/`。
- 实验结果与数值不在本文件复述，owner 为论文 §5 / §6 与 `paper/图表-数据对照表.md`。

## 状态

平台实现与实验管线已落地，论文为中文草稿。已取得的结论与尚未验证的范围以论文 §6「局限与价值」为准。

## 许可证

MIT，见 `LICENSE`。
