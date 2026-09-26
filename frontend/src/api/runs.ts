/**
 * 磁盘 run 只读客户端（`api/API接口.md` §2.4）——Evolution Dashboard 的数据源。
 *
 * 为什么不是内存实验表：`results/runs/<run_id>/` 是落盘契约，进程重启也还在，
 * 因此 `pilot20-s1103` 这类非本进程产生的 run 也能被前端看到。
 */

import { req } from "./http";
import type { Page, RunEvolution, RunSummary } from "./types";

export type { RunEvolution, RunFitnessDistribution, RunGeneration, RunSummary } from "./types";

export function listRuns(limit = 20, cursor?: string): Promise<Page<RunSummary>> {
  const query = new URLSearchParams({ limit: String(limit) });
  if (cursor) query.set("cursor", cursor);
  return req<Page<RunSummary>>(`/v1/runs?${query}`);
}

export function getRunEvolution(runId: string): Promise<RunEvolution> {
  return req<RunEvolution>(`/v1/runs/${encodeURIComponent(runId)}/evolution`);
}
