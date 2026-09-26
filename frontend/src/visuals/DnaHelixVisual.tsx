import { useEffect, useRef } from "react";
import { DNA, STRIP } from "@/design/palette";

/* ===========================================================================
   DNA 双螺旋（**像素风**，扁平硬边），由**真实序列**驱动。

   与旧版的区别（2026-09-27，前端功能项接管的改动）：
     1) 新增 `sequence` / `highlightPosition` props：横档颜色 = 该行对应碱基的
        STRIP 色（A/C/G/T），行列 -> 碱基索引的映射是 `flatten()` 的同一坐标序
        （`API接口.md` §2.3：pair0.maternal → pair0.paternal → pair1.maternal →
        pair1.paternal），因此画面与 mutation 的 position 语义一致。
     2) 新增帧循环：相位 `phase` 使正弦沿轴滚动（螺旋"转起来"）。**不是**缩放/淡出
        类动画（那些被 A10 禁止），只是结构沿轴的平移相位。
     3) 布局仍是 `(w, h)` 的纯函数（无随机数、无时钟输入）；`phase` 只影响绘制相位，
        故同尺寸同相位必得同一像素 —— 确定性性质保留。

   刻意不做的事：
     - 不用 three.js / 不用 @react-three/*：pixel-art + scientific UI hybrid。
     - 不写任何文字或数字，不画坐标轴、图例、刻度。
     - 不做渐变描边、不用线宽过渡：链是整数方块沿轴逐行堆出来的。

   「不是虚点」怎么保证：每行除了画本行的块，还把**该行的块与上一行的块之间的
   垂直跳变补齐**（见 put 调用里的 |c - cp| + BLOCK）。螺距恒定 => 每行最多跳
   约 ROW_STEP 像素，补齐后链是连续的折线，而不是一串孤立方块。

   颜色：只用 @/design/palette，本文件**没有**任何 hex 字面量。
   =========================================================================== */

/** 小于这些尺寸就不画（避免退化画布上出现半像素）。 */
const MIN_W = 8;
const MIN_H = 16;

/** 沿轴每 2 逻辑像素一行；行厚同时是链的块厚。 */
const ROW_STEP = 2;
/** 链的块厚（垂直于轴的那一边）。 */
const BLOCK = 2;
/** 无序列时的稀疏横档：每 8 行一道（约每半圈 4 道，太密会读成梯子）。 */
const RUNG_EVERY = 8;
/**
 * 画布长边内的圈数。**固定圈数**（而不是固定振幅）=> 螺距恒定，链的斜率
 * 只由画布长宽比决定，换尺寸时形状不会退化成一条扁直线。
 */
const TURNS = 2.4;
/** 轴两端留白 = BLOCK + 2。 */
const PAD = BLOCK + 2;
/** 滚动速度（圈/秒）与帧率上限：低帧率足够表现"活"，且不抢 CPU。 */
const TURNS_PER_SEC = 0.06;
const FPS = 15;

interface HelixRow {
  /** 行序号，用于决定哪几行画横档 */
  i: number;
  /** 沿轴的整数位置 */
  a: number;
  /** sin(相位)：> 0 表示 strandA 在前（遮挡 B） */
  s: number;
  /** strandA 垂直于轴的整数位置 */
  ca: number;
  /** strandB 垂直于轴的整数位置 */
  cb: number;
}
interface Helix {
  horizontal: boolean;
  rows: HelixRow[];
}

/**
 * 参数化螺旋 -> 行表。**无需随机数**：给定 (w, h, phase) 完全确定，且所有坐标都是整数。
 *
 * 轴的取法：**长边作轴**。本面板的视觉区通常是"宽而扁"，竖着画一个正弦会退化成
 * 几个很扁的椭圆（振幅受高度限制，而横向留白浪费）；沿长边画，螺距与斜率才稳定。
 */
function buildHelix(w: number, h: number, phase: number): Helix {
  const horizontal = w >= h;
  const span = horizontal ? w : h;
  const cross = horizontal ? h : w;

  const rows: HelixRow[] = [];
  const L = span - 2 * PAD;
  // 振幅：先按"每半圈抬升 2*amp"求出约 45 度的斜率，再用cross 方向的 30% 封顶。
  const amp = Math.max(
    BLOCK + 2,
    Math.min(Math.round(L / (2 * Math.PI * TURNS)), Math.round(cross * 0.3)),
  );
  if (L < ROW_STEP * 8) return { horizontal, rows };
  if (cross < 2 * PAD + BLOCK) return { horizontal, rows };

  const cc = Math.round(cross / 2);
  for (let a = PAD, i = 0; a <= span - PAD; a += ROW_STEP, i++) {
    const t = ((i * ROW_STEP) / L) * TURNS * Math.PI * 2 + phase;
    const s = Math.sin(t);
    const d = Math.round(amp * s);
    rows.push({ i, a, s, ca: cc + d, cb: cc - d });
  }
  return { horizontal, rows };
}

export interface DnaHelixVisualProps {
  /** 真实碱基串（`flatten()` 展平的 512 碱基）。缺省 = 纯装饰链，不带碱基色。 */
  sequence?: string;
  /** 高亮第 i 个碱基对应的那一行（0-based；见 `API接口.md` §2.3 坐标序）。 */
  highlightPosition?: number;
}

/**
 * 绘制顺序 = 真实的遮挡顺序，共四遍：
 *   1) 交织暗部  shade   —— 只在两链靠近的行铺一块比链稍大的暗底。
 *   2) 后链      strandA / strandB（按每行的 s 决定谁在后面）
 *   3) 横档      rung    —— 画在后链之上、前链之下，于是横档"从后面穿过去"；
 *                          有真实序列时按碱基上 STRIP 色，且每行都画（一行 = 一个碱基）。
 *   4) 前链      压在横档与后链之上。
 * 四遍都只调 fillRect，且参数全为整数，因此边缘是硬的、没有任何抗锯齿过渡。
 */
function drawHelix(
  canvas: HTMLCanvasElement,
  w: number,
  h: number,
  sequence: string | undefined,
  highlightPosition: number | undefined,
  phase: number,
) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, w, h);

  const { horizontal, rows } = buildHelix(w, h, phase);
  if (rows.length < 2) return;

  /** 把 (沿轴位置 a, 垂直位置 c, 沿轴长 aLen, 垂直厚 cLen) 映射成 fillRect。 */
  const put = (a: number, c: number, aLen: number, cLen: number) => {
    if (horizontal) ctx.fillRect(a, c, aLen, cLen);
    else ctx.fillRect(c, a, cLen, aLen);
  };
  /** 补齐"上一行块 -> 本行块"的跳变，使链连续（而不是虚点）。 */
  const prevRow = (i: number) => (i > 0 ? rows[i - 1] : rows[0]);

  /** 行 -> 碱基索引：与 flatten() 的坐标序一致（线性覆盖整条序列）。 */
  const baseIndexAt = (i: number): number => {
    if (!sequence || sequence.length === 0) return -1;
    return Math.min(sequence.length - 1, Math.floor((i * sequence.length) / rows.length));
  };

  // 1) 交织暗部：只在 |ca - cb| <= BLOCK 的行（两链重叠处）
  ctx.fillStyle = DNA.shade;
  for (const r of rows) {
    if (Math.abs(r.ca - r.cb) > BLOCK) continue;
    const lo = Math.min(r.ca, r.cb) - 1;
    const hi = Math.max(r.ca, r.cb) + BLOCK + 1;
    put(r.a - 1, lo, ROW_STEP + 2, hi - lo);
  }

  // 2) 后链
  for (const r of rows) {
    const p = prevRow(r.i);
    const c = r.s > 0 ? r.cb : r.ca;
    const cp = r.s > 0 ? p.cb : p.ca;
    ctx.fillStyle = r.s > 0 ? DNA.strandB : DNA.strandA;
    put(r.a, Math.min(c, cp), ROW_STEP, Math.abs(c - cp) + BLOCK);
  }

  // 3) 横档：连接两条链。两链交叉处宽度不足，自然跳过（画不出负长度的横档）。
  for (const r of rows) {
    const lo = Math.min(r.ca, r.cb) + BLOCK;
    const hi = Math.max(r.ca, r.cb) - 1;
    if (hi < lo) continue;

    const baseIndex = baseIndexAt(r.i);
    const selected = baseIndex >= 0 && baseIndex === highlightPosition;
    if (baseIndex < 0 && r.i % RUNG_EVERY !== 0) continue; // 无数据时退回稀疏装饰横档

    let fill: string = DNA.rung;
    if (baseIndex >= 0) {
      const ch = sequence?.[baseIndex];
      fill = selected ? DNA.highlight : (baseFill(ch) ?? DNA.rung);
    }
    ctx.fillStyle = fill;
    const thickness = selected ? 2 : 1;
    put(r.a + Math.floor(ROW_STEP / 2) - (selected ? 1 : 0), lo, thickness, hi - lo + 1);
  }

  // 4) 前链
  for (const r of rows) {
    const p = prevRow(r.i);
    const c = r.s > 0 ? r.ca : r.cb;
    const cp = r.s > 0 ? p.ca : p.cb;
    ctx.fillStyle = r.s > 0 ? DNA.strandA : DNA.strandB;
    put(r.a, Math.min(c, cp), ROW_STEP, Math.abs(c - cp) + BLOCK);
  }
}

/** 碱基 -> STRIP 色；未知字符返回 undefined（调用方回退到装饰色）。 */
function baseFill(ch: string | undefined): string | undefined {
  switch (ch) {
    case "A":
      return STRIP.A;
    case "C":
      return STRIP.C;
    case "G":
      return STRIP.G;
    case "T":
      return STRIP.T;
    default:
      return undefined;
  }
}

/**
 * 尺寸**随容器**：位图宽高取容器的 CSS 像素（取整），因此逻辑像素 = CSS 像素，
 * 1 px 的横档不会被缩放糊掉；设备像素比 > 1 时是整数倍放大，仍然锐利。
 */
export function DnaHelixVisual({ sequence, highlightPosition }: DnaHelixVisualProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // props 走 ref：帧循环只建一次，不因每次数据更新重建 RAF。
  const propsRef = useRef({ sequence, highlightPosition });
  propsRef.current = { sequence, highlightPosition };

  useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas) return;

    let raf = 0;
    let phase = 0;
    let last = 0;
    let w = 0;
    let h = 0;

    const resize = () => {
      w = Math.max(MIN_W, Math.round(wrap.clientWidth));
      h = Math.max(MIN_H, Math.round(wrap.clientHeight));
      // 只在尺寸真的变了时改 canvas 属性：改属性会清空画布，且会触发一次 layout。
      if (canvas.width !== w) canvas.width = w;
      if (canvas.height !== h) canvas.height = h;
    };

    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (now - last < 1000 / FPS) return;
      last = now;
      resize();
      phase += (TWO_PI * TURNS_PER_SEC * 1) / FPS;
      const { sequence: seq, highlightPosition: pos } = propsRef.current;
      drawHelix(canvas, w, h, seq, pos, phase);
    };

    resize();
    drawHelix(canvas, w, h, propsRef.current.sequence, propsRef.current.highlightPosition, 0);
    raf = requestAnimationFrame(frame);

    const ro = new ResizeObserver(() => resize());
    ro.observe(wrap);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, []);

  return (
    <div ref={wrapRef} className="h-full w-full overflow-hidden">
      {/* 也加 .pixelated：位图 = 容器 CSS 像素，在 DPR>1（本机 1.5）时是 1.5 倍
          上采样，不加则被双线性插值糊掉硬边；1px 横档会消失。 */}
      <canvas ref={canvasRef} aria-hidden className="pixelated block h-full w-full" />
    </div>
  );
}

const TWO_PI = Math.PI * 2;
