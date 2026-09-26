/** Arena REST client — the single REST entry point (`api/API接口.md` §1). */

import { req } from "./http";
import type {
  ArenaSnapshot,
  SpawnedIndividual,
  Environment,
  FishCard,
  Leaderboard,
  SessionCreate,
  SessionSummary,
} from "./types";

export type {
  ArenaEvent,
  ArenaSnapshot,
  SpawnedIndividual,
  Environment,
  FishCard,
  FishState,
  JobStatus,
  Leaderboard,
  LeaderboardEntry,
  ObstacleState,
  PredatorState,
  PreyState,
  SessionSummary,
} from "./types";

/** Frozen demo master seed -- one source of truth for the whole live demo. */
export const MASTER_SEED = 250927;

/** Session options that are only meaningful for model-driven sessions. */
export type SessionDriving =
  | { model_driven?: false; checkpoint_path?: null }
  | { model_driven: true; checkpoint_path?: string | null };

export function createSession(
  masterSeed = MASTER_SEED,
  environment: Environment = "food_rich",
  driving: SessionDriving = {},
): Promise<SessionSummary> {
  const body: Partial<SessionCreate> = {
    master_seed: masterSeed,
    environment,
    model_driven: driving.model_driven ?? false,
    checkpoint_path: driving.checkpoint_path ?? null,
  };
  return req<SessionSummary>("/v1/sessions", { method: "POST", body: JSON.stringify(body) });
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

/** Manual Control 的单鱼动作（`API接口.md` §1.6，`交互与可视化.md` §10）。 */
export interface ManualControl {
  fishId: string;
  /** 转向角速度（rad/s），后端裁剪到 [-1, 1]。 */
  omega: number;
  /** 速度（世界单位/秒），后端裁剪到 [0, 1]。 */
  speed: number;
}

export function release(
  sessionId: string,
  steps = 1,
  useExpert = true,
  control?: ManualControl,
): Promise<SessionSummary> {
  const query = new URLSearchParams({ steps: String(steps), use_expert: String(useExpert) });
  if (control) {
    query.set("fish_id", control.fishId);
    query.set("omega", String(control.omega));
    query.set("speed", String(control.speed));
  }
  return req<SessionSummary>(`/v1/sessions/${sessionId}/release?${query}`, { method: "POST" });
}

/**
 * 把发育好的实验室个体追加进会话 Arena（`API接口.md` §1.11）。
 * 之后该鱼由**它自己的 DanioNet** 驱动，鱼卡回真实 `genome_id`。
 */
export function spawnIndividual(
  sessionId: string,
  genomeId: string,
  seed = 0,
): Promise<SpawnedIndividual> {
  return req<SpawnedIndividual>(`/v1/sessions/${sessionId}/individuals`, {
    method: "POST",
    body: JSON.stringify({ genome_id: genomeId, seed }),
  });
}

/** Toggle pause/resume (`API接口.md` §1.7: one endpoint, not pause+resume). */
export function pauseSession(sessionId: string): Promise<SessionSummary> {
  return req<SessionSummary>(`/v1/sessions/${sessionId}/pause`, { method: "POST" });
}

export function getSnapshot(sessionId: string): Promise<ArenaSnapshot> {
  return req<ArenaSnapshot>(`/v1/sessions/${sessionId}/snapshot`);
}

export function getFishCard(sessionId: string, fishId: string): Promise<FishCard> {
  return req<FishCard>(
    `/v1/sessions/${sessionId}/fish/${encodeURIComponent(fishId)}`,
  );
}

export function getLeaderboard(sessionId: string): Promise<Leaderboard> {
  return req<Leaderboard>(`/v1/sessions/${sessionId}/leaderboard`);
}
