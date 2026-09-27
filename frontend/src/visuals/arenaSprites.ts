/**
 * Arena 像素素材接线 —— 已落盘的 sprite（`frontend/public/assets/arena/`）
 * 与 `ArenaScene` 之间的**唯一**装载点。DanioArena 与 Playback 共用 `ArenaScene`，
 * 故接线只此一处，两处显示不会漂移。
 *
 * 素材出处：`artifacts/assets_placeholder/生图总清单.md` §十一。
 * 命名 `{族}_{朝向}_f{1..4}.png`；朝向为罗盘八向（斜向由基本向 45° 旋转派生）。
 * 49 个文件的落盘尺寸 / 色数 / flat 实测见 §十一 的表。
 *
 * 绘制约定（与生图侧的裁剪对齐一致）：
 *
 * - 画布为正方形、鱼体居中，**锚点 = 画布中心 = 鱼身质心**；4 帧按鱼头对齐，
 *   故摆尾时鱼身不漂（§十一「动画对齐实测」极差 0.1–0.7 px）。
 * - `bodyPx` 是该族在源资产里的体长；画到画布时按 `bodyLen / bodyPx` 等比缩放。
 * - `imageSmoothingEnabled = false` 由 `ArenaScene` 统一设置，故此处缩放一律最近邻。
 */

export type SpriteDir = "e" | "se" | "s" | "sw" | "w" | "nw" | "n" | "ne";

/** 资产根：Vite 把 `public/` 直出到根路径，dev 与 build 同路径。 */
const ROOT = "/assets/arena";

/**
 * 八个朝向，按 `heading` 每 π/4 一档排列（见 `dirOf`）。
 * 斜向是基本向的 45° 整数旋转，已在落盘阶段生成，运行时不做任何变换。
 */
const DIRS: SpriteDir[] = ["e", "se", "s", "sw", "w", "nw", "n", "ne"];

/** 摆尾帧号，与落盘文件名一致。 */
const FRAMES = [1, 2, 3, 4] as const;

export interface SpriteFamily {
  prefix: string;
  /** 源资产里的体长（像素）。 */
  bodyPx: number;
  /** 源资产画布边长（像素）。 */
  canvasPx: number;
}

const ADULT: SpriteFamily = { prefix: "fish_adult", bodyPx: 128, canvasPx: 134 };
const JUVENILE: SpriteFamily = { prefix: "fish_juvenile", bodyPx: 128, canvasPx: 140 };
export const PREDATOR: SpriteFamily = { prefix: "predator", bodyPx: 192, canvasPx: 226 };

/** 猎物：单张、无朝向、无帧。 */
export const PREY_SRC = `${ROOT}/prey.png`;

/**
 * 幼鱼 / 成鱼的分界。**这是视觉常量，不是玩法参数** ——
 * 取值 = `configs/default_arena.yaml` 里鱼体区间 [initial_size 1.0, max_size 2.5] 的中点。
 * 玩法侧若将来在 arena 契约里给出阶段字段，替换此处即可。
 */
const JUVENILE_BELOW = 1.75;

export function familyFor(size: number): SpriteFamily {
  return size < JUVENILE_BELOW ? JUVENILE : ADULT;
}

export function fishSrc(family: SpriteFamily, dir: SpriteDir, frame: number): string {
  return `${ROOT}/${family.prefix}_${dir}_f${frame}.png`;
}

export function predatorSrc(dir: SpriteDir, frame: number): string {
  return `${ROOT}/${PREDATOR.prefix}_${dir}_f${frame}.png`;
}

/**
 * `heading`（弧度；画布坐标 +x 右、+y 下）→ 八个朝向：
 * 0 → e（右）、π/4 → se（右下）、π/2 → s（下）、3π/4 → sw（左下）、
 * π → w（左）、5π/4 → nw（左上）、3π/2 → n（上）、7π/4 → ne（右上）。
 * 量化到最近的 45°，所以转向是八向吸附，不是连续旋转。
 */
export function dirOf(heading: number): SpriteDir {
  const k = Math.round(heading / (Math.PI / 4));
  return DIRS[((k % 8) + 8) % 8];
}

/** 摆尾帧（1..4）。取 `step` 而非墙钟，回放与实时因此逐帧一致。 */
export function frameOf(step: number): number {
  return (((step % 4) + 4) % 4) + 1;
}

/** 按体长换算正方形画布的边长（像素）并取整（rule 9(b)：整数定位）。 */
export function spriteSide(family: SpriteFamily, bodyLen: number): number {
  return Math.max(8, Math.round((bodyLen * family.canvasPx) / family.bodyPx));
}

interface Slot {
  img: HTMLImageElement;
  ready: boolean;
}

const slots = new Map<string, Slot>();

function slot(src: string): Slot {
  let s = slots.get(src);
  if (!s) {
    const img = new Image();
    const rec: Slot = { img, ready: false };
    img.addEventListener("load", () => {
      rec.ready = true;
    });
    img.src = src;
    slots.set(src, rec);
    s = rec;
  }
  return s;
}

/**
 * 把位图以 `(cx, cy)` 为中心画成 `side × side`。位图未就绪返回 `false`，
 * 调用方据此回落到矢量形状（避免首帧空场）。坐标取整，遵守 rule 9(b)。
 */
export function drawSprite(
  ctx: CanvasRenderingContext2D,
  src: string,
  cx: number,
  cy: number,
  side: number,
): boolean {
  const s = slot(src);
  if (!s.ready || s.img.naturalWidth === 0) return false;
  const half = side / 2;
  ctx.drawImage(s.img, Math.round(cx - half), Math.round(cy - half), side, side);
  return true;
}

/**
 * 启动即预热全部素材（模块导入时执行一次）。
 *
 * 面板只在场景更新时重绘（`useEffect([scene, selectedFishId])`），若首帧早于位图
 * 就绪、且会话随即暂停，回落三角会一直留在画布上。预热把「就绪」提前到 App 启动，
 * 正常使用下不会再看到回落。
 */
export function preloadArenaSprites(): void {
  for (const family of [ADULT, JUVENILE, PREDATOR]) {
    for (const dir of DIRS) {
      for (const frame of FRAMES) slot(`${ROOT}/${family.prefix}_${dir}_f${frame}.png`);
    }
  }
  slot(PREY_SRC);
}

if (typeof Image !== "undefined") preloadArenaSprites();
