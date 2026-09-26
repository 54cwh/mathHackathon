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
  metrics: Record<string, unknown>;
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

export interface MutationResult {
  genome_id: string;
  new_genome_id: string;
  diff: Record<string, unknown>;
}

export interface DevelopmentRequest {
  genome_id: string;
  seed: number;
}

export interface DevelopmentResult {
  genome_id: string;
  dev_trace: Record<string, unknown>;
  phenotype: Record<string, unknown>;
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

export interface EnvironmentalSelectionDetail extends EnvironmentalSelectionSummary {
  results: Record<string, unknown>;
}

export interface Health {
  status: string;
}
