/** Arena REST client — the single REST entry point (`api/API接口.md` §1). */

import { req } from "./http";
import type { ArenaSnapshot, Environment, SessionSummary } from "./types";

export type { ArenaEvent, ArenaSnapshot, Environment, FishState, ObstacleState, PredatorState, PreyState, SessionSummary } from "./types";

/** Frozen demo master seed -- one source of truth for the whole live demo. */
export const MASTER_SEED = 250927;

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
