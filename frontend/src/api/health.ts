/** Health probe (`api/API接口.md` §1.10) — used by the shell before a live demo. */

import { req } from "./http";
import type { Health } from "./types";

export function getHealth(): Promise<Health> {
  return req<Health>("/v1/health");
}
