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
import {
  PREDATOR,
  PREY_SRC,
  dirOf,
  drawBackdrop,
  drawSprite,
  familyFor,
  fishSrc,
  frameOf,
  predatorSrc,
  propSrc,
  spriteSide,
} from "@/visuals/arenaSprites";

/**
 * 显示层**外推**：按每条鱼的 `(heading, speed)` 把它从最近一帧服务端状态往前推 `dt` 秒。
 *
 * 用途：服务端帧率（≈30 Hz）低于屏幕刷新率时，直接按帧重绘会有"跳跃"感；这里在**两帧之间**
 * 补位置，让画面在 60 fps 下连续。**只改显示**：输入是权威 `x/y/heading/speed`，不产生新状态、
 * 不参与仿真与命中（命中另用最新权威帧）。
 */
export function extrapolateFish(
  fish: Record<string, FishState>,
  dt: number,
  world: { w: number; h: number },
): Record<string, FishState> {
  if (dt <= 0) return fish;
  const out: Record<string, FishState> = {};
  for (const [id, f] of Object.entries(fish)) {
    if (!f.alive || !(f.speed > 0)) {
      out[id] = f;
      continue;
    }
    const x = Math.min(world.w, Math.max(0, f.x + Math.cos(f.heading) * f.speed * dt));
    const y = Math.min(world.h, Math.max(0, f.y + Math.sin(f.heading) * f.speed * dt));
    out[id] = { ...f, x, y };
  }
  return out;
}

export interface ArenaScene {
  step: number;
  fish: Record<string, FishState>;
  prey: Record<string, PreyState>;
  predators: Record<string, PredatorState>;
  obstacles: ObstacleState[];
}

/**
 * 画布底色（调用方也可只清屏不铺底，但两处视觉必须一致，故在此统一）。
 * 素材就绪时平铺海洋底，未就绪回落纯色 —— 两处不会出现不同底色。
 */
export function fillBackdrop(ctx: CanvasRenderingContext2D): void {
  ctx.clearRect(0, 0, CANVAS.w, CANVAS.h);
  if (!drawBackdrop(ctx, CANVAS.w, CANVAS.h)) {
    ctx.fillStyle = ARENA.canvas;
    ctx.fillRect(0, 0, CANVAS.w, CANVAS.h);
  }
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
    const cx = sx(o.x);
    const cy = sy(o.y);
    // 外观大于碰撞体：碰撞直径在画布上只有 19–45px，128px 的素材按这个尺寸画会被
    // 缩到 3–7 倍以下、糊成噪点；放大到 48–96px 后降采样倍数与鱼同量级。
    // 视觉体积与命中体分离是俯视游戏的常规做法。
    const dia = Math.min(96, Math.max(48, Math.round(sr(o.radius) * 3)));
    if (!drawSprite(ctx, propSrc(o.x, o.y), cx, cy, dia)) {
      ctx.beginPath();
      ctx.arc(cx, cy, sr(o.radius), 0, Math.PI * 2);
      ctx.fillStyle = ARENA.obstacleDark;
      ctx.fill();
      ctx.strokeStyle = ARENA.obstacleLight;
      ctx.stroke();
    }
  }

  for (const p of Object.values(scene.prey)) {
    if (!p.alive) continue;
    // 直径沿用原圆点足迹（2 x 1.5 x sr），换皮不改玩法读数。
    const dia = Math.max(12, sr(p.size) * 3);
    if (!drawSprite(ctx, PREY_SRC, sx(p.x), sy(p.y), dia)) {
      ctx.beginPath();
      ctx.arc(sx(p.x), sy(p.y), dia / 2, 0, Math.PI * 2);
      ctx.fillStyle = ARENA.prey;
      ctx.fill();
    }
  }

  for (const d of Object.values(scene.predators)) {
    // 契约里 `PredatorState` 没有 heading，故固定用源资产朝向 s（头朝下）；
    // 将来契约给出 heading 再改成 dirOf(d.heading)。
    const dia = Math.max(24, sr(d.size) * 6);
    const side = spriteSide(PREDATOR, dia);
    const cx = sx(d.x);
    const cy = sy(d.y);
    if (drawSprite(ctx, predatorSrc("s", frameOf(scene.step)), cx, cy, side)) {
      // 威胁读数：捕食者位图只有深色四色，在 ink 画布上对比过低（旧版是亮红圆），
      // 故补一圈 1px 危险色边框。用四条 fillRect 而非 stroke，保持整数、无插值（rule 9(b)）。
      const bx = Math.round(cx - side / 2);
      const by = Math.round(cy - side / 2);
      ctx.fillStyle = ARENA.predator;
      ctx.fillRect(bx, by, side, 1);
      ctx.fillRect(bx, by + side - 1, side, 1);
      ctx.fillRect(bx, by, 1, side);
      ctx.fillRect(bx + side - 1, by, 1, side);
    } else {
      ctx.beginPath();
      ctx.arc(cx, cy, sr(d.size) * 3, 0, Math.PI * 2);
      ctx.fillStyle = ARENA.predator;
      ctx.fill();
      ctx.strokeStyle = ARENA.outline;
      ctx.stroke();
    }
  }

  for (const [fid, f] of Object.entries(scene.fish)) {
    if (!f.alive) continue;
    const x = sx(f.x);
    const y = sy(f.y);
    const len = Math.max(8, sr(f.size) * 10);
    const isSelected = fid === selectedFishId;
    const family = familyFor(f.size);
    // 位图足迹 = 原三角的视觉长度（前 len + 后 0.6 len），换皮不改玩法读数。
    const bodyLen = Math.max(12, Math.round(len * 1.6));
    const side = spriteSide(family, bodyLen);
    const src = fishSrc(family, dirOf(f.heading), frameOf(scene.step));

    if (drawSprite(ctx, src, x, y, side)) {
      if (isSelected) {
        // 位图不能重新着色，选中态改用取整方框标出（rule 9(b)）。
        const half = Math.round(side / 2) + 2;
        ctx.strokeStyle = ARENA.fishSelected;
        ctx.lineWidth = 1;
        ctx.strokeRect(x - half, y - half, half * 2, half * 2);
      }
    } else {
      // 位图未就绪：回落原三角，避免首帧空场。
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
    }

    if (isSelected) {
      ctx.beginPath();
      ctx.arc(x, y, len + 4, -Math.PI / 2, -Math.PI / 2 + f.energy * Math.PI * 2);
      ctx.strokeStyle = f.energy > 0.3 ? ARENA.energyOk : ARENA.energyLow;
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }
}
