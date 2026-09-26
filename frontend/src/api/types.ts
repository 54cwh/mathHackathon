/**
 * Backend contract types (snake_case) — the **single definition site** for
 * REST/WS payload shapes. Mirrors `api/API接口.md` and `schemas/`.
 */

/** Environment id set (owner: `experiment §4`; must match `schemas/`). */
export type Environment = "default" | "food_rich" | "predator_rich" | "resource_scarce";

export interface SessionSummary {
  session_id: string;
  generation: number;
  environment: string;
  population: number;
  running: boolean;
  master_seed: number;
  fish_alive: number;
  prey_remaining: number;
}

export interface FishState {
  x: number;
  y: number;
  heading: number;
  speed: number;
  energy: number;
  size: number;
  alive: boolean;
}

export interface PreyState {
  x: number;
  y: number;
  size: number;
  alive: boolean;
}

export interface PredatorState {
  x: number;
  y: number;
  size: number;
}

export interface ObstacleState {
  x: number;
  y: number;
  radius: number;
}

export interface ArenaEvent {
  seq: number;
  type: string;
  step: number;
  payload: Record<string, unknown>;
}

export interface ArenaSnapshot {
  session_id: string;
  step: number;
  fish: Record<string, FishState>;
  prey: Record<string, PreyState>;
  predators: Record<string, PredatorState>;
  obstacles: ObstacleState[];
  events: ArenaEvent[];
}

/** DNA bases (`genome §3.1`); `MutationRequest.base` is restricted to these. */
export type Base = "A" | "C" | "G" | "T";

/**
 * The six development cell types (`development` 契约). `FishCard.cell_counts`
 * carries these as keys; typed as `Record<string, number>` because the backend
 * declares an open dict, not a closed key set.
 */
export type CellType =
  | "sensory"
  | "prey"
  | "threat"
  | "memory"
  | "inhibitory"
  | "motor";

/** Job lifecycle (`api/schemas.py::JobStatusKind`). */
export type JobStatusKind = "queued" | "running" | "done" | "failed" | "cancelled";

export interface JobStatus {
  job_id: string;
  status: JobStatusKind;
  progress: number; // 0..1
  detail: Record<string, unknown>;
}

/** Cursor pagination (`API接口.md` §0/R9). */
export interface Page<T> {
  items: T[];
  next_cursor: string | null;
}

/** Session create body (`api/schemas.py::SessionCreate`). */
export interface SessionCreate {
  environment: Environment;
  master_seed: number;
  arena_config_path: string;
  model_config_path: string;
  /** true ⇒ DanioNet drives the fish and `brain.activation` is pushed (`API接口.md` §7.2). */
  model_driven: boolean;
  /** Frozen demo checkpoint (`pipeline §6`); only honoured when `model_driven`. */
  checkpoint_path: string | null;
  /** 初始基因组种群大小（`API接口.md` §1.1）；缺省用 Arena 配置。 */
  population_size?: number | null;
}

/** 已追加进会话 Arena 的实验室个体（`API接口.md` §1.11）。 */
export interface SpawnedIndividual {
  /** 稳定 ID：`fish_id == genome_id`。 */
  fish_id: string;
  genome_id: string;
  generation: number;
  viable: boolean;
  n_neurons: number;
  n_edges: number;
  tau_mean: number;
  cell_type_counts: Record<string, number>;
}

/** Fish Card metrics (`API接口.md` §1.5；字段已定稿). */
export interface FishCardMetrics {
  alive: boolean;
  captures: number;
  encounters: number;
  predator_encounters: number;
  escape_successes: number;
  survival_steps: number;
  // 实验室个体（`API接口.md` §1.11）额外带上连接组摘要；默认 Arena 鱼没有这三项。
  n_neurons?: number;
  n_edges?: number;
  tau_mean?: number;
}

/** Fish Card (`API接口.md` §1.5). */
export interface FishCard {
  fish_id: string;
  generation: number;
  genome_id: string;
  viable: boolean;
  energy: number;
  size: number;
  fitness: number | null;
  cell_counts: Record<string, number>;
  metrics: FishCardMetrics;
}

export interface LeaderboardEntry {
  rank: number;
  fish_id: string;
  captures: number;
  survival_steps: number;
  energy: number;
  fitness: number | null;
}

export interface Leaderboard {
  session_id: string;
  generation: number;
  entries: LeaderboardEntry[];
}

// --- genome lab (`API接口.md` §2.3) ----------------------------------------

export interface GenomeCreate {
  /** Omitted ⇒ reference seed (`configs/demo_seed.yaml`). */
  seed?: number | null;
}

export interface GenomeRecord {
  genome_id: string;
  chromosome_pairs: Record<string, string>[];
  lineage: string | null;
}

export interface MutationRequest {
  /** Linear over the diploid genome, `[0, 512)` (`API接口.md` §2.3, 已定稿). */
  position: number;
  base: Base;
}

/** Single-point free edit diff (`API接口.md` §2.3). */
export interface MutationDiff {
  position: number;
  from_base: string;
  to_base: string;
}

export interface MutationResult {
  genome_id: string;
  new_genome_id: string;
  diff: MutationDiff;
}

export interface DevelopmentRequest {
  genome_id: string;
  seed: number;
}

/** `dev_trace` fields (`API接口.md` §2.3, 实现语义已定稿). */
export interface DevelopmentTrace {
  /** RGCD affinity `q`, length 8 (`RGCD数学模型.md`). */
  q: number[];
  /** Cell-type histogram; keys are the backend's `str(int)` labels. */
  cell_type_counts: Record<string, number>;
  tau: { mean: number; std: number };
  n_neurons: number;
  n_edges: number;
  viable: boolean;
  viability_reason: string;
}

/** `phenotype` summary fields (`API接口.md` §2.3, 实现语义已定稿). */
export interface DevelopmentPhenotype {
  n_neurons: number;
  n_edges: number;
  edge_density: number;
  tau_mean: number;
  tau_std: number;
  viable: boolean;
}

/** 发育轨迹采样点（`API接口.md` §2.3；`交互与可视化.md` §4 的动画顺序）。 */
export interface DevelopmentTraceSample {
  stage: "grn" | "proliferate" | "connectome";
  step: number;
  n_neurons: number;
  /** 仅 proliferate 阶段。 */
  n_divisions: number | null;
  /** 仅 connectome 阶段。 */
  n_edges: number | null;
  mean_abs: number;
  max_abs: number;
  /** 逐神经元坐标（单位方域，`RGCD §3`）——画**真实几何**用。 */
  positions: [number, number][] | null;
  /** 逐神经元 fate（六类序号）；仅 connectome 阶段确定，早期为 null。 */
  cell_type: number[] | null;
  /** 真实邻接表（边对 `[i, j]`，指向 `positions` 下标）；仅 connectome 阶段。 */
  edges: [number, number][] | null;
}

export interface DevelopmentResult {
  genome_id: string;
  dev_trace: DevelopmentTrace;
  phenotype: DevelopmentPhenotype;
  /** 仅 `?with_trace=true` 时给出。 */
  trace?: DevelopmentTraceSample[] | null;
}

export interface BreedingRequest {
  genome_a: string;
  genome_b: string;
  n_offspring: number;
}

export interface BreedingResult {
  offspring: string[];
  meiosis_trace: Record<string, unknown>;
}

// --- environmental selection / Experiment F (`API接口.md` §2.2) ------------

export interface EnvironmentalSelectionLaunch {
  name: string;
  seeds: number[];
  environment: Environment;
  generations: number;
}

export interface EnvironmentalSelectionSummary {
  experiment_id: string;
  name: string;
  status: JobStatusKind;
  seeds: number[];
}

export interface EnvironmentalSelectionRun {
  seed: number;
  run_dir: string;
  /** 实现附加字段（`API接口.md` §2.2 的表只列 seed/run_dir；实测有这两项）。 */
  generations_run?: number;
  bottleneck?: boolean;
}

/** `results` 实测形状（`environment`/`generations`/`job_id` + `runs`）。 */
export interface EnvironmentalSelectionResults {
  environment?: string;
  generations?: number;
  job_id?: string;
  runs: EnvironmentalSelectionRun[];
}

export interface EnvironmentalSelectionDetail extends EnvironmentalSelectionSummary {
  results: EnvironmentalSelectionResults;
}

// --- runs（磁盘 run 只读；`API接口.md` §2.4） -------------------------------

export interface RunSummary {
  run_id: string;
  experiment_id: string;
  seed: number | null;
  status: string;
  created_at: string;
  /** `evolution.jsonl` 行数（= 已跑代数）；无该文件时 null。 */
  generations: number | null;
}

/**
 * `evolution.jsonl` 的一代。字段随 producer 版本变化（老 run 缺 `p_A`/`mean_*` 等），
 * 故 §8 需要的项一律可选——**缺失就显示"未记录"，不补 0**（不许编造）。
 */
export interface RunGeneration {
  generation: number;
  n_individuals?: number;
  n_viable?: number;
  fitness_mean?: number;
  fitness_std?: number;
  bottleneck?: boolean;
  /** 环境变更标记（非空即发生环境切换）。 */
  event?: string | null;
  p_A?: number;
  p_B?: number;
  phenotype_freq?: Record<string, number>;
  mean_neuron?: number;
  mean_edge?: number;
  mean_tau?: number;
}

export interface RunFitnessDistribution {
  generation: number;
  values: number[];
}

export interface RunEvolution {
  run_id: string;
  experiment_id: string;
  seed: number | null;
  generations: RunGeneration[];
  fitness: RunFitnessDistribution[];
}

export interface Health {
  status: string;
  /** 能力位：`true` = 后端 `release` 支持手动动作（`API接口.md` §1.10）。
   *  旧进程缺该字段（FastAPI 静默忽略多余查询参数）⇒ 前端须显式提示"后端版本落后"。 */
  manual_control?: boolean;
}
