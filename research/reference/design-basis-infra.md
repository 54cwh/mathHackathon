# EvoGenesis 工程契约设计依据：config / logging / registry / io

> 检索时间：2026-09-26　｜　配套机器可读文件：`research/reference/design-basis-infra.json`
> 用途：为 EvoGenesis（Python 3.12 / PyTorch / FastAPI；产物落 `results/runs/<experiment_id>/`；跨语言契约在 `schemas/`）确定 config、logging/tracking、registry、io 四类工程契约的国际标准或权威实践依据。
> 来源约定：**spec**＝国际标准/开放规范；**docs**＝官方产品文档；**repo**＝官方代码仓库；**book**＝官方书籍。GitHub star 与 SPDX 许可证均为 2026-09-26 用 `gh` CLI 实测。凡『权威原文』与『本项目综合推荐』混同处，正文标注 `[权威]` 或 `[设计推荐-待验证]`。

---

## 一句话结论

- **config**：用 **Hydra 1.x + OmegaConf** 做文件合成与 CLI 覆盖，用 **Pydantic Settings** 做 env/secrets 与类型校验，用 **JSON Schema Draft 2020-12** 做 `schemas/` 跨语言契约。`[权威]` CLI > 选中 config 文件 > 字段默认。**完整四层序 `CLI > env > file > default` 没有单一权威原文同时覆盖 env 层**，属本项目设计决定，必须先写进 `configs/` 文档定稿后才能依赖。
- **logging**：**structlog + JSONRenderer** 落 **JSONL**；字段模型对齐 **OpenTelemetry Logs Data Model（Stable）** 的 `Timestamp / SeverityNumber / Body / Resource`，需要时再加 ECS 的 `@timestamp`（必填）、`log.level`（core）。
- **tracking**：字段命名对齐 **MLflow Tracking**（`run_id / experiment_id / status / start_time / end_time / metrics / params / tags / artifacts`）。MLflow 可本地 file store + sqlite 离线跑，**推荐**；**W&B 依赖云端，与现场离线冲突，不建议**。
- **registry**：采用 **MLflow Model Registry** 语义——稳定名称 + 不可变版本 + 可变 alias（`champion`/`current`）+ tags + 血缘 `run_id`；离线实现用 **content-addressable 文件存储 + JSON 索引**（依据 Git Objects 与 DVC cache）。
- **io 边界**：轨迹/事件流 → **JSONL**；指标表 → 小 CSV / 大 Parquet；大 N 维数组 → **HDF5 或 Zarr v3**；浮点 → **IEEE 754** 的 float32/float64；时间戳 → **ISO 8601-1:2019 / RFC 3339（UTC，`Z`）**。

---

## 一、config 契约

### 1.1 权威依据

| 依据 | 关键原文 | 出处 |
|---|---|---|
| Hydra — The Defaults List | “the content of a config is overriding the content of configs in the defaults list”；Config Group 可由命令行 `python my_app.py server/db=sqlite` 覆盖；“the last one, in depth first order, wins” | [hydra.cc/docs/advanced/defaults_list](https://hydra.cc/docs/advanced/defaults_list/) |
| Hydra — Basic Override syntax | CLI override DSL：`key=value` 改配置对象，`group=option` 改 defaults list，`+`/`++` 追加、`~` 删除 | [hydra.cc/docs/advanced/override_grammar/basic](https://hydra.cc/docs/advanced/override_grammar/basic/) |
| OmegaConf — Usage | 官方示例把 CLI 配置放 `merge` 最后：`OmegaConf.merge(base_conf, second_conf, cli_conf)`，CLI 胜出（last wins） | [omegaconf.readthedocs.io/en/latest/usage.html](https://omegaconf.readthedocs.io/en/latest/usage.html) |
| Pydantic Settings | 源优先级（高→低）：CLI（启用 `cli_parse_args` 时）> 初始化参数 > 环境变量 > `.env` > secrets 目录 > 字段默认值；可 `settings_customise_sources` 改序 | [pydantic.dev/docs/validation/latest/concepts/pydantic_settings](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings) |
| 12-Factor App III. Config | “strict separation of config from code”；“stores config in environment variables”；env var 彼此正交 | [12factor.net/config](https://12factor.net/config) |
| JSON Schema Draft 2020-12 | `type`/`required`/`properties`/`prefixItems`/`unevaluatedProperties` 等断言语义；2020-12 与 draft-07 在 `$ref` 同级关键字、`items` 语义上不同 | [json-schema.org/draft/2020-12](https://json-schema.org/draft/2020-12) |

### 1.2 推荐（可直接落地）

1. **合成与覆盖**：`configs/` 用 Hydra defaults list 组织多层 yaml；命令行用 Hydra/OmegaConf override；env 与 secrets（如 API key、本地路径）走 Pydantic Settings；`schemas/` 用 JSON Schema 2020-12 定义键名与类型。
2. **优先级**：
   - `CLI 覆盖 > 选中 config 文件 > 字段默认`　`[权威]`（Hydra Defaults List + OmegaConf merge 顺序）。
   - `env > .env > secrets > 默认`　`[权威]`（Pydantic Settings 明文）。
   - **合成四层序 `CLI > env > file > default`：`[设计推荐-待验证]`** —— 两个权威体系各自只覆盖一半，交集序无单一原文。**这是阻断项**：必须先写入 `configs/` 或 `docs/参数总表` 并标注 `已定稿`，代码不得自行选定。
3. **校验**：所有 config 文件先过 JSON Schema，再进 Pydantic 类型模型；禁止「文档未定义、由实现自选」的默认值进入正式实验（呼应 AGENTS.md「禁止 AI 填空」）。
4. **风险点**：Hydra 与 Pydantic Settings 的 CLI 解析可能互相抢夺 `sys.argv`（Pydantic 仅在 `cli_parse_args=True` 时参与）。二选一，不要同时启用两层 CLI 解析。

---

## 二、logging / tracking

### 2.1 权威依据

| 依据 | 关键原文 | 出处 |
|---|---|---|
| OpenTelemetry Logs Data Model（Stable） | 字段：`Timestamp`(uint64 ns since epoch)、`ObservedTimestamp`、`TraceId`、`SpanId`、`TraceFlags`、`SeverityText`、`SeverityNumber`、`Body`、`Resource`、`InstrumentationScope`、`Attributes`、`EventName` | [opentelemetry.io/docs/specs/otel/logs/data-model](https://opentelemetry.io/docs/specs/otel/logs/data-model/) |
| OTel 严重度分段 | TRACE 1–4 / DEBUG 5–8 / INFO 9–12 / WARN 13–16 / ERROR 17–20 / FATAL 21–24；`SeverityNumber=0` 表未指定；“ERROR (numeric 17) or higher” 即错误事件 | 同上 |
| OTel 格式映射 Appendix | Zap：`ts→Timestamp`、`level→Severity`、`msg→Body`、其余→`Attributes`；可直接指导 structlog 字段命名 | [data-model-appendix](https://opentelemetry.io/docs/specs/otel/logs/data-model-appendix/) |
| structlog | 生产建议 `processors` 链末端 `JSONRenderer()`；开发用 `ConsoleRenderer()`；`dict_tracebacks` 结构化堆栈 | [structlog standard-library](https://www.structlog.org/en/stable/standard-library.html)、[best-practices](https://www.structlog.org/en/stable/logging-best-practices.html) |
| ECS | `@timestamp` 为 “Required field for all events”（date，例 `2016-05-23T08:05:34.853Z`）；`log.level` 为 core，且标注对应 OTel `severity_text` | [elastic.co/docs/reference/ecs](https://www.elastic.co/docs/reference/ecs)、[ecs-log](https://www.elastic.co/docs/reference/ecs/ecs-log) |
| MLflow Tracking | “Each run records metadata (metrics, parameters, start and end times) and artifacts”；`start_run`/`log_param`/`log_metric`/`log_input` | [mlflow.org/docs/latest/ml/tracking](https://mlflow.org/docs/latest/ml/tracking) |
| MLflow REST API | run/experiment 字段：`run_id`、`experiment_id`、`status`、`start_time`、`end_time`、`metrics`、`params`、`tags`、`artifacts` | [mlflow.org/docs/latest/rest-api.html](https://mlflow.org/docs/latest/rest-api.html) |
| W&B | `wandb.init()` 建 run；`run.config`＝输入超参，`run.log()`＝过程指标，artifacts＝模型/表 | [docs.wandb.ai/models/track](https://docs.wandb.ai/models/track) |
| DVC Internal Files | “The DVC cache is a content-addressable storage (by default in `.dvc/cache`)”；支持本地 remote | [doc.dvc.org/.../internal-files](https://doc.dvc.org/user-guide/project-structure/internal-files) |
| JSON Lines | UTF-8、禁 BOM；每行一个合法 JSON 值（空行非法）；行终止 `\n` | [jsonlines.org](https://jsonlines.org/) |

### 2.2 推荐（可直接落地）

1. **日志实现**：structlog 配置共享 processors，生产/落盘接 `JSONRenderer`，本地 tty 接 `ConsoleRenderer`；运行日志写 `results/runs/<experiment_id>/logs.jsonl`（JSONL：UTF-8、无 BOM、每行一个 JSON 对象、`\n`）。
2. **字段最小集（建议必填）**：`timestamp`、`level`、`event`、`experiment_id`、`run_id`、`component`、`seed`；异常追加 `exception.type` / `exception.message` / stack。
   - `timestamp` 落 ISO 8601 / RFC 3339（UTC，`Z`）；若与 OTel 生态对接，内部可存 uint64 纳秒 epoch。
   - `level` 映射到 OTel `SeverityNumber`（INFO=9、WARN=13、ERROR=17…）。
   - **此必填集是综合 OTel 字段与项目 ID 约定得出，非规范原文** → `[设计推荐-待验证]`，落文档定稿后依赖。
3. **tracking**：字段名对齐 MLflow；`results/runs/<experiment_id>/` 下放 `config.yaml`（合成后已解析配置）、`metrics.csv`、`artifacts/`、`logs.jsonl`。本地离线可用 MLflow file store + sqlite，或自研薄 tracker 复用同一字段名。
4. **不建议**：W&B 作为现场依赖（云端同步，违反「现场完全离线」）。DVC 可离线（本地 remote），仅作参考用于数据/产物的内容寻址。

---

## 三、registry

### 3.1 权威依据

| 依据 | 关键原文 | 出处 |
|---|---|---|
| MLflow Model Registry | “A registered model has a unique name, contains versions, aliases, tags, and other metadata”；提供血缘“which MLflow experiment and run produced the model” | [mlflow.org/docs/latest/ml/model-registry](https://mlflow.org/docs/latest/ml/model-registry) |
| MLflow Registry Workflows | 用可变 model version aliases（如 `champion`）与 tags 取代固定 stages；`models:/<registered model name>@champion` 可解析 | [.../model-registry/workflow](https://mlflow.org/docs/latest/ml/model-registry/workflow) |
| Pro Git — Git Objects | “Git is a content-addressable filesystem … a simple key-value data store”；内容哈希即唯一 key | [git-scm.com/book/.../Git-Internals-Git-Objects](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects) |
| DVC Internal Files | cache 为 content-addressable storage，按内容哈希寻址、去重 | [doc.dvc.org/.../internal-files](https://doc.dvc.org/user-guide/project-structure/internal-files) |

### 3.2 推荐（可直接落地）

1. **语义对齐 MLflow**：注册对象用稳定 ID（`fish_id`/`genome_id`/`experiment_id`/`model_name`），版本不可变，别名可变（`champion`/`current`/`best`），tags 存评估状态，血缘字段 `source_run_id` / `source_experiment_id`。
2. **离线实现** `[设计推荐-待验证]`：产物按内容哈希（如 sha256）存入 content-addressable 目录，另维护 JSON 注册索引：

   ```json
   { "stable_id": "...", "version": 3, "content_hash": "sha256:...",
     "path": "artifacts/registry/<sha256>", "created_at": "2026-09-26T10:00:00Z",
     "tags": {"status": "validated"}, "lineage_run_id": "..." }
   ```

   **待定项**：哈希算法、索引 schema、与 `schemas/` 的契约字段需先写入文档并定稿。
3. **命名纪律**：沿用 AGENTS.md 的稳定 ID（`fish_id` / `genome_id` / `generation_id` / `experiment_id` / `environment_id`）；前端不得用数组下标当 identity。

---

## 四、io / 序列化

### 4.1 格式边界

| 数据类型 | 推荐格式 | 依据 |
|---|---|---|
| 异质、追加、逐条流式的事件 / 轨迹 | **JSONL** | [jsonlines.org](https://jsonlines.org/)：UTF-8、每行一个 JSON 值、`\n` |
| 小规模表列指标 | **CSV** | 通用、可读；本项目 `results/runs/*/metrics.csv` 沿用 |
| 大规模 / 需类型与压缩的表列 | **Parquet** | 列式、row group、逻辑类型（[File Format](https://parquet.apache.org/docs/file-format/)、[Logical Types](https://parquet.apache.org/docs/file-format/types/logicaltypes/)）；FLOAT=IEEE 32-bit、DOUBLE=IEEE 64-bit（[parquet-format](https://github.com/apache/parquet-format)） |
| 大体量同构 N 维数组 | **HDF5** 或 **Zarr v3** | HDF5：dataset + datatype + dataspace，group 层级（[OGC HDF5 Core Standard](https://docs.ogc.org/is/18-043r3/18-043r3.html)）；Zarr v3：N 维分块数组、codec 流水线、存储无关（[Zarr v3 spec](https://zarr-specs.readthedocs.io/en/latest/v3/core/index.html)） |
| 浮点 | **float32 / float64（IEEE 754-2019）** | [IEEE SA 754-2019](https://standards.ieee.org/standard/754-2019.html)：binary/decimal 交换与算术格式、异常与默认处理 |
| 时间戳 | **ISO 8601-1:2019 / RFC 3339（UTC，`Z`）** | [ISO 8601-1:2019](https://www.iso.org/standard/70907.html)；[RFC 3339](https://www.rfc-editor.org/info/rfc3339)（时区不可省、大写 T/Z，被 RFC 9557 更新） |

### 4.2 推荐（可直接落地）

1. **轨迹用 JSONL，指标表用 CSV/Parquet**。JSONL 逐条可流式、对 shell 友好；当指标行数大或需列裁剪/压缩时换 Parquet。
2. **JSON 不承载高精度浮点数组**：JSON 无二进制浮点与精度保证，需比特级复现的数组落 `npz`/HDF5/Parquet，JSONL 只放元数据与低风险标量。
3. **时间戳统一 UTC + `Z`**：JSON 内用 `2026-09-26T10:00:00Z`（小数秒可选）；OTel 日志内部可用 uint64 纳秒；Parquet 用 TIMESTAMP 逻辑类型（INT64）。
4. **大数组二选一**：单文件层级 + 丰富 attribute → HDF5；分块并行写、对象存储、云原生 → Zarr v3。两者皆需在模块文档写明 chunk/shape/dtype 契约。

---

## 五、未找到 / 需继续验证（不用低质结果充数）

1. **config 四层优先级无单一权威原文**：`CLI > env > file > default` 由 Hydra/OmegaConf（CLI>file>default）与 Pydantic（env>dotenv>secrets>default）拼接而成，属 **`[设计推荐-待验证]`**，必须先落文档定稿。这是本次唯一的阻断级风险点。
2. **JSON Lines 是社区规范**：jsonlines.org 非 IETF RFC；若评委要求正式标准，需改用 RFC 8259 JSON + 自定义 framing，或评估其他新行分隔格式。
3. **ISO 8601-1:2019 与 IEEE 754-2019 为付费标准**：本次只核实官方摘要/OBP 页面与元数据（发布时间、范围），**未核对正文条款编号**，论文引用时应只引摘要级断言。
4. **未实测项**：MLflow 本地 file store 的跨版本字段稳定性、Parquet/Zarr/HDF5 的 Python 库离线安装体积与依赖树，本次均未跑通验证；需在 `scripts/` 或本机 `uv` 环境确认后回写文档。
5. **旁证类来源（未作为结论依据）**：检索中出现的 Medium / 博客 / 视频教程（如 W&B、MLflow 实践帖）仅用于交叉印证，未采信为权威出处；所有结论均来自上表官方来源。
