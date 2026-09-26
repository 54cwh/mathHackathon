# EvoGenesis 运行运维设计依据：artifacts 体积预算 与 失败/续跑/清理策略

> 搜索时间：2026-09-26 ｜ 用途：为核心机制文档 `src/evogenesis/core/核心机制与数据流.md` §10 #10「artifacts/ Demo 子集规则与体积预算」与 #11「失败/续跑/清理策略（异步长任务）」提供外部依据与工程惯例。
> 证据清单见同目录 `design-basis-runops.json`（19 条）。本文件只做摘要与建议，不修改代码、不修改文档。
> 约定：`[硬标准]`＝有官方原文/评审政策支撑；`[工程惯例]`＝官方文档给出的常见做法，非强制；`[设计选择]`＝无外部依据，属本项目自定，必须写入文档并标状态。

---

## 0. 项目现状（只读核对）

- `artifacts/` 入库（固定 seed、Demo 种群、小 checkpoint），冻结以保证现场复现；现场完全离线（`api/API与系统工程.md` §7 离线红线）。
- `results/runs/<experiment_id>/` 布局见 `experiment/实验与评价体系.md` §5.1：`metadata.json / config_snapshot/ / metrics.csv / population.jsonl / seed.txt / git_commit.txt / plots/`。
- `.gitignore` 第 51-55 行整体忽略 `results/**`；第 63-66 行默认忽略 `*.pt/*.pth/*.ckpt/*.safetensors`，仅 `artifacts/**` 显式白名单入库。既有意图是：**artifacts/ 只放冻结演示资产，不放实验中间产物**。
- `core §10 #6`（seed 派生函数形式）仍待定——它决定续跑是「可确定性重放」还是「必须序列化 RNG state」。

---

## 一句话结论

- **artifacts 体积**：受 GitHub 入库硬约束——单文件 `< 100 MiB`（超则阻断）、`> 50 MiB` 警告、网页上传 `≤ 25 MiB`，仓库建议 `< 1 GB`。综合建议 `artifacts/` 总量 `≤ 100 MB`、单文件 `≤ 50 MiB`。**不引入 Git LFS**（clone 需联网，与离线红线冲突）。`[硬标准 + 设计选择]`
- **checkpoint**：演化 10–20 代属短任务，建议**每代存一次**；保留用 **`last + best`**（或 `top_k=2~3`），`artifacts/` 只冻结 1 个 best demo checkpoint。`[工程惯例]`
- **续跑**：最小状态 = 完整 config 快照 + `git_commit` + master seed + 代数 + 当前种群 + `status` + 已写指标边界。是否额外存 RNG state 取决于 §10 #6。`[工程惯例，需与 §10 #6 联动]`
- **清理**：先软删、再按窗口硬清；GC 根＝「被 artifacts/ 或论文图表引用的 run」。保留最近 3 次或 30 天，未被引用者可清。`[工程惯例 + 设计选择]`

---

## 1. 模型/产物体积惯例

### 1.1 权威约束（官方原文）

| 依据 | 关键原文 | 出处 |
|---|---|---|
| GitHub — About large files | 「larger than **50 MiB**, you will receive a warning」「GitHub blocks files larger than **100 MiB**」「repositories remain small, ideally less than **1 GB**, and less than **5 GB** is strongly recommended」 | [docs.github.com](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) |
| GitHub — Repository limits | 单对象推荐上限 `1 MB`、强制上限 `100 MB`；单次 push `2 GB` | [docs.github.com](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits) |
| GitHub — Git LFS | 单文件上限 Free/Pro `2 GB`、Team `4 GB`、Enterprise `5 GB`（实体在服务端，clone 需联网） | [docs.github.com](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage) |
| PyTorch — Saving and Loading Models | 通用 checkpoint「often **2~3 times larger** than the model alone」 | [docs.pytorch.org](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html) |
| Hugging Face — Storage limits | 文件 `<200 GB`、每仓文件 `<100k`、单 commit `<100 files` | [huggingface.co](https://huggingface.co/docs/hub/storage-limits)（页面直取超时，取自官方页检索摘要） |

### 1.2 对本项目的含义

- artifacts/ 走**普通 Git 入库**，因此 **100 MiB/文件是绝对红线**，50 MiB 是体验警戒线。
- LFS 虽能放宽单文件上限，但 **clone/CI 需联网拉取 LFS 实体**，与「现场完全离线」冲突，`[设计选择]` **不采用**。
- checkpoint 体积可用「参数规模 × 2~3」粗估（PyTorch 官方口径）；Demo checkpoint 的硬指标是**单文件可随仓库克隆**，而非某个绝对 MB 数。
- HF 的 GB~TB 量级建议远超本项目，仅作「大仓库上限惯例」参考，不作约束。

---

## 2. 可复现性 / 产物评审清单（与产物分级/体积/续跑相关条目）

| 依据 | 与本任务相关的条目 | 出处 |
|---|---|---|
| ACM Artifact Review and Badging v1.1（2020-08-24）`[硬标准-评审流程]` | **Available**：公开归档 + DOI/稳定标识 + 许可证；**Functional**：文档化、一致、完整、可执行、有 V&V 证据；**Reusable**：结构清晰、可复用；**Results Reproduced**：他方用其产物复现 | [acm.org](https://www.acm.org/publications/policies/artifact-review-and-badging-current)（经 SIGIR / SIGSIM PADS 页交叉核对） |
| SIGSIM PADS Artifact Evaluation | 必须含 README（环境与执行说明）、license、**论文每张图/表一个可复跑脚本**；评审期望「数小时内」完成 | [sigsim.acm.org](https://sigsim.acm.org/conf/pads/2026/blog/artifact-evaluation) |
| NeurIPS 2022 Paper Checklist `[工程惯例]` | 要有「运行所需的确切命令与环境」「全部训练/实验细节」「算力：worker 类型、内存、单次运行时长」 | [neurips.cc](https://neurips.cc/Conferences/2022/PaperInformation/PaperChecklist) |
| ML Reproducibility Checklist v2.0（Pineau）`[同行评审]` | 报告中心趋势 + 离散度；报告**每个结果的平均运行时长**或能耗；描述计算基础设施；论文与代码作为两份独立产物 | [cs.mcgill.ca](https://www.cs.mcgill.ca/~jpineau/ReproducibilityChecklist.pdf) |

含义：评审友好性直接约束 artifacts 的**可跑时间**与**体积**（要在数小时内、能随仓库拿到）。建议把「单次运行墙钟时长」补进 run metadata——它同时是 §2 清单与 §3 续跑频率决策的输入。`[设计选择]`

---

## 3. 长任务断点续跑惯例

| 系统 | 机制 | 可迁移原则 | 出处 |
|---|---|---|---|
| Snakemake | `--rerun-incomplete`（重跑不完整输出）、`--keep-going`（失败不中断独立分支）、`--keep-incomplete`（失败保留半成品）、`--rerun-triggers {code,input,params,software-env,mtime}` | 用「产物是否完整」判定续跑点；code/config/input 变化即失效缓存 | [snakemake docs](https://snakemake.readthedocs.io/en/stable/executing/cli.html) |
| Nextflow | `-resume`，缓存键由输入与任务代码共同哈希，官方称「similar to checkpointing」 | 续跑判据由 (config, code, input, generation) 共同决定，不能只比代数 | [Seqera docs](https://docs.seqera.io/nextflow/cache-and-resume) |
| Airflow | 「Tasks should ideally be designed to be **idempotent**」；重试会**整体重跑**任务；副作用需 upsert/去重 | 续跑必须幂等：从第 g 代接着跑 == 从第 g 代重跑到结束；对 append-only 文件有直接写策略要求 | [airflow docs](https://airflow.apache.org/docs/apache-airflow/stable/howto/dag-level-retry-via-callback.html) |
| TensorFlow CheckpointManager | `max_to_keep`，超限**最旧优先**删除；`keep_checkpoint_every_n_hours` 额外留存 | 「last-K + oldest-first 淘汰」的权威范式 | [tensorflow.org](https://www.tensorflow.org/api_docs/python/tf/train/CheckpointManager) |
| PyTorch Lightning | `save_top_k`（最优 K 个）、`save_last`、`every_n_epochs` | 「best-K + last」保留范式 | [lightning docs](https://pytorch-lightning.readthedocs.io/en/stable/api/pytorch_lightning.callbacks.ModelCheckpoint.html) |
| PyTorch 通用 checkpoint | 存 `epoch / model_state_dict / optimizer_state_dict / loss` | 状态清单范式（本项目无 optimizer，需替换为演化状态） | [pytorch tutorial](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html) |
| Daly 2004（FGCS, 引用 492）`[同行评审]` | 最优点检间隔随 `sqrt(dump 成本 × MTBF)` 增长 | checkpoint 存在理论最优间隔；但本项目 MTBF 不可知，**不套用公式** | [DOI](https://doi.org/10.1016/j.future.2004.11.016) |

---

## 4. 结果保留 / GC

| 依据 | 机制 | 可迁移原则 | 出处 |
|---|---|---|---|
| MLflow `gc` | 删除先进 `deleted` 生命周期（可恢复），再 `mlflow gc` 永久清；支持 `--older-than` | 两步式「软删 → 按窗口硬清」 | [mlflow docs](https://mlflow.org/docs/latest/cli.html) |
| DVC `gc` | 只删「不再被指定 scope 引用」的缓存；不给 scope 不删；有 `--dry` | GC 必须有显式「保留根」+ dry-run 预览 | [dvc docs](https://doc.dvc.org/command-reference/gc) |
| GitHub Actions retention | 产物/日志默认 90 天自动过期 | 平台默认保留期旁证（本项目不用 CI 存产物） | [docs.github.com](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository) |

---

## 5. 综合推荐（对应四项输出要求）

### (a) artifacts 体积预算
- `[硬标准]` 单文件 `< 100 MiB`（阻断）、`> 50 MiB` 警告、浏览器上传 `≤ 25 MiB`；仓库建议 `< 1 GB`。
- `[工程惯例]` `artifacts/` 总量 `≤ 100 MB`、单文件 `≤ 50 MiB`；需网页上传时 `≤ 25 MiB`。
- `[设计选择]` 不引入 Git LFS（离线冲突）；宁可压小 checkpoint。
- 依据 `[工程惯例]`：checkpoint ≈ 参数体积 × 2~3（PyTorch）。

### (b) checkpoint 保存频率与保留策略
- 频率：**每代结束存一次**（与 `metrics.csv` 逐代追加对齐）；单代墙钟很长时考虑隔代，Daly 公式仅作原理依据 `[同行评审/仅参考]`。
- 保留：**`last + best`**（或 `save_top_k=2~3` + `save_last`），超出最旧优先删 `[工程惯例]`。
- `[设计选择]` `artifacts/` 只冻结 1 个 best demo checkpoint；中间 checkpoint 留在 gitignore 的 `results/`。

### (c) 续跑最小状态清单（`[工程惯例]`）
1. **完整 config 快照**（解析后的最终 yaml，非 diff）
2. **`git_commit.txt`**（含 dirty 标记）
3. **master seed**
4. **代数/步计数** `generation`
5. **当前种群** `population.jsonl`（genome + phenotype，或可重放的编码）
6. **`status ∈ {running, completed, failed}`**
7. **已写指标边界**（`metrics.csv` 末代/行数），保证 append-only 不重写

判据：`config/code/input` 变化即不可续（对齐 Snakemake rerun-triggers 与 Nextflow 缓存键）；续跑须幂等（对齐 Airflow）。

> ⚠️ **需进一步验证**：是否必须额外序列化 RNG state（`random.getstate()` / `np.random.get_state()` / `torch.Generator.get_state()`），取决于 `§10 #6` 的 seed 派生契约。若 `(config, master seed, generation)` 可被确定性重放（core §3 判据），则不必存；否则必须存或实现「每代从 generation 重新派生」。**在 §10 #6 定稿前，实现侧不得自行选定。**

### (d) results 清理规则
- `[项目契约]` `results/**` 已 gitignore，可随时删；无历史体积风险。
- `[工程惯例]` 两步式：软删（标 `deleted`/trash）→ 按窗口硬清；用 dry-run 预览。
- `[设计选择]` GC 根＝「被 `artifacts/` 或论文图表引用的 run」；窗口＝最近 3 次或 30 天。
- 保留：artifacts/ demo（永久）、正式 3 seeds 的小文本（metadata/config/metrics/git_commit）；可清：中间代 checkpoint/plots/大 population。
- ⚠️ 若 §10 #10 把某些 run 纳入 artifacts/，GC 必须同步排除，防止误删冻结证据。

---

## 6. 状态标注与下一步

本主题结论除「GitHub 100 MiB / 1 GB」与「Daly 点检模型」外，**均属工程惯例或设计选择，无单一权威标准**。落地前必须在 `core §10 #10/#11` 显式标注状态（`已定稿`/`草案待确认`/`占位`）后方可被实现依赖。

1. `#10`：先写体积守卫（脚本 + CI），定稿单文件/总量阈值，写入 core §7 与 `.gitignore` 注释。
2. `#11`：先定 `§10 #6` seed 派生契约 → 再判 RNG state 是否需要序列化 → 写 core「run 状态机 + 续跑判据 + GC 规则」。
3. 把「单次运行时长 / 环境」补进 run metadata（对齐 NeurIPS/Pineau 清单）。
4. 在 `experiment/实验与评价体系.md` §5.2（产物字段与 schema 归属）补齐 `metadata.json` 的 `status`/`last_generation` 字段契约（该文阅读问题 #10 已记为未对齐）。
