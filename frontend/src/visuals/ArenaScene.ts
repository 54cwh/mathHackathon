/**
 * Arena 画面原语 —— DanioArena 与 Playback **共用**一套绘制/命中判定，
 * 避免两处各写一份（画风与命中半径必须同源，否则回放里点不到鱼）。
 *
 * 输入 `ArenaScene` 是「渲染所需的最小集合」：鱼 + 猎物 + 捕食者 + 障碍 + step。
 * 它既可由 `GET .../snapshot`（全场）构造，也可由 `arena.fish_state` 推送 + 低频
 * snapshot 合并构造（见 `DanioArenaPanel`）。
 *
 * 颜色全部取自 `design/palette` 的 `ARENA`；坐标经 `design/geometry` 的取整函数。
 */

import { ARENA } from "@/design/palette";
import { CANVAS, sx, sy, sr } from "@/design/geometry";
import type { FishState, ObstacleState, PredatorState, PreyState } from "@/api/types";

export interface ArenaScene {
  step: number;
  fish: Record<string, FishState>;
  prey: Record<string, PreyState>;
  predators: Record<string, PredatorState>;
  obstacles: ObstacleState[];
}

/** 画布底色（调用方也可只清屏不铺底，但两处视觉必须一致，故在此统一）。 */
export function fillBackdrop(ctx: CanvasRenderingContext2D): void {
  ctx.clearRect(0, 0, CANVAS.w, CANVAS.h);
  ctx.fillStyle = ARENA.canvas;
  ctx.fillRect(0, 0, CANVAS.w, CANVAS.h);
}

/** 命中半径：按**屏幕**尺度折算（24 CSS px），否则缩小显示时人点不中。 */
export function fishHitRadius(displayWidth: number): number {
  if (!displayWidth) return 20;
  return 24 * (CANVAS.w / displayWidth);
}

/** 最近的鱼（`maxDist` 为位图像素距离）；无则 null。 */
export function hitTestFish(scene: ArenaScene, mx: number, my: number, maxDist: number): string | null {
  let best: string | null = null;
  let bestDist = Infinity;
  for (const [fid, f] of Object.entries(scene.fish)) {
    if (!f.alive) continue;
    const d = Math.hypot(sx(f.x) - mx, sy(f.y) - my);
    if (d < bestDist) {
      bestDist = d;
      best = fid;
    }
  }
  return best && bestDist < maxDist ? best : null;
}

/** 整场景绘制；`selectedFishId` 高亮并在其身上画能量环。 */
export function drawArenaScene(
  ctx: CanvasRenderingContext2D,
  scene: ArenaScene,
  selectedFishId?: string | null,
): void {
  ctx.imageSmoothingEnabled = false; // hard pixel edges (rule 9(b))
  fillBackdrop(ctx);

  for (const o of scene.obstacles) {
    ctx.beginPath();
    ctx.arc(sx(o.x), sy(o.y), sr(o.radius), 0, Math.PI * 2);
    ctx.fillStyle = ARENA.obstacleDark;
    ctx.fill();
    ctx.strokeStyle = ARENA.obstacleLight;
    ctx.stroke();
  }

  for (const p of Object.values(scene.prey)) {
    if (!p.alive) continue;
    ctx.beginPath();
    ctx.arc(sx(p.x), sy(p.y), Math.max(2, sr(p.size) * 1.5), 0, Math.PI * 2);
    ctx.fillStyle = ARENA.prey;
    ctx.fill();
  }

  for (const d of Object.values(scene.predators)) {
    ctx.beginPath();
    ctx.arc(sx(d.x), sy(d.y), sr(d.size) * 3, 0, Math.PI * 2);
    ctx.fillStyle = ARENA.predator;
    ctx.fill();
    ctx.strokeStyle = ARENA.outline;
    ctx.stroke();
  }

  for (const [fid, f] of Object.entries(scene.fish)) {
    if (!f.alive) continue;
    const x = sx(f.x);
    const y = sy(f.y);
    const len = Math.max(8, sr(f.size) * 10);
    const isSelected = fid === selectedFishId;
    ctx.beginPath();
    ctx.moveTo(x + Math.cos(f.heading) * len, y + Math.sin(f.heading) * len);
    ctx.lineTo(x + Math.cos(f.heading + 2.6) * (len * 0.6), y + Math.sin(f.heading + 2.6) * (len * 0.6));
    ctx.lineTo(x + Math.cos(f.heading - 2.6) * (len * 0.6), y + Math.sin(f.heading - 2.6) * (len * 0.6));
    ctx.closePath();
    ctx.fillStyle = isSelected ? ARENA.fishSelected : ARENA.fishUnselected;
    ctx.fill();
    ctx.strokeStyle = ARENA.outline; // 统一轮廓（像素画惯例；见 design/palette.ts 的 ARENA 说明）
    ctx.lineWidth = isSelected ? 2 : 1;
    ctx.stroke();

    if (isSelected) {
      ctx.beginPath();
      ctx.arc(x, y, len + 4, -Math.PI / 2, -Math.PI / 2 + f.energy * Math.PI * 2);
      ctx.strokeStyle = f.energy > 0.3 ? ARENA.energyOk : ARENA.energyLow;
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }
}
