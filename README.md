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

### 工程约定

- **文档先行、单一来源。** 每个模块的接口 / 目的 / 用法与其代码同目录，是该模块的审计基准；字段名与类型归 `schemas/`，参数取值归 `configs/`，文献归 `research/notes/bibliography.md`。
- **运行期取值集中。** 所有数值以 `configs/*.yaml` 为准，报告记录实际版本；`docs/参数总表.json` 登记参数依据与状态。
- **确定性复现。** 所有随机过程由统一 seed manager 派生，每个 run 固定 config / seed / git commit，逐个体原值落盘。
- **跨语言契约。** `schemas/` 的 JSON Schema 由 Python 后端与 TS 前端共用，改契约双方同步。
- **离线可运行。** CPU 可运行、GPU 可加速；现场不依赖外部模型 API、远程数据库或 CDN 资产。

## 前端

`frontend/` 是现场演示 UI，只做渲染与交互；物理、神经动力学与仿真由 Python 后端权威运行，前端不重算。

**技术栈**：Vite + React 18 + TypeScript、Tailwind CSS、zustand（状态）、ECharts（指标图）、Cytoscape.js（连接组图）、原生 Canvas 2D（Arena 逐帧渲染）、原生 WebSocket 与 fetch（传输）。字体与素材本地自托管，满足离线要求；锁定版本见 `frontend/README.md`。

**面板**：DNA2Brain Lab（DNA 编辑与 motif）、Brain Forge（连接组与神经元激活）、Danio Arena（实时会话与逐代推进）、Evolution Dashboard（演化指标）、Development Pipeline 与 Playback。

**数据通道**：REST（会话、基因组实验室、运行记录、环境选择实验）加 WebSocket 实时推送；前端类型对齐 `schemas/`，不自行定义后端契约。

**设计系统**：`src/design/` 是颜色、几何、字体的唯一定义处，面板只引用 token；`npm run lint:design` 作为强制闸门，检查颜色越界、圆角残留与 token 漂移。Arena 的热路径走 `requestAnimationFrame` + Canvas 2D，状态放 `useRef`，不经 React 每帧渲染。

**文档**：`frontend/README.md`（技术栈、种子与实时行为、防坑约定）、`交互与可视化.md`（界面规格）、`通用层设计.md` / `通用层接口.md`（通用层接口与设计）、`演示讲稿.md` / `网页说明与讲解顺序.md`（路演）。

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
