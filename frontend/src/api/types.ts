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
