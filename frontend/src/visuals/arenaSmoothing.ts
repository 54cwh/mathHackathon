import type { FishState, PreyState, PredatorState } from "@/api/types";
import type { ArenaScene } from "@/visuals/ArenaScene";

/**
 * 画面平滑（`交互与可视化.md` §7.1，2026-09-27）：把「仿真推进」与「画面刷新」解耦。
 *
 * 背景：仿真按 `POLL_MS × simSpeed` 推进（默认每 100ms 一次、每次 `simSpeed` 步），位置只在
 * 权威帧（WS `arena.fish_state` / REST `snapshot`）到达时更新 ⇒ 直接绘制就是 ~10 Hz 的"跳格"。
 *
 * 做法：每次权威帧按**到达时刻**入环形缓冲（每实体保留最近 `KEEP` 个样本）；rAF 每帧取
 * 渲染时刻 `t = now - RENDER_DELAY_MS` 的位姿：
 *   - `t` 落在两样本之间 ⇒ 线性插值（heading 走最短弧，避免绕圈）；
 *   - `t` 超过最新样本 ⇒ 用最后两样本的**有限差分速度**外推，上限 `MAX_AHEAD_MS`（超出即钉住）。
 *
 * 位置始终以权威帧为基准，仿真步长与速度口径不变；视觉变为显示刷新率上的连续运动。
 * 本模块为纯函数（无 DOM / 无计时器），便于单测。
 */

/** 每实体保留的样本数（≥3 才能同时插值与差分外推）。 */
const KEEP = 8;
/** 外推上限（ms）：超过则钉在最新样本，避免暂停后"飞鱼"。 */
const MAX_AHEAD_MS = 180;
/** 同一时刻（<4ms）的重复样本视为重复推送（WS 与 snapshot 同刻），后者覆盖前者。 */
const SAME_T_MS = 4;

export interface PoseSample {
  t: number;
  x: number;
  y: number;
  heading: number;
  speed: number;
  alive: boolean;
}

export interface PoseBuffer {
  fish: Map<string, PoseSample[]>;
  prey: Map<string, PoseSample[]>;
  predator: Map<string, PoseSample[]>;
}

export function createPoseBuffer(): PoseBuffer {
  return { fish: new Map(), prey: new Map(), predator: new Map() };
}

function push(map: Map<string, PoseSample[]>, id: string, s: PoseSample): void {
  const list = map.get(id);
  if (!list) {
    map.set(id, [s]);
    return;
  }
  const last = list[list.length - 1];
  if (s.t - last.t < SAME_T_MS) {
    list[list.length - 1] = s;
    return;
  }
  list.push(s);
  if (list.length > KEEP) list.splice(0, list.length - KEEP);
}

/** 权威帧入缓冲（`t` = `performance.now()`）。空 `fish/prey/predators` 的帧只更新其中有的实体。 */
export function pushScene(buf: PoseBuffer, scene: ArenaScene, t: number): void {
  for (const [id, f] of Object.entries(scene.fish)) {
    push(buf.fish, id, { t, x: f.x, y: f.y, heading: f.heading, speed: f.speed, alive: f.alive });
  }
  for (const [id, p] of Object.entries(scene.prey)) {
    push(buf.prey, id, { t, x: p.x, y: p.y, heading: 0, speed: 0, alive: p.alive });
  }
  for (const [id, d] of Object.entries(scene.predators)) {
    push(buf.predator, id, { t, x: d.x, y: d.y, heading: 0, speed: 0, alive: true });
  }
}

/** 角度差归一到 (-π, π]，插值/外推走最短弧。 */
function wrapPi(a: number): number {
  return Math.atan2(Math.sin(a), Math.cos(a));
}

/** 取 `t` 时刻的位姿；缓冲为空 ⇒ null（调用方保留权威帧原值）。 */
function poseAt(list: PoseSample[] | undefined, t: number): PoseSample | null {
  if (!list || list.length === 0) return null;
  if (list.length === 1) return list[0];

  const last = list[list.length - 1];
  const prev = list[list.length - 2];

  if (t >= last.t) {
    const dt = last.t - prev.t;
    if (dt <= 0) return last;
    const u = Math.min(t - last.t, MAX_AHEAD_MS) / dt;
    return {
      t,
      alive: last.alive,
      x: last.x + (last.x - prev.x) * u,
      y: last.y + (last.y - prev.y) * u,
      heading: last.heading + wrapPi(last.heading - prev.heading) * u,
      speed: last.speed,
    };
  }

  const first = list[0];
  if (t <= first.t) return first;

  for (let i = list.length - 1; i > 0; i -= 1) {
    const b = list[i];
    const a = list[i - 1];
    if (t >= a.t && t <= b.t) {
      const span = b.t - a.t;
      const u = span > 0 ? (t - a.t) / span : 1;
      return {
        t,
        alive: a.alive,
        x: a.x + (b.x - a.x) * u,
        y: a.y + (b.y - a.y) * u,
        heading: a.heading + wrapPi(b.heading - a.heading) * u,
        speed: a.speed + (b.speed - a.speed) * u,
      };
    }
  }
  return last;
}

/**
 * 按缓冲把权威场景平滑到 `t` 时刻；某实体无样本 ⇒ 保留其原值。
 * `step`/`events`/`obstacles` 原样带过（障碍静止，无需插值）。
 */
export function sampleScene(buf: PoseBuffer, scene: ArenaScene, t: number): ArenaScene {
  const fish: Record<string, FishState> = {};
  for (const [id, f] of Object.entries(scene.fish)) {
    const p = poseAt(buf.fish.get(id), t);
    fish[id] = p ? { ...f, x: p.x, y: p.y, heading: p.heading, alive: p.alive } : f;
  }

  const prey: Record<string, PreyState> = {};
  for (const [id, item] of Object.entries(scene.prey)) {
    const p = poseAt(buf.prey.get(id), t);
    prey[id] = p ? { ...item, x: p.x, y: p.y, alive: p.alive } : item;
  }

  const predators: Record<string, PredatorState> = {};
  for (const [id, item] of Object.entries(scene.predators)) {
    const p = poseAt(buf.predator.get(id), t);
    predators[id] = p ? { ...item, x: p.x, y: p.y } : item;
  }

  return { ...scene, fish, prey, predators };
}

/** 泳姿帧（1..4）由**渲染时钟**步进：与仿真速度解耦，20× 下不再每秒切 200 帧而频闪。 */
export function animFrame(t: number, ms = 110): number {
  return ((((Math.floor(t / ms) % 4) + 4) % 4) + 1) as number;
}
