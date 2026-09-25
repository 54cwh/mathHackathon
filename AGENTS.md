# 项目公约
- 使用uv, 不使用overleaf，latex写作采用本地编译链+github.
- 如果准备用 AI 写文章，在正式写作前应阅读 `docs/ai-tone-boundaries.md`
- 每次代码写完或改完，提交前按 `docs/code-review.md` 做审查；阻断项复验关闭后方可提交。


# 项目目录结构

代码按任务分层：`core/` 是方向无关的机制底座，其余模块（`genome/ development/ connectome/ arena/ evolution/ learning/ experiment/ api/`）各对应一项研发任务，彼此独立、可单独替换。

```text
mathHackathon/
├── src/evogenesis/             # 唯一可导入包（hatchling editable）
│   ├── core/                   # 机制底座：config / seed / logging / tracking / registry / io
│   ├── genome/                 # 二倍体基因组、motif
│   ├── development/            # GRN、precursor、RGCD 发育解码
│   ├── connectome/             # 连接生成与 DanioNet 动力学
│   ├── arena/                  # 二维生态仿真：感官 / 物理 / 规则
│   ├── evolution/              # 繁殖、选择、drift
│   ├── learning/               # Behavior Cloning 生命周期学习
│   ├── experiment/             # 实验协议、指标、run
│   ├── viz/                    # 可视化（论文图、网络图）
│   └── api/                    # FastAPI 路由 + WebSocket
├── frontend/                   # Next.js 演示 UI（栈待定）
├── configs/                    # yaml 实验配置
├── scripts/                    # 薄 CLI 入口
├── notebooks/                  # 探索性分析
├── tests/                      # 冒烟 + 单测
├── paper/                      # LaTeX 论文
├── schemas/                    # JSON Schema（genome / fish / experiment）
├── docs/                       # 团队协作文档（ai-tone-boundaries / code-review / THIRD_PARTY 等）
│   └── design/                 # 方向设计规格与冻结文档（EvoGenesis 01–17 等）
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

> 每个目录的职责与"放什么 / 不放什么"见 `docs/directory-structure.md`。

## 分层与归属

- `core/` 是唯一长期稳定的机制层，任何任务都复用。
- `genome/ development/ connectome/ arena/ evolution/ learning/ experiment/ api/` 按任务划分，各模块彼此独立、可单独替换；`viz/` 负责出图。
- 任务与角色对应：`research/notes/` 归建模，`paper/` 归写作，`research/reference/` 归调研，`frontend/` 归展示，`results/` 归实验。
- `docs/design/` 存放方向设计规格与冻结文档；`schemas/` 存放跨语言数据契约（JSON Schema）。

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
```


# 技术栈

除「前端 / 演示」外均为已冻结选型；依据 `docs/design/10_系统工程与接口.md`，要求 CPU 可运行、GPU 有则加速。

## 后端 / 模型
- Python 3.12（uv 管理，`requires-python >=3.12`）
- PyTorch（CPU 可运行，GPU 加速）
- FastAPI + Pydantic（API 契约）
- NumPy / SciPy / pandas（数值与数据处理）
- NetworkX（连接组分析）

## 前端 / 演示（待定，未冻结）
- 设计包候选（`docs/design/10_系统工程与接口.md`）：Next.js + TypeScript、Canvas / Phaser.js、Cytoscape.js、WebSocket
- 具体框架与渲染库尚未拍板；`frontend/` 现有骨架仅作参考

## 数据 / 配置
- YAML（`configs/`）
- JSON Schema（`schemas/`，跨语言契约）

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

6. **只读角色约束**：采集与评审类子代理只做调查和判断，不改动文件。

7. **数学表述纪律**：符号表标注单位与维度，量纲一致；显式列出假设及其失效后果；推导不跳步。

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
