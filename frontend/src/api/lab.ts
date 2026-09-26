/**
 * Genome lab REST client (`api/API接口.md` §2.3) — genomes, developments,
 * breedings. All three share one in-memory store (`genome_lab.py`), so they live
 * in one module rather than three.
 */

import { req } from "./http";
import type {
  BreedingRequest,
  BreedingResult,
  DevelopmentRequest,
  DevelopmentResult,
  GenomeCreate,
  GenomeRecord,
  MutationRequest,
  MutationResult,
} from "./types";

export type {
  Base,
  BreedingResult,
  DevelopmentResult,
  GenomeRecord,
  MutationResult,
} from "./types";

export function createGenome(seed?: number | null): Promise<GenomeRecord> {
  const body: GenomeCreate = { seed: seed ?? null };
  return req<GenomeRecord>("/v1/genomes", { method: "POST", body: JSON.stringify(body) });
}

export function getGenome(genomeId: string): Promise<GenomeRecord> {
  return req<GenomeRecord>(`/v1/genomes/${encodeURIComponent(genomeId)}`);
}

/** Single-point free edit; `position ∈ [0, 512)` over the diploid genome. */
export function mutateGenome(
  genomeId: string,
  mutation: MutationRequest,
): Promise<MutationResult> {
  return req<MutationResult>(`/v1/genomes/${encodeURIComponent(genomeId)}/mutations`, {
    method: "POST",
    body: JSON.stringify(mutation),
  });
}

/**
 * 发育。`withTrace=true` 时后端额外返回逐阶段轨迹（`API接口.md` §2.3）：
 * 记录只读、不抽随机数，故开/关该参数的表型逐位相同（后端有回归测试守护）。
 */
export function develop(
  request: DevelopmentRequest,
  withTrace = false,
): Promise<DevelopmentResult> {
  const path = withTrace ? "/v1/developments?with_trace=true" : "/v1/developments";
  return req<DevelopmentResult>(path, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function breed(request: BreedingRequest): Promise<BreedingResult> {
  return req<BreedingResult>("/v1/breedings", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
