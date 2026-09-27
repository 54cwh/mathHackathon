import { useEffect, useRef } from "react";
import { BRAIN, BRAND } from "@/design/palette";

/* ===========================================================================
   Brain Forge 的**装饰性神经视觉暗示纹理**。

   两条必须写明的边界（写给后来改它的人）：

   1) 这**不是**网络图 / 树 / hub-spoke / 神经网络拓扑。画面上没有 node、没有
      edge、没有可遍历的路径，也没有任何数字或文字 —— 只有方形粒子、断开的
      微小线段、以及若干局部密集团块。

   2) 下面 BRAIN 的三色（particleA / particleB / particleC）是**装饰分组**，
      只为让纹理有三档明度层次，**不是 cell type 契约**。真实 CellType 有**六**类
      （src/api/types.ts 的 CellType：sensory|prey|threat|memory|inhibitory|motor），
      且 core §10 把「六类 cell type owner」列为**未定契约**。按 AGENTS.md
      「未定契约不得被下游依赖」，本视觉**故意不绑定**该契约：三色与六类之间没有
      任何映射，将来 cell type 定稿也**不需要**改本文件。

   尺寸策略：**位图 = 容器 CSS 像素**（ResizeObserver），与 DnaHelixVisual 同源。
      1 逻辑 px = 1 CSS px，所以 1-3 px 的方形粒子既不被拉伸也不被裁掉，
      坐标取整即等于设备像素的整数定位（§十一）。
      **刻意不用 `object-fit: cover`**：它把位图等比放大再裁掉，放大倍率通常
      非整数（源像素有的占 4 个设备像素、有的占 5 个），恰是「非整数像素定位」；
      而且会丢掉构图的大部分（本面板列宽约为高度的 1/2，横向会被裁掉约 2/3）。

   3) **2026-09-27 起接入真实数据 + 帧循环**（前端功能项接管）：`activation` prop
      传真实的 DanioNet 激活向量后，粒子的"放电"概率由它决定（高激活 -> 更频繁地
      用最亮档闪烁），并叠加一层缓慢的沿轴行波，使纹理是活的。传空则退化为环境闪烁。
      **布局仍是** `(seed, w, h)` 的纯函数（上一条确定性性质保留）；帧循环只改变
      **每个粒子的瞬态亮档**，不改变位置、不新增连线 —— 因此节点/边仍不可数。

   颜色：全部取自 @/design/palette 的 BRAIN，本文件**没有**任何 hex 字面量。
   =========================================================================== */

/** 小于这些尺寸就不画（避免退化画布上的半像素与空布局）。 */
const MIN_W = 32;
const MIN_H = 32;

/**
 * 固定 seed —— 确定性的**唯一**来源。
 * 本文件内**没有** Math.random() / Date.now() / performance.now() /
 * 任何全局可变状态；布局是 (seed, w, h) 的纯函数。
 */
const BRAIN_FORGE_SEED = 20260926;

/**
 * 六类 fate 的着色（顺序 = `configs/default_model.yaml::development.domains`，已定稿）。
 * **只取 BRAND**（唯一色源），不新增色板条目；仅用于「发育几何」模式（§4）。
 */
const FATE_COLORS = [
  BRAND.deepWater,
  BRAND.grassGreen,
  BRAND.sandWarm,
  BRAND.mutationViolet,
  BRAND.blueGrey,
  BRAND.coralOrange,
] as const;

/** GRN / 增殖阶段的单色（fate 未定）。 */
const STAGE_COLORS: Record<string, string> = {
  grn: BRAND.shallowWater,
  proliferate: BRAND.amber,
  fate: BRAND.bone,
  connectome: BRAND.bone,
};

/** 装饰分组的三色（明度层次用，非 cell type —— 见文件头）。 */
const LANES = [BRAIN.particleA, BRAIN.particleB, BRAIN.particleC] as const;

/* 密度按**面积**给，换尺寸时观感一致（否则大画布上会稀稀拉拉）。
   系数来自改造前 240x150 上调好的绝对数：780 粒子 / 90 线段。 */
const PARTICLE_DENSITY = 780 / (240 * 150);
const SEGMENT_DENSITY = 90 / (240 * 150);
/** 线段候选预算倍数：膨胀检查淘汰率高（约 1% 命中），预算远大于目标。 */
const SEGMENT_BUDGET_FACTOR = 100;

/* --- 帧循环参数（动画只改瞬态亮档，不改布局） ------------------------------- */
/** 帧率上限：低帧率足够表现"放电"，且不抢 CPU（也不进 React 热路径）。 */
const FPS = 12;
/** 无激活数据时的环境放电概率（让纹理"呼吸"而不是死图）。 */
const AMBIENT_FIRE = 0.14;
/** 有激活数据时的基础放电概率。 */
const BASE_FIRE = 0.06;

/**
 * 装饰簇的**局部**密集中心（画布比例坐标），共 3 处。
 * x 取 0.22 / 0.70 / 0.38（左右交错、**非单调**），避免被读成某个方向的
 * 全局密度梯度；三处 fy 均匀铺开，构图均衡。
 */
const CLUSTER_SPOTS = [
  { fx: 0.22, fy: 0.28 },
  { fx: 0.7, fy: 0.52 },
  { fx: 0.38, fy: 0.8 },
] as const;

/* 簇半径也按比例给（改造前 240x150 上的 rx 20-28 / ry 13-20）。 */
const CLUSTER_RX = [0.083, 0.033] as const;
const CLUSTER_RY = [0.087, 0.046] as const;

/**
 * mulberry32：32-bit 状态的小 PRNG。
 * 纯整数运算、无外部状态、不读时钟 —— 同一 seed 必得同一序列。
 */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * 逐帧放电判定：`(粒子序号, 帧桶)` -> [0,1)。纯整数运算、无状态；
 * 同一帧桶内结果稳定，因此动画可复现（不同帧桶才变化）。
 */
function hash2(index: number, bucket: number): number {
  let x = (Math.imul(index, 374761393) + Math.imul(bucket, 668265263)) >>> 0;
  x = Math.imul(x ^ (x >>> 13), 1274126177) >>> 0;
  return ((x ^ (x >>> 16)) >>> 0) / 4294967296;
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}

type ParticleSize = 1 | 2 | 3;
type Lane = 0 | 1 | 2;

interface Particle {
  x: number;
  y: number;
  size: ParticleSize;
  lane: Lane;
}
interface MicroSegment {
  x: number;
  y: number;
  /** 2-5 px */
  len: number;
  horizontal: boolean;
}
interface Cell {
  x: number;
  y: number;
  /** 所属装饰簇（-1 = 非簇，如线段垫底）；逐帧"呼吸"按簇整体调制。 */
  cluster: number;
}
interface Layout {
  w: number;
  h: number;
  clusterBase: Cell[];
  segments: MicroSegment[];
  particles: Particle[];
}

/**
 * 由固定 seed 生成整张布局。**纯函数**：同样的 (seed, w, h) 恒得同样的像素。
 */
function buildBrainForgeLayout(w: number, h: number): Layout {
  const rnd = mulberry32(BRAIN_FORGE_SEED);

  const particles: Particle[] = [];
  const clusterBase: Cell[] = [];
  const segments: MicroSegment[] = [];
  if (w < MIN_W || h < MIN_H) return { w, h, clusterBase, segments, particles };

  /* 两张占用图：粒子一层、线段一层。1 = 该逻辑像素被占据。 */
  const particleCells = new Uint8Array(w * h);
  const segmentCells = new Uint8Array(w * h);

  const mark = (grid: Uint8Array, x: number, y: number, mw: number, mh: number) => {
    for (let dy = 0; dy < mh; dy++) {
      for (let dx = 0; dx < mw; dx++) {
        const px = x + dx;
        const py = y + dy;
        if (px >= 0 && px < w && py >= 0 && py < h) grid[py * w + px] = 1;
      }
    }
  };

  const pickSize = (): ParticleSize => {
    const r = rnd();
    if (r < 0.62) return 1;
    if (r < 0.9) return 2;
    return 3;
  };
  const pickLane = (): Lane => (Math.floor(rnd() * 3) % 3) as Lane;

  /* --- 1) 均匀底噪：全画布等概率撒方形粒子 -------------------------------
     无任何位置权重 => 不制造 sparse -> dense 的全局密度梯度。 */
  const baseCount = Math.round(w * h * PARTICLE_DENSITY);
  for (let i = 0; i < baseCount; i++) {
    const size = pickSize();
    const x = Math.floor(rnd() * (w - size + 1));
    const y = Math.floor(rnd() * (h - size + 1));
    particles.push({ x, y, size, lane: pickLane() });
    mark(particleCells, x, y, size, size);
  }

  /* --- 2) 装饰簇：3 处局部密集团块（clusterBase 作极暗垫底） -------------
     簇只抬升**局部**密度；边界用 16 个扇区的随机半径做硬边抖动（不做平滑衰减，
     以保持像素风的硬边），所以簇看上去是不规则的密集团，而不是圆"节点"。 */
  CLUSTER_SPOTS.forEach((spot, spotIndex) => {
    const cx = Math.round(spot.fx * w);
    const cy = Math.round(spot.fy * h);
    const rx = Math.max(3, Math.round(w * (CLUSTER_RX[0] + rnd() * CLUSTER_RX[1])));
    const ry = Math.max(3, Math.round(h * (CLUSTER_RY[0] + rnd() * CLUSTER_RY[1])));

    const SECTORS = 16;
    const edge: number[] = [];
    for (let k = 0; k < SECTORS; k++) edge.push(0.78 + rnd() * 0.5);

    const reach = Math.ceil(Math.max(rx, ry) * 1.4);
    for (let dy = -reach; dy <= reach; dy++) {
      for (let dx = -reach; dx <= reach; dx++) {
        const rr = Math.hypot(dx / rx, dy / ry);
        const ang = Math.atan2(dy, dx);
        const sector =
          Math.abs(Math.floor(((ang + Math.PI) / (Math.PI * 2)) * SECTORS)) % SECTORS;
        if (rr > edge[sector]) continue;
        const x = cx + dx;
        const y = cy + dy;
        if (x < 0 || x >= w || y < 0 || y >= h) continue;
        clusterBase.push({ x, y, cluster: spotIndex });
        if (rnd() < 0.72) {
          const size: ParticleSize = rnd() < 0.8 ? 1 : 2;
          particles.push({ x, y, size, lane: pickLane() });
          mark(particleCells, x, y, size, size);
        }
      }
    }
  });

  /* --- 3) 断开的微小线段：2-5 px，横竖各半 ------------------------------
     「断开」怎么保证：fits() 检查线段自身 Cell **加上 1 px 的方形膨胀邻域**，
     必须在 particleCells 与 segmentCells 两张图上全空。于是：
       (a) 两个端点都不落在任何粒子上（要求更严：线段四周 1 px 内都没有粒子）；
       (b) 线段之间也至少有 1 px 空隙，不可能首尾相接拼成更长的线；
       (c) 每条线段一次 fillRect 画完，从不与另一条共享端点或折行 ——
           因此画面上**不存在**可遍历的路径，也不存在 node/edge 可数。 */
  const fits = (x: number, y: number, len: number, horizontal: boolean): boolean => {
    for (let i = -1; i <= len; i++) {
      for (let j = -1; j <= 1; j++) {
        const gx = horizontal ? x + i : x + j;
        const gy = horizontal ? y + j : y + i;
        if (gx < 0 || gx >= w || gy < 0 || gy >= h) return false;
        const idx = gy * w + gx;
        if (particleCells[idx] || segmentCells[idx]) return false;
      }
    }
    return true;
  };

  const segmentTarget = Math.round(w * h * SEGMENT_DENSITY);
  const budget = Math.max(2000, segmentTarget * SEGMENT_BUDGET_FACTOR);
  for (let attempt = 0; attempt < budget && segments.length < segmentTarget; attempt++) {
    const horizontal = rnd() < 0.5;
    const len = 2 + Math.floor(rnd() * 4); // 2..5
    const x = Math.floor(rnd() * w);
    const y = Math.floor(rnd() * h);
    if (!fits(x, y, len, horizontal)) continue;
    segments.push({ x, y, len, horizontal });
    mark(segmentCells, x, y, horizontal ? len : 1, horizontal ? 1 : len);
  }

  return { w, h, clusterBase, segments, particles };
}

/**
 * 静态层：**只缓存断开线段**（逐帧不变）。装饰簇改为逐帧"呼吸"，故不进静态层
 * （原先把簇画进静态层，用户实测反馈"几个大色块一直不变化"）。
 */
function buildStaticLayer(layout: Layout): HTMLCanvasElement {
  const layer = document.createElement("canvas");
  layer.width = layout.w;
  layer.height = layout.h;
  const ctx = layer.getContext("2d");
  if (!ctx) return layer;
  ctx.imageSmoothingEnabled = false;

  ctx.fillStyle = BRAIN.microSegment;
  for (const s of layout.segments) {
    ctx.fillRect(s.x, s.y, s.horizontal ? s.len : 1, s.horizontal ? 1 : s.len);
  }
  return layer;
}

/**
 * 每帧绘制：静态层 -> 粒子。
 * 粒子的**亮档**由真实激活驱动（高激活 -> 更频繁闪成最亮档），叠加一层沿轴行波；
 * 位置、数量、线段都不变，因此画面上仍无 node/edge 可数。
 */
function drawBrainForge(
  canvas: HTMLCanvasElement,
  layout: Layout,
  staticLayer: HTMLCanvasElement | null,
  activation: number[] | undefined,
  bucket: number,
) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  // 位图缩放交给 CSS 的 .pixelated（最近邻），这里也关掉画布自身的插值。
  ctx.imageSmoothingEnabled = false;
  // 不铺底色：留空即透出面板的 bg-card，纹理与面板同底。
  ctx.clearRect(0, 0, layout.w, layout.h);
  if (staticLayer) ctx.drawImage(staticLayer, 0, 0);

  // 1) 装饰簇垫底：每簇按自己的相位在暗档之间缓慢切换 —— 簇会"呼吸"，不再是一块死色。
  const shades = [BRAIN.clusterBase, BRAIN.microSegment] as const;
  for (let cluster = 0; cluster < CLUSTER_SPOTS.length; cluster++) {
    const phase = Math.sin((bucket / 18) * Math.PI * 2 + cluster * 2.1);
    ctx.fillStyle = shades[phase > 0 ? 1 : 0];
    for (const cell of layout.clusterBase) {
      if (cell.cluster !== cluster) continue;
      ctx.fillRect(cell.x, cell.y, 1, 1);
    }
  }

  // 2) 断开线段（静态层已缓存，见 drawImage）
  const n = activation?.length ?? 0;
  const dim = LANES.length - 1; // 最亮档的下标：放电时用

  // 先把每个粒子分到 3 个桶，避免逐粒子切换 fillStyle。
  const buckets: number[][] = [[], [], []];
  for (let i = 0; i < layout.particles.length; i++) {
    const p = layout.particles[i];
    // 激活值按 (粒子序号, 空间位置) 稳定映射到向量某一维（同一粒子恒看同一维）。
    const level = n > 0 ? clamp01(activation?.[(i * 7 + p.x + p.y) % n] ?? 0) : 0;
    // 沿轴缓慢行波：同一时刻不同列的放电概率不同，读起来像"扫过一层"。
    const wave = 0.5 + 0.5 * Math.sin(((p.x / layout.w) * 2 + bucket / 12) * Math.PI * 2);
    const probability = (n > 0 ? BASE_FIRE + 0.9 * level : AMBIENT_FIRE) * (0.35 + wave);
    const firing = hash2(i, bucket) < probability;
    buckets[firing ? dim : p.lane].push(i);
  }

  for (let lane = 0; lane < LANES.length; lane++) {
    ctx.fillStyle = LANES[lane];
    for (const i of buckets[lane]) {
      const p = layout.particles[i];
      ctx.fillRect(p.x, p.y, p.size, p.size);
    }
  }
}

/** 发育轨迹的当前采样（画真实几何用；`positions` 已在单位方域）。 */
export interface DevelopmentGeometry {
  stage: "grn" | "proliferate" | "fate" | "connectome";
  positions: [number, number][];
  cellType: number[] | null;
  /** 真实邻接表；null = 该阶段无（或用户关闭图层）。 */
  edges: [number, number][] | null;
  /** 逐神经元表达强度（`RGCD §4`）；GRN 阶段用它驱动节点明暗，让"表达上升"可见。 */
  expr?: number[] | null;
  /**
   * `expr` 的**全局参考最大值**（整条轨迹固定）。必须用固定参考，否则"按当前帧自身归一化"会让
   * 每帧都同样亮 —— GRN 迭代看上去毫无变化（实测踩过）。
   */
  exprScale?: number | null;
  /**
   * 增殖阶段：前 `nParents` 个是父代、其余是本轮**新生**子代（模型 §5 冻结"每前体至多分裂一次"
   * ⇒ 只有一轮）。子代用亮色描边标出，让"神经元瞬时增加"这件事可读。
   */
  nParents?: number | null;
  /** 连接概率场 `p_ij`（`RGCD §8`）；`connectome` 阶段画「两幕」的第一幕用。 */
  probs?: number[][] | null;
  /** `connectome` 阶段画哪一幕：`"p"` 概率场 / `"a"` 采样邻接（默认 `"a"`）。 */
  connFrame?: "p" | "a";
}

/**
 * 发育几何绘制：把 `positions` 按**单位方域**等比映射到画布（保纵横比、居中、
 * 整数取整），每个神经元一个 3×3 方块；`cellType` 有值时按六类 fate 上色。
 * **不画连线**（`交互与可视化.md` §八 禁止 node-edge 图；用户 2026-09-27 裁决取"真几何 + fate 着色"）。
 */
function drawDevelopmentGeometry(
  canvas: HTMLCanvasElement,
  geometry: DevelopmentGeometry,
  showEdges: boolean,
): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const w = canvas.width;
  const h = canvas.height;
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, w, h);

  // 单位方域边框（1px）：让"方域"这件事可见，而不是让人猜坐标含义。
  const side = Math.max(8, Math.min(w, h) - 2);
  const ox = Math.round((w - side) / 2);
  const oy = Math.round((h - side) / 2);
  ctx.fillStyle = BRAIN.clusterBase;
  ctx.fillRect(ox - 1, oy - 1, side + 2, 1);
  ctx.fillRect(ox - 1, oy + side, side + 2, 1);
  ctx.fillRect(ox - 1, oy - 1, 1, side + 2);
  ctx.fillRect(ox + side, oy - 1, 1, side + 2);

  // 真实连接（可选图层）：1px 细线（Bresenham 式逐列取整），色取暗档，
  // 让 fate 着色的节点仍是视觉主体。**只画真实存在的边**（`edges` 来自邻接矩阵）。
  const px = (index: number): [number, number] => {
    const [x, y] = geometry.positions[index] ?? [0, 0];
    return [
      ox + Math.round(Math.min(1, Math.max(0, x)) * (side - 1)),
      oy + Math.round(Math.min(1, Math.max(0, y)) * (side - 1)),
    ];
  };
  // 连接层。`connectome` 阶段有**两幕真值**（`交互与可视化.md` §4，用户 2026-09-27 裁决）：
  //   ① `"p"` 概率场 `p_ij = σ(ℓ)`（模型的连接概率；透明度 ∝ p，只画 p ≥ 0.5 的候选）
  //   ② `"a"` 采样邻接 `A`（真实边）。**不画"逐步长边"**——模型里没有这个过程。
  const connFrame = geometry.connFrame ?? "a";
  if (geometry.stage === "connectome" && connFrame === "p" && geometry.probs) {
    const probs = geometry.probs;
    const n = Math.min(probs.length, geometry.positions.length);
    ctx.fillStyle = BRAND.shallowWater;
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        if (i === j) continue;
        const p = probs[i]?.[j] ?? 0;
        if (p < 0.5) continue;
        const [x, y] = px(i);
        ctx.globalAlpha = Math.min(1, Math.max(0.2, p));
        ctx.fillRect(x, y, 1, 1);
      }
    }
    ctx.globalAlpha = 1;
  } else if (showEdges && geometry.edges && geometry.edges.length > 0) {
    ctx.fillStyle = BRAIN.microSegment;
    for (const [i, j] of geometry.edges) {
      if (i >= geometry.positions.length || j >= geometry.positions.length) continue;
      const [x0, y0] = px(i);
      const [x1, y1] = px(j);
      const dx = x1 - x0;
      const dy = y1 - y0;
      const steps = Math.max(Math.abs(dx), Math.abs(dy), 1);
      for (let s = 0; s <= steps; s++) {
        const t = s / steps;
        ctx.fillRect(Math.round(x0 + dx * t), Math.round(y0 + dy * t), 1, 1);
      }
    }
  }

  const fallback = STAGE_COLORS[geometry.stage] ?? BRAIN.particleA;
  // 节点：11×11 实心方块（用户两轮要求加粗：3×3 → 5×5 → 11×11，约 2× 当前）。
  // 外圈先铺 1px 暗底再压亮色，让节点在边交叉处也读得出来。
  // fate 未定的阶段（grn / proliferate）用 `expr` 驱动**明暗**：表达越强越亮 —— 于是 GRN 的
  // 12 步迭代不再是一张静止图（节点尺寸仍是冻结的 11×11，只动明暗）。
  const expr = geometry.expr ?? null;
  const scale = geometry.exprScale ?? (expr && expr.length > 0 ? Math.max(...expr) : 0);
  const nParents = geometry.nParents ?? null;
  const NODE_HALF = 5; // 边长 = 2*half + 1 = 11
  geometry.positions.forEach((_position, index) => {
    const [nx, ny] = px(index);
    const fate = geometry.cellType?.[index];
    const color = typeof fate === "number" ? FATE_COLORS[fate % FATE_COLORS.length] : fallback;
    const alpha =
      typeof fate !== "number" && expr && scale > 0
        ? 0.25 + 0.75 * Math.min(1, (expr[index] ?? 0) / scale)
        : 1;
    const isNewDaughter = nParents !== null && index >= nParents;
    ctx.fillStyle = isNewDaughter ? BRAND.grassGreen : BRAIN.clusterBase;
    ctx.fillRect(nx - NODE_HALF - 1, ny - NODE_HALF - 1, NODE_HALF * 2 + 3, NODE_HALF * 2 + 3);
    ctx.globalAlpha = alpha;
    ctx.fillStyle = color;
    ctx.fillRect(nx - NODE_HALF, ny - NODE_HALF, NODE_HALF * 2 + 1, NODE_HALF * 2 + 1);
    ctx.globalAlpha = 1;
  });
}

export interface BrainForgeVisualProps {
  /**
   * 真实 DanioNet 激活向量（`BrainActivationPayload.fish[<id>]`）。
   * 缺省 = 无数据，退化为环境闪烁（不编造数值）。
   */
  activation?: number[];
  /**
   * 发育几何（§4）。给出时画布改为**真实几何**：`positions` 映射到单位方域，
   * 有 `cellType` 则按 fate 上色；否则退回装饰纹理 + 激活驱动。
   */
  geometry?: DevelopmentGeometry | null;
  /** 是否叠加真实连接图层（`edges`）；默认关，由面板开关控制。 */
  showEdges?: boolean;
}

/**
 * 尺寸**随容器**（与 DnaHelixVisual 同源）：位图宽高取容器的 CSS 像素（取整），
 * 因此逻辑像素 = CSS 像素，1 px 的线段与 1-3 px 的粒子不会被缩放糊掉；
 * 设备像素比 > 1 时是整数倍放大，仍然锐利。
 */
export function BrainForgeVisual({ activation, geometry, showEdges = false }: BrainForgeVisualProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // props 走 ref：帧循环只建一次，不因每次激活帧重建 RAF。
  const activationRef = useRef(activation);
  activationRef.current = activation;
  const geometryRef = useRef(geometry);
  geometryRef.current = geometry;
  const showEdgesRef = useRef(showEdges);
  showEdgesRef.current = showEdges;

  useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas) return;

    let raf = 0;
    let last = 0;
    let layout: Layout | null = null;
    let staticLayer: HTMLCanvasElement | null = null;
    let w = 0;
    let h = 0;

    const resize = () => {
      const nextW = Math.max(MIN_W, Math.round(wrap.clientWidth));
      const nextH = Math.max(MIN_H, Math.round(wrap.clientHeight));
      if (nextW === w && nextH === h) return;
      w = nextW;
      h = nextH;
      if (canvas.width !== w) canvas.width = w;
      if (canvas.height !== h) canvas.height = h;
      // 布局与静态层只在尺寸变化时重算（这是唯一较贵的部分）。
      layout = buildBrainForgeLayout(w, h);
      staticLayer = buildStaticLayer(layout);
    };

    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (now - last < 1000 / FPS) return;
      last = now;
      resize();
      // 几何模式不逐帧重画（边图层可达 ~200 条线）；由下面的 effect 在 prop 变化时画一次。
      if (geometryRef.current) return;
      if (!layout) return;
      drawBrainForge(canvas, layout, staticLayer, activationRef.current, Math.floor(now / (1000 / FPS)));
    };

    resize();
    // 几何模式的首帧由几何 effect 负责（此处只在装饰模式画首帧）。
    if (!geometryRef.current && layout) {
      drawBrainForge(canvas, layout, staticLayer, activationRef.current, 0);
    }
    raf = requestAnimationFrame(frame);

    const ro = new ResizeObserver(() => resize());
    ro.observe(wrap);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, []);

  // 几何模式：geometry / showEdges 变化时重画一次（含首帧与尺寸变化）
  useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas || !geometry) return;
    const render = () => {
      const w = Math.max(MIN_W, Math.round(wrap.clientWidth));
      const h = Math.max(MIN_H, Math.round(wrap.clientHeight));
      if (canvas.width !== w) canvas.width = w;
      if (canvas.height !== h) canvas.height = h;
      drawDevelopmentGeometry(canvas, geometry, showEdges);
    };
    render();
    const ro = new ResizeObserver(render);
    ro.observe(wrap);
    return () => ro.disconnect();
  }, [geometry, showEdges]);

  return (
    <div ref={wrapRef} className="h-full w-full overflow-hidden">
      <canvas
        ref={canvasRef}
        aria-hidden
        // 不加 object-fit：位图与容器同为 CSS 像素 1:1，铺满即等比。
        className="pixelated block h-full w-full"
      />
    </div>
  );
}
