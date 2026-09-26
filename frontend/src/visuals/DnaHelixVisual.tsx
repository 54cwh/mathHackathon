import { useEffect, useRef } from "react";
import { DNA } from "@/design/palette";

/* ===========================================================================
   DNA 双螺旋（**像素风**，扁平硬边）。

   刻意不做的事：
     - 不用 three.js / 不用 @react-three/*：本项目是 pixel-art + scientific UI
       hybrid，PBR / glossy / 平滑渐变不属于这套视觉语言（依赖里虽有 three，
       但对本视觉是多余的，且会把"硬边"变成"高光"）。
     - 不写任何文字或数字，不画坐标轴、图例、刻度。
     - 不做渐变描边、不用线宽过渡：链是整数方块沿轴逐行堆出来的。

   「不是虚点」怎么保证：每行除了画本行的块，还把**该行的块与上一行的块之间的
   垂直跳变补齐**（见 put 调用里的 |c - cp| + BLOCK）。螺距恒定 => 每行最多跳
   约 ROW_STEP 像素，补齐后链是连续的折线，而不是一串孤立方块。

   颜色：只用 @/design/palette 的 DNA 角色，本文件**没有**任何 hex 字面量。
   =========================================================================== */

/** 小于这些尺寸就不画（避免退化画布上出现半像素）。 */
const MIN_W = 8;
const MIN_H = 16;

/** 沿轴每 2 逻辑像素一行；行厚同时是链的块厚。 */
const ROW_STEP = 2;
/** 链的块厚（垂直于轴的那一边）。 */
const BLOCK = 2;
/** 每 8 行画一道横档（约每半圈 4 道，太密会读成梯子）。 */
const RUNG_EVERY = 8;
/**
 * 画布长边内的圈数。**固定圈数**（而不是固定振幅）=> 螺距恒定，链的斜率
 * 只由画布长宽比决定，换尺寸时形状不会退化成一条扁直线。
 */
const TURNS = 2.4;
/** 轴两端留白 = BLOCK + 2。 */
const PAD = BLOCK + 2;

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
 * 参数化螺旋 -> 行表。**无需随机数**：给定 (w, h) 完全确定，且所有坐标都是整数。
 *
 * 轴的取法：**长边作轴**。本面板的视觉区通常是"宽而扁"，竖着画一个正弦会退化成
 * 几个很扁的椭圆（振幅受高度限制，而横向留白浪费）；沿长边画，螺距与斜率才稳定。
 */
function buildHelix(w: number, h: number): Helix {
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
    const t = ((i * ROW_STEP) / L) * TURNS * Math.PI * 2;
    const s = Math.sin(t);
    const d = Math.round(amp * s);
    rows.push({ i, a, s, ca: cc + d, cb: cc - d });
  }
  return { horizontal, rows };
}

/**
 * 绘制顺序 = 真实的遮挡顺序，共四遍：
 *   1) 交织暗部  shadow  —— 只在两链靠近的行铺一块比链稍大的暗底，
 *                          链随后压在它上面，露出的一圈就是"交织点"的暗部。
 *   2) 后链      strandA / strandB（按每行的 s 决定谁在后面）
 *   3) 横档      rung    —— 画在后链之上、前链之下，于是横档"从后面穿过去"。
 *   4) 前链      压在横档与后链之上。
 * 四遍都只调 fillRect，且参数全为整数，因此边缘是硬的、没有任何抗锯齿过渡。
 */
function drawHelix(canvas: HTMLCanvasElement, w: number, h: number) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, w, h);

  const { horizontal, rows } = buildHelix(w, h);
  if (rows.length < 2) return;

  /** 把 (沿轴位置 a, 垂直位置 c, 沿轴长 aLen, 垂直厚 cLen) 映射成 fillRect。 */
  const put = (a: number, c: number, aLen: number, cLen: number) => {
    if (horizontal) ctx.fillRect(a, c, aLen, cLen);
    else ctx.fillRect(c, a, cLen, aLen);
  };
  /** 补齐"上一行块 -> 本行块"的跳变，使链连续（而不是虚点）。 */
  const prevRow = (i: number) => (i > 0 ? rows[i - 1] : rows[0]);

  // 1) 交织暗部：只在 |ca - cb| <= BLOCK 的行（两链重叠处）
  ctx.fillStyle = DNA.shadow;
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
  ctx.fillStyle = DNA.rung;
  for (const r of rows) {
    if (r.i % RUNG_EVERY !== 0) continue;
    const lo = Math.min(r.ca, r.cb) + BLOCK;
    const hi = Math.max(r.ca, r.cb) - 1;
    if (hi < lo) continue;
    put(r.a + Math.floor(ROW_STEP / 2), lo, 1, hi - lo + 1);
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

/**
 * 尺寸**随容器**：位图宽高取容器的 CSS 像素（取整），因此逻辑像素 = CSS 像素，
 * 1 px 的横档不会被缩放糊掉；设备像素比 > 1 时是整数倍放大，仍然锐利。
 *
 * DNA.highlight 本视觉**未使用**：要标出"选定区段"得先有选中态契约（选中的是
 * 第几个碱基、对应螺旋的哪一段），而该契约尚未定义；按「未定契约不得被下游依赖」，
 * 这里不引入一个没有依据的高亮，留作后续接入。
 */
export function DnaHelixVisual() {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas) return;

    let raf = 0;
    const draw = () => {
      const w = Math.max(MIN_W, Math.round(wrap.clientWidth));
      const h = Math.max(MIN_H, Math.round(wrap.clientHeight));
      // 只在尺寸真的变了时改 canvas 属性：改属性会清空画布，且会触发一次 layout，
      // 若无条件赋值可能与 ResizeObserver 形成抖动。
      if (canvas.width !== w) canvas.width = w;
      if (canvas.height !== h) canvas.height = h;
      drawHelix(canvas, w, h);
    };

    draw();
    const ro = new ResizeObserver(() => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(draw);
    });
    ro.observe(wrap);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, []);

  return (
    <div ref={wrapRef} className="h-full w-full overflow-hidden">
      <canvas ref={canvasRef} aria-hidden className="block h-full w-full" />
    </div>
  );
}
