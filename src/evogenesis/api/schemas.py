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


class SessionSummary(BaseModel):
    session_id: str
    generation: int = 0
    environment: str
    population: int
    running: bool
    master_seed: int
    fish_alive: int
    prey_remaining: int


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
class DevelopmentRequest(BaseModel):
    genome_id: str
    seed: int = 0


class DevelopmentResult(BaseModel):
    genome_id: str
    dev_trace: dict[str, Any]
    phenotype: dict[str, Any]


# --- breedings -------------------------------------------------------------
class BreedingRequest(BaseModel):
    genome_a: str
    genome_b: str
    n_offspring: int = 1


class BreedingResult(BaseModel):
    offspring: list[str]
    meiosis_trace: dict[str, Any]


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
    """环境选择实验（Experiment F）启动请求：展开为 N 个 `ExperimentRun`。"""

    name: str
    seeds: list[int]
    environment: Environment = "food_rich"
    generations: int = 10


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
