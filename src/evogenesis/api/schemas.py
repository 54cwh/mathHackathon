"""API contract models (`API与系统工程.md` §4.2/§4.3, R6/R9/R10/R11)。

字段名 snake_case（R6），有对应 `schemas/*.json` 者对齐之。端点集合见
`API与系统工程.md` §4.3 与 `api/API接口.md`（端点 owner）。
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

Environment = Literal["default", "food_rich", "predator_rich", "resource_scarce"]
JobStatusKind = Literal["queued", "running", "done", "failed", "cancelled"]


# --- RFC 7807 problem details (R10) ---------------------------------------
class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None


# --- sessions (R4: nested <= 2 levels, scoped by session) ------------------
class SessionCreate(BaseModel):
    environment: Environment = "food_rich"
    master_seed: int = 0
    arena_config_path: str = "configs/default_arena.yaml"
    model_config_path: str = "configs/default_model.yaml"
    #: 模型驱动会话（`API接口.md` §7.2）：DanioNet 驱动并推送 `brain.activation`；默认
    #: false（ExpertPolicy）。
    model_driven: bool = False
    #: 冻结 demo checkpoint 路径（`pipeline §6`）；仅 `model_driven=true` 时生效：
    #: 直接加载该网络与种群，免重建/免训练。
    checkpoint_path: str | None = None
    #: 初始基因组种群大小（`API接口.md` §1.1）。缺省用 Arena 配置的 `population.n_fish`；
    #: 实际鱼数为其中 viable 的个数（全 non-viable 则 `422`）。演示用小种群（如 16）。
    population_size: int | None = None
    #: **演示用**：其中多少条走 `ExpertPolicy`（规则策略，**无基因组、无自己的网**），
    #: 其余为基因组个体（有 DNA + 自己的 DanioNet）。缺省 0 = 全基因组化；
    #: 须满足 `0 <= expert_fish <= population_size`。
    expert_fish: int | None = None


class SessionSummary(BaseModel):
    session_id: str
    generation: int = 0
    environment: str
    population: int
    running: bool
    master_seed: int
    fish_alive: int
    prey_remaining: int


class SessionEvolutionStep(BaseModel):
    """会话内逐代演化的一步（`API接口.md` §2.3）。

    `summary` 为该代 `GenerationSummary`（键见文档）：`generation` / `n_individuals` /
    `n_viable` / `fitness_mean` / `fitness_std` / `bottleneck` / `event` / `p_A` / `p_B` /
    `phenotype_freq` / `mean_neuron` / `mean_edge` / `mean_tau`。
    """

    summary: dict[str, Any]
    session: SessionSummary


# --- story-mutations -------------------------------------------------------
class StoryMutation(BaseModel):
    genome_id: str
    position: int
    from_base: str
    to_base: str
    tag: str  # e.g. "increases_prey_bias"


# --- genomes / mutations (R3: action as noun subresource) ------------------
class GenomeCreate(BaseModel):
    seed: int | None = None  # 缺省用参考种子（`API接口.md` §2.3）


class GenomeRecord(BaseModel):
    genome_id: str
    chromosome_pairs: list[dict[str, str]]
    lineage: str | None = None


class MutationRequest(BaseModel):
    position: int = Field(ge=0)
    base: Literal["A", "C", "G", "T"]


class MutationResult(BaseModel):
    genome_id: str
    new_genome_id: str
    diff: dict[str, Any]


# --- developments ----------------------------------------------------------
class DevelopmentTraceSample(BaseModel):
    """发育轨迹的一个采样点（`API接口.md` §2.3；`交互与可视化.md` §4 的动画顺序）。

    键集合固定，便于前端把各阶段画成同一条时间线；该阶段不存在的量记 ``None``（缺失 ≠ 0）。
    阶段顺序：``grn``（0..development_steps）→ ``proliferate`` → ``fate`` → ``connectome``（`§4`）。
    """

    stage: Literal["grn", "proliferate", "fate", "connectome"]
    #: grn 阶段为步序号（0..development_steps）；proliferate 为轮次；connectome 为 0。
    step: int
    n_neurons: int
    n_divisions: int | None = None
    n_edges: int | None = None
    mean_abs: float
    max_abs: float
    #: 逐神经元坐标（单位方域，`RGCD §3`）；供前端画真实几何。
    positions: list[list[float]] | None = None
    #: 逐神经元 fate（六类序号）；仅 connectome 阶段确定，早期为 null。
    cell_type: list[int] | None = None
    #: 真实邻接表（边对 `[i, j]`，指向 `positions` 的下标）；仅 connectome 阶段。
    edges: list[list[int]] | None = None
    #: 逐神经元表达强度 `expr[i] = mean_d |g_id|`（`RGCD §4`）。
    #: `grn` / `proliferate` / `fate` / `connectome` 阶段均有值。
    expr: list[float] | None = None
    #: 逐个体 fate 置信度 `max_k z_ik`（`RGCD §6`）；仅 `fate` / `connectome` 阶段。
    fate_conf: list[float] | None = None
    #: 连接概率场 `p_ij = σ(ℓ_ij)`（`RGCD §8`）的模型真值矩阵（`N×N` 行主序，`[0,1]`，
    #: 无自环时对角 0）；仅 `connectome` 阶段。前端据此画「两幕真值」第一幕（第二幕 = `edges`）。
    probs: list[list[float]] | None = None


class DevelopmentRequest(BaseModel):
    genome_id: str
    seed: int = 0


class DevelopmentResult(BaseModel):
    genome_id: str
    dev_trace: dict[str, Any]
    phenotype: dict[str, Any]
    #: 仅 `?with_trace=true` 时给出（`API接口.md` §2.3）：逐阶段发育轨迹。
    trace: list[DevelopmentTraceSample] | None = None


# --- breedings -------------------------------------------------------------
class BreedingRequest(BaseModel):
    genome_a: str
    genome_b: str
    n_offspring: int = 1


class BreedingResult(BaseModel):
    offspring: list[str]
    meiosis_trace: dict[str, Any]


# --- lab individuals (API接口.md §1.11) ---------------------------------------
class IndividualSpawn(BaseModel):
    """把实验室个体追加进会话 Arena 的请求体。"""

    genome_id: str
    #: 发育随机种子（`DevelopmentRequest.seed` 同口径）。
    seed: int = 0


class SpawnedIndividual(BaseModel):
    """已追加个体的摘要（发育产物 + Arena 侧稳定 ID）。"""

    fish_id: str
    genome_id: str
    generation: int
    viable: bool
    n_neurons: int
    n_edges: int
    tau_mean: float
    #: 六类 fate 计数（键 = fate 序号 0..5）。
    cell_type_counts: dict[str, int] = Field(default_factory=dict)


# --- fish card (API与系统工程.md §4.3) -------------------------------------------
class FishCard(BaseModel):
    fish_id: str
    generation: int
    genome_id: str
    viable: bool
    energy: float
    size: float
    fitness: float | None = None
    cell_counts: dict[str, int] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)


# --- snapshot (API与系统工程.md §4.3: 全场快照) ------------------------------------
class Snapshot(BaseModel):
    session_id: str
    step: int
    fish: dict[str, dict[str, Any]]  # transforms + energy
    prey: dict[str, dict[str, Any]]  # pos + size + alive
    predators: dict[str, dict[str, Any]]  # pos + size
    obstacles: list[dict[str, Any]]  # pos + radius
    events: list[dict[str, Any]]


# --- leaderboard -----------------------------------------------------------
class LeaderboardEntry(BaseModel):
    rank: int
    fish_id: str
    captures: int
    survival_steps: int
    energy: float
    fitness: float | None = None


class Leaderboard(BaseModel):
    session_id: str
    generation: int
    entries: list[LeaderboardEntry]


# --- environmental selection (Experiment F; `API接口.md` §2.2) ---------------
class EnvironmentalSelectionLaunch(BaseModel):
    """环境选择实验（Experiment F）启动请求：展开为 N 个 `ExperimentRun`。

    `population_size` / `steps` 为**演示用**可选覆盖（缺省 None ⇒ 用
    `configs/evolution.yaml::population_size`(48) 与 arena 的 `episode_steps`(600)）：现场演示时
    调小（如 12 / 150）可让一轮在几秒内跑完；正式实验不传。
    """

    name: str
    seeds: list[int]
    environment: Environment = "food_rich"
    generations: int = 10
    population_size: int | None = None
    steps: int | None = None


class EnvironmentalSelectionSummary(BaseModel):
    experiment_id: str
    name: str
    status: JobStatusKind
    seeds: list[int]


class EnvironmentalSelectionDetail(BaseModel):
    experiment_id: str
    name: str
    status: JobStatusKind
    seeds: list[int]
    results: dict[str, Any] = Field(default_factory=dict)


# --- runs (磁盘 run 只读；`API接口.md` §2.4) ---------------------------------
class RunSummary(BaseModel):
    """`results/runs/<run_id>/` 的一条索引（来自 `metadata.json` + `evolution.jsonl` 行数）。"""

    run_id: str
    experiment_id: str
    seed: int | None = None
    status: str = "unknown"
    created_at: str = ""
    #: `evolution.jsonl` 行数（= 已跑代数）；无该文件时 None。
    generations: int | None = None


class RunFitnessDistribution(BaseModel):
    """某一代的**逐个体** fitness（`generations/g<NNNN>/fitness.jsonl`），用于分布直方图。"""

    generation: int
    values: list[float]


class RunEvolution(BaseModel):
    """一个 run 的逐代指标；`generations` 原样透传 `evolution.jsonl` 行（字段随 producer）。"""

    run_id: str
    experiment_id: str
    seed: int | None = None
    generations: list[dict[str, Any]]
    fitness: list[RunFitnessDistribution] = Field(default_factory=list)


# --- jobs ------------------------------------------------------------------
class JobStatus(BaseModel):
    job_id: str
    status: JobStatusKind
    progress: float = 0.0  # 0..1
    detail: dict[str, Any] = Field(default_factory=dict)


# --- pagination (R9) -------------------------------------------------------
class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None = None


# --- WebSocket envelope (R11) ----------------------------------------------
class WSMessage(BaseModel):
    v: int = 1
    type: str  # dot-hierarchical: arena.fish_state, ...
    seq: int
    ts: float
    payload: dict[str, Any] = Field(default_factory=dict)
