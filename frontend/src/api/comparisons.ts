import { req } from "./http";
import type { ComparisonTable, ComparisonTableSummary } from "./types";

/** 列出 `results/tables/` 下的对比表（`API接口.md` §2.5）。空表 = 该目录还没有产物。 */
export function listComparisons(): Promise<ComparisonTableSummary[]> {
  return req<ComparisonTableSummary[]>("/v1/comparisons");
}

/** 读取一张对比表全文（`payload` 原样透传）。 */
export function getComparison(id: string): Promise<ComparisonTable> {
  return req<ComparisonTable>(`/v1/comparisons/${encodeURIComponent(id)}`);
}
