/**
 * Environmental selection (Experiment F) + job control (`api/API接口.md` §2.2).
 * Launch returns `202` with a `JobStatus`; poll it or consume `job.progress` over
 * the WS channel (`./ws`).
 */

import { req } from "./http";
import type {
  EnvironmentalSelectionDetail,
  EnvironmentalSelectionLaunch,
  EnvironmentalSelectionSummary,
  JobStatus,
  Page,
  SessionEvolutionStep,
} from "./types";

export type {
  EnvironmentalSelectionDetail,
  EnvironmentalSelectionLaunch,
  EnvironmentalSelectionSummary,
  JobStatus,
} from "./types";

export function launchSelection(
  launch: EnvironmentalSelectionLaunch,
): Promise<JobStatus> {
  return req<JobStatus>("/v1/environmental-selections", {
    method: "POST",
    body: JSON.stringify(launch),
  });
}

export function listSelections(limit = 20, cursor?: string): Promise<Page<EnvironmentalSelectionSummary>> {
  const query = new URLSearchParams({ limit: String(limit) });
  if (cursor) query.set("cursor", cursor);
  return req<Page<EnvironmentalSelectionSummary>>(`/v1/environmental-selections?${query}`);
}

export function getSelection(experimentId: string): Promise<EnvironmentalSelectionDetail> {
  return req<EnvironmentalSelectionDetail>(
    `/v1/environmental-selections/${encodeURIComponent(experimentId)}`,
  );
}

export function getJob(jobId: string): Promise<JobStatus> {
  return req<JobStatus>(`/v1/jobs/${encodeURIComponent(jobId)}`);
}

/** Cooperative cancel — takes effect at the next seed boundary (`API接口.md` §2.2). */
export function cancelJob(jobId: string): Promise<JobStatus> {
  return req<JobStatus>(`/v1/jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST" });
}

/** In-session evolution (`API接口.md` §2.3): reuses the selection job. */
export function evolveSession(sessionId: string, generations?: number): Promise<JobStatus> {
  const query = generations === undefined ? "" : `?generations=${generations}`;
  return req<JobStatus>(`/v1/sessions/${encodeURIComponent(sessionId)}/evolutions${query}`, {
    method: "POST",
  });
}

/** 会话内**逐代推进一代**（`API接口.md` §2.3；纯内存、同步）。 */
export function stepSessionEvolution(sessionId: string): Promise<SessionEvolutionStep> {
  return req<SessionEvolutionStep>(
    `/v1/sessions/${encodeURIComponent(sessionId)}/evolutions/step`,
    { method: "POST" },
  );
}
