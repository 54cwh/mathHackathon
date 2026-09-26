/**
 * Geometry and coordinate mapping — the **single definition site** for every
 * frontend dimension. Panels must import from here and never hardcode sizes.
 *
 * Basis: `frontend/视觉规范审计.md` rules 1 (frame 3:2), 3 (arena 5:3),
 * 5 (1px divider), 9(b) (integer positioning); world contract = arena §2.
 */

/** Overall frame ratio (rule 1). */
export const FRAME_RATIO = [3, 2] as const;

/** Arena viewport ratio (rule 3); matches the canvas bitmap. */
export const ARENA_RATIO = [5, 3] as const;

/** World size (arena §2) — the arena's intrinsic coordinate space. */
export const WORLD = { w: 100, h: 60 } as const;

/** Arena canvas bitmap; ratio must equal ARENA_RATIO (rule 3). */
export const CANVAS = { w: 640, h: 384 } as const;

/** Shared divider width (rule 5). */
export const DIVIDER_PX = 1;

/** CSS value for the overall frame's `aspect-ratio`. */
export function frameAspect(): string {
  return `${FRAME_RATIO[0]} / ${FRAME_RATIO[1]}`;
}

/**
 * CSS width for the overall frame: fills the viewport when possible, otherwise
 * pillarboxes (rule 1 — a 16:9 screen is *wider* than 3:2, so height bound the
 * frame and the leftover sits left/right).
 */
export function frameWidth(): string {
  return `min(100%, calc(100dvh * ${FRAME_RATIO[0]} / ${FRAME_RATIO[1]}))`;
}

/** CSS value for the arena viewport's `aspect-ratio` (rule 3, explicit). */
export function arenaAspect(): string {
  return `${ARENA_RATIO[0]} / ${ARENA_RATIO[1]}`;
}

/** World x → canvas x, snapped to an integer pixel (rule 9(b)).
 *
 * 注意：注释里也**不要写那个圆角工具类的词** —— Tailwind 扫原始文本，
 * 英文注释里的 `round` + `ed` 会被切出来，在产物里生成一个没人用的圆角类。 */
export function sx(x: number): number {
  return Math.round((x / WORLD.w) * CANVAS.w);
}

/** World y → canvas y, snapped to an integer pixel (rule 9(b)). */
export function sy(y: number): number {
  return Math.round((y / WORLD.h) * CANVAS.h);
}

/** World radius → canvas radius, same uniform scale as sx/sy (rule 9(b)). */
export function sr(r: number): number {
  return Math.round((r / WORLD.w) * CANVAS.w);
}
