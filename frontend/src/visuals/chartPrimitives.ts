/**
 * 指标图表原语（手绘 Canvas）——Evolution Dashboard §8 用。
 *
 * **为什么不用 echarts**：`交互与可视化.md` A10 要求像素硬度（无 blur/shadow/gradient/
 * 缩放动画/非整数定位），第三方图表库要么带平滑插值、要么需要外层 CSS 缩放；
 * 手绘 32 行代码即可满足，且配色/取整与 `ArenaScene` 同源。图表路线若日后改为
 * ECharts，替换点只在本文件。
 *
 * 规则：只用 `design/palette` 的颜色；坐标一律 `Math.round`；线段 1px；不做填充渐变。
 * 命名：本文件是**图元**（纯函数），React 壳在 `MetricChart.tsx`（避免同基名歧义）。
 */

import { ARENA, BRAND } from "@/design/palette";

export interface SeriesDef {
  label: string;
  color: string;
  /** 与 `x` 等长；null 表示该点未记录（断线，不补 0）。 */
  values: (number | null)[];
}

export interface ChartFrame {
  w: number;
  h: number;
  /** 左右/上下留白（给端点画短线用）。 */
  pad: number;
}

const PAD = 3;

function frame(canvasW: number, canvasH: number): ChartFrame {
  return { w: canvasW, h: canvasH, pad: PAD };
}

/** 数值 -> canvas y（整数；`yMax` 与 `yMin` 必须不同）。 */
function scaleY(value: number, yMin: number, yMax: number, f: ChartFrame): number {
  const span = yMax - yMin || 1;
  const usable = Math.max(1, f.h - 2 * f.pad);
  return Math.round(f.h - f.pad - ((value - yMin) / span) * usable);
}

function bounds(series: SeriesDef[]): [number, number] | null {
  const all = series.flatMap((s) => s.values).filter((v): v is number => typeof v === "number");
  if (all.length === 0) return null;
  let lo = Math.min(...all);
  let hi = Math.max(...all);
  if (lo === hi) {
    lo -= 0.5;
    hi += 0.5;
  }
  return [lo, hi];
}

export function clearChart(ctx: CanvasRenderingContext2D, w: number, h: number): void {
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, w, h);
}

/** 多序列折线（值缺失处断开）。返回是否画出了内容。 */
export function drawLineChart(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  series: SeriesDef[],
  baseline?: number,
): boolean {
  clearChart(ctx, w, h);
  const f = frame(w, h);
  const b = bounds(series);
  if (!b) return false;
  const [yMin, yMax] = b;

  if (baseline !== undefined && baseline >= yMin && baseline <= yMax) {
    ctx.fillStyle = BRAND.stoneShadow;
    const y = scaleY(baseline, yMin, yMax, f);
    ctx.fillRect(f.pad, y, Math.max(1, w - 2 * f.pad), 1);
  }

  const count = Math.max(1, ...series.map((s) => s.values.length));
  const xAt = (i: number) =>
    count === 1 ? Math.round(w / 2) : Math.round(f.pad + (i / (count - 1)) * (w - 2 * f.pad));

  for (const s of series) {
    ctx.fillStyle = s.color;
    let prevX: number | null = null;
    let prevY: number | null = null;
    s.values.forEach((value, index) => {
      if (typeof value !== "number") {
        prevX = null;
        prevY = null;
        return;
      }
      const x = xAt(index);
      const y = scaleY(value, yMin, yMax, f);
      if (prevX !== null && prevY !== null) {
        // 1px 细线：逐列线性插值取**一个** y（不是按列填充 y 跨度——那会在跳变处糊成色块）。
        const dx = x - prevX;
        for (let sx = Math.min(prevX, x); sx <= Math.max(prevX, x); sx++) {
          const t = dx === 0 ? 0 : (sx - prevX) / dx;
          ctx.fillRect(sx, Math.round(prevY + t * (y - prevY)), 1, 1);
        }
      }
      ctx.fillRect(x - 1, y - 1, 3, 3); // 采样点（3px 方块，像素风）
      prevX = x;
      prevY = y;
    });
  }
  return true;
}

/** 直方图（逐个体 fitness 分布）。返回是否画出了内容。 */
export function drawHistogram(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  values: number[],
  bins = 16,
): boolean {
  clearChart(ctx, w, h);
  if (values.length === 0) return false;
  const f = frame(w, h);
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = hi - lo || 1;
  const counts = new Array<number>(bins).fill(0);
  for (const value of values) {
    const index = Math.min(bins - 1, Math.max(0, Math.floor(((value - lo) / span) * bins)));
    counts[index] += 1;
  }
  const peak = Math.max(...counts);
  const usable = Math.max(1, f.h - 2 * f.pad);
  const barW = Math.max(1, Math.floor((w - 2 * f.pad) / bins));
  ctx.fillStyle = ARENA.fishUnselected;
  counts.forEach((count, index) => {
    if (count === 0) return;
    const height = Math.max(1, Math.round((count / peak) * usable));
    ctx.fillRect(f.pad + index * barW, h - f.pad - height, Math.max(1, barW - 1), height);
  });
  return true;
}

/** 单序列柱状图（Brain Forge 的 motif affinity / 细胞组成概览用）。 */
export function drawBars(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  values: (number | null)[],
  color: string = ARENA.fishUnselected,
): boolean {
  clearChart(ctx, w, h);
  const f = frame(w, h);
  if (values.length === 0) return false;
  const numeric = values.filter((v): v is number => typeof v === "number");
  if (numeric.length === 0) return false;
  const peak = Math.max(...numeric.map((v) => Math.abs(v))) || 1;
  const usable = Math.max(1, h - 2 * f.pad);
  const slot = Math.max(2, Math.floor((w - 2 * f.pad) / values.length));
  const barW = Math.max(1, slot - 1);
  values.forEach((value, index) => {
    if (typeof value !== "number") return;
    const height = Math.max(1, Math.round((Math.abs(value) / peak) * usable));
    ctx.fillStyle = color;
    ctx.fillRect(f.pad + index * slot, h - f.pad - height, barW, height);
  });
  return true;
}

/**
 * 成对柱状图（Before/After 对比用）：每个 index 画两根相邻竖柱。
 * `values` 为 null 的项不画（缺失 ≠ 0）；`max` 缺省取两组最大值。
 */
export function drawPairedBars(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  before: (number | null)[],
  after: (number | null)[],
  beforeColor: string = BRAND.blueGrey,
  afterColor: string = ARENA.fishSelected,
): boolean {
  clearChart(ctx, w, h);
  const f = frame(w, h);
  const count = Math.max(before.length, after.length);
  if (count === 0) return false;
  const all = [...before, ...after].filter((v): v is number => typeof v === "number");
  if (all.length === 0) return false;
  const peak = Math.max(...all.map((v) => Math.abs(v))) || 1;
  const usable = Math.max(1, h - 2 * f.pad);
  const slot = Math.max(2, Math.floor((w - 2 * f.pad) / count));
  const barW = Math.max(1, Math.floor((slot - 1) / 2));

  for (let i = 0; i < count; i++) {
    const x = f.pad + i * slot;
    const pair: Array<[number | null, string, number]> = [
      [before[i] ?? null, beforeColor, 0],
      [after[i] ?? null, afterColor, barW],
    ];
    for (const [value, color, offset] of pair) {
      if (typeof value !== "number") continue;
      const height = Math.max(1, Math.round((Math.abs(value) / peak) * usable));
      ctx.fillStyle = color;
      ctx.fillRect(x + offset, h - f.pad - height, barW, height);
    }
  }
  return true;
}

/** 环境变更标记：在指定索引处画 1px 竖线（只画有标记的那些 x）。 */
export function drawEventMarkers(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  total: number,
  marked: number[],
): void {
  if (total <= 0 || marked.length === 0) return;
  ctx.fillStyle = ARENA.predator;
  for (const index of marked) {
    const x =
      total === 1 ? Math.round(w / 2) : Math.round(PAD + (index / (total - 1)) * (w - 2 * PAD));
    ctx.fillRect(x, PAD, 1, Math.max(1, h - 2 * PAD));
  }
}
