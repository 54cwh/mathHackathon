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

export function develop(request: DevelopmentRequest): Promise<DevelopmentResult> {
  return req<DevelopmentResult>("/v1/developments", {
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
