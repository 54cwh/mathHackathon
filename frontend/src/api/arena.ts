/** Arena API client -- mirrors backend evogenesis/api/schemas.py (doc 10). */

export type Environment = "food_rich" | "predator_rich" | "resource_scarce";

/** Frozen demo master seed -- one source of truth for the whole live demo. */
export const MASTER_SEED = 250927;

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

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? `HTTP ${res.status}`);
  }
  // 204 No Content carries no body (e.g. DELETE /v1/sessions/{id}).
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function createSession(
  masterSeed = MASTER_SEED,
  environment: Environment = "food_rich",
): Promise<SessionSummary> {
  return req<SessionSummary>("/v1/sessions", {
    method: "POST",
    body: JSON.stringify({ master_seed: masterSeed, environment }),
  });
}

export function getSession(sessionId: string): Promise<SessionSummary> {
  return req<SessionSummary>(`/v1/sessions/${sessionId}`);
}

export function resetSession(sessionId: string): Promise<SessionSummary> {
  return req<SessionSummary>(`/v1/sessions/${sessionId}/reset`, { method: "POST" });
}

export function deleteSession(sessionId: string): Promise<void> {
  return req<void>(`/v1/sessions/${sessionId}`, { method: "DELETE" });
}

export function release(sessionId: string, steps = 1, useExpert = true): Promise<SessionSummary> {
  return req<SessionSummary>(
    `/v1/sessions/${sessionId}/release?steps=${steps}&use_expert=${useExpert}`,
    { method: "POST" },
  );
}

export function getSnapshot(sessionId: string): Promise<ArenaSnapshot> {
  return req<ArenaSnapshot>(`/v1/sessions/${sessionId}/snapshot`);
}
