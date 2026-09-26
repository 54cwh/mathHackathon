/** Shared REST helper — the single place that turns a response into a value
 *  or throws the backend's `detail` (`api/API接口.md` §4). */

export async function req<T>(path: string, init?: RequestInit): Promise<T> {
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
