# 目录说明

> 本文是 `AGENTS.md`「项目目录结构」的展开版，给出每个目录的职责、"放什么 / 不放什么"、归属与数据流。
> 设计包的目录映射见 `api/API与系统工程.md §2`；两者与本文保持同一事实。

## 1. 顶层速览

| 路径 | 类别 | 定位 | 入库 |
|---|---|---|---|
| `src/evogenesis/` | 代码 | 唯一可导入 Python 包 | 是 |
| `frontend/` | 代码 | 演示 UI（Vite + React） | 是 |
| `configs/` | 契约/配置 | yaml 实验配置 | 是 |
| `schemas/` | 契约/配置 | JSON Schema 跨语言契约 | 是 |
| `scripts/` | 工具 | 薄 CLI 入口 | 是 |
| `tests/` | 工具 | 冒烟 + 单测 | 是 |
| `docs/` | 文档 | 跨模块协作文档 | 是 |
| `prompts/` | 文档 | AI 角色提示词 | 是 |
| `paper/` | 文档 | LaTeX 论文 | 是 |
| `notebooks/` | 文档 | 探索性分析 | 是 |
| `research/` | 资料 | 调研与建模笔记 | 是 |
| `artifacts/` | 产物 | 冻结演示资产 | 是 |
| `results/` | 产物 | 实验图 / 日志 / 指标表 | 否（可删重建） |
| `data/` | 数据 | 原始 / 处理 / 外部数据 | 部分（`raw/` 忽略） |
| `archive/` | 归档 | 历史版本 | 是 |

根文件（不属于任何目录）：`AGENTS.md`（协作公约）、`opencode.json`（opencode 配置）、`README.md`、`LICENSE`、`pyproject.toml` / `uv.lock` / `.python-version`（依赖与环境）、`Makefile`（常用命令）、`.gitignore`。

## 2. 代码：`src/evogenesis/`（唯一 Python 包）

采用 src-layout：仓库根不在 `sys.path` 上，必须 `uv sync` 安装（editable）后才能 `import evogenesis`。导入前缀固定为 `evogenesis.`，例如 `from evogenesis.genome.genome import DiploidGenome`。

依赖方向：`core/` 被所有任务包依赖；任务包彼此尽量不互相依赖；`api/` 是唯一对外服务层。

**每个模块的文档与该模块同目录**（文档随代码）：

```text
core/                # 机制底座：config / seed / logging / tracking / registry / io（最稳定）
  └ 核心机制与数据流.md
genome/              # 二倍体基因组、motif 匹配、遗传表示
  └ 生物学与进化遗传学基础.md
development/         # GRN 离散动力学、precursor、RGCD 发育解码
  └ RGCD数学模型.md
connectome/          # 连接生成与 DanioNet 结构、动力学
  └ DanioNet设计规范.md
arena/               # 二维生态仿真：感官、物理、规则
  └ Danio_Arena设计规范.md
evolution/           # 繁殖、选择、drift、代际更新
  └ 遗传繁殖与演化模型.md
learning/            # 生命周期学习（Behavior Cloning）
  └ 行为克隆学习.md
experiment/          # 实验协议、指标、run、统计
  └ 实验与评价体系.md
viz/                 # 出图（论文图、网络图）
api/                 # FastAPI 路由 + WebSocket
  └ API与系统工程.md
```

`src/evogenesis/` 根另有 `EvoGenesis项目总纲.md`（总交接 + 模块索引）与 `问题定义与研究假设.md`（建模总纲）。

- **放**：本任务的建模与实现代码，以及该模块的接口/目的/用法文档。
- **不放**：实验产物（→ `results/`）、跨模块文档与论文（→ `docs/`、`paper/`）、探索脚本（→ `notebooks/`）、可执行入口（→ `scripts/`）。

## 3. 契约与配置

- `configs/`：实验参数（yaml）。所有数值以 config 为准，报告记录实际版本；`demo_seed.yaml` 与 `experiment_seeds.yaml` 分离 demo 与正式种子。
- `schemas/`：跨语言 JSON Schema（`genome` / `fish` / `experiment`），Python 后端与 TS 前端共用的数据契约。改契约必须双方同步。

## 4. 工具

- `scripts/`：薄 CLI 入口，只做参数解析与调用包逻辑（如 `start_demo.sh`、`serve_api.py`、`run_experiment.py`）。**不放业务逻辑**——逻辑归 `src/evogenesis/`。
- `tests/`：冒烟 + 单测。`TEST_PLAN.md` 是测试计划，`test_*.py` 是现状。
- `Makefile`：常用命令入口（`env` / `test` / `lint` / `fmt` / `tree`）。

## 5. 文档与资料

- `docs/`：跨模块协作文档——`ai-tone-boundaries.md`、`code-review.md`、`search-spec.md`、`ai-use-declaration.md`、`directory-structure.md`（本文）、`THIRD_PARTY.md`、`AI工作流.md`、`开发排期与人员分工.md`、`路演与答辩.md`、`相关工作与开源参考.md`、`局限与未来路线.md`、`参数总表.md`、`验收清单.md`、`项目状态.md`。**各模块的接口/目的/用法文档不在这里**，而是与代码同目录（见 §2）。
- `prompts/`：AI 角色提示词。
- `paper/`：LaTeX 论文（本地编译链 + GitHub，不用 Overleaf）。
- `notebooks/`：探索性分析。
- `research/`：写代码前的材料——`notes/` 放建模推导、符号表、决策记录；`reference/` 放子代理调研 JSON。

## 6. 数据与产物

- `data/`：`raw/` 原始数据（忽略，不入库）、`processed/` 处理后数据、`external/` 外部数据。
- `artifacts/`：冻结演示资产，**入库**（固定 seed、demo population、小 checkpoint），保证现场可复现。
- `results/`：实验产物，**忽略、可随时删掉重建**——`figs/` 图、`runs/<id>/` 单次运行的 config/指标/日志、`tables/` 指标表。
- `archive/`：历史版本归档，入库。

## 7. 数据 / 控制流

```text
genome ──→ development ──→ connectome ──→ arena ──→ evolution ──┐
  │            │              │            │            │        │
DNA+motif   GRN+RGCD      DanioNet     behavior     fitness      │
  └──────────────────────── 下一代 ───────────────────────────────┘
                    ▲                    ▲
                 learning(BC)        experiment 编排；viz 出图；api 对外
```

## 8. “我要放什么”速查

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
| API 路由 / WebSocket | `src/evogenesis/api/` |
| CLI / 一键脚本 | `scripts/` |
| 实验参数 | `configs/` |
| 数据契约 | `schemas/` |
| 冻结演示资产 | `artifacts/` |
| 实验产物（图 / 指标 / run 日志） | `results/` |
| 建模推导 / 符号表 / 决策 | `research/notes/` |
| 调研 JSON | `research/reference/` |
| 模块接口/规格文档 | 对应模块目录（如 `arena/Danio_Arena设计规范.md`） |
| 跨模块文档（工作流 / 排期 / 参数索引 / 验收） | `docs/` |
| 论文 | `paper/` |

## 9. 约定

- **稳定 ID**：`fish_id` / `genome_id` / `generation_id` / `experiment_id` / `environment_id`；前端不得用数组下标当 identity。
- **种子**：所有随机过程由 `core/` 的 seed manager 统一派生（Python `random` / NumPy / PyTorch CPU / PyTorch CUDA）。
- **产物分级**：`artifacts/` 入库冻结资产；`results/` 忽略可重建；`data/raw/` 不入库。
- **空目录**：Git 不跟踪空目录，用 `.gitkeep` 占位。被忽略的目录（`data/raw/`、`results/*/`）长期保留；一旦目录里有被跟踪的真实文件，`.gitkeep` 即可删除。
- **前端**：仅 `frontend/`；技术栈与版本锁定见 `frontend/README.md`。
