import { useEffect, useRef } from "react";

/* ===========================================================================
   DNA 双螺旋（**示意素材** + 纵向滚动）。

   与上一版的区别（2026-09-27 用户裁决）：
     - 画面改为 `public/assets/dna/helix.png`（像素风双螺旋素材，**自带透明背景**，
       **纵向无缝可平铺**：顶行像素 == 底行像素），纵向**平铺多份** + 匀速滚动 ⇒ 无缝循环的
       "链在流动"——**不再由真实序列绘制**。
     - 因此 `sequence` / `highlightPosition` 两个 props 一并移除：素材不承载
       碱基身份与突变位点。**真实碱基的可视证据由下方四条单倍体条带（
       `NucleotideStrip`，含选中位高亮）承担**（`交互与可视化.md` §15）。
     - 标题旁的读数由「显示 <单倍体>」改为「示意素材」：素材与当前选中的
       单倍体无关，继续标"显示 X"会读成"这条链就是 X"。

   刻意不做的事：
     - 不抠图/不改素材像素：素材下缘是 alpha=0 的透明底，直接叠在面板背景上即可；
       `alphaBBox()` 只用来裁掉四周空白，避免把大量透明区缩进画面。
     - 不做缩放动画、不做淡入淡出（`A10`）：只有沿轴的匀速平移。
     - 不用 three.js / 不用 @react-three/*（`README.md` 技术栈 3D DNA 条推迟）。

   确定性：`(容器尺寸, 时间)` 的函数，无随机数；位图取容器 CSS 像素，逻辑像素 =
   CSS 像素。
   =========================================================================== */

const MIN_W = 8;
const MIN_H = 16;

/** 素材路径（`public/assets/` 下，构建后按原路径发布）。 */
const IMG_SRC = "/assets/dna/helix.png";
/** 帧率上限：滚动很慢，15 fps 足够，且不抢 CPU。 */
const FPS = 15;
/**
 * 缩放：素材裁到不透明包围盒后，其高度映射为容器高度的该倍数。
 * 素材是**纵向无缝平铺**的（顶行像素 == 底行像素），故任意缩放都无缝；`1.0` = 一屏正好一个周期。
 */
const ZOOM = 0.4;
/** 滚动速度（CSS px/s）：能看清横档，同时看得出链在快速流动。 */
const SCROLL_PX_PER_SEC = 55;

interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

/**
 * 不透明像素的包围盒（裁掉素材四周空白）。逐像素扫一次，只在加载后算一次；
 * 扫不到任何不透明像素时返回整幅（调用方回退）。
 */
function alphaBBox(img: HTMLImageElement): Box {
  const w = img.naturalWidth;
  const h = img.naturalHeight;
  const full: Box = { x: 0, y: 0, w, h };
  if (w === 0 || h === 0) return full;
  const probe = document.createElement("canvas");
  probe.width = w;
  probe.height = h;
  const pctx = probe.getContext("2d");
  if (!pctx) return full;
  pctx.drawImage(img, 0, 0);
  let data: Uint8ClampedArray;
  try {
    data = pctx.getImageData(0, 0, w, h).data;
  } catch {
    return full; // 同源素材不应触发；保险起见回退整幅
  }
  let x0 = w;
  let y0 = h;
  let x1 = -1;
  let y1 = -1;
  for (let y = 0; y < h; y++) {
    const row = y * w * 4;
    for (let x = 0; x < w; x++) {
      if (data[row + x * 4 + 3] > 8) {
        if (x < x0) x0 = x;
        if (x > x1) x1 = x;
        if (y < y0) y0 = y;
        if (y > y1) y1 = y;
      }
    }
  }
  if (x1 < x0 || y1 < y0) return full;
  return { x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1 };
}

/**
 * 尺寸**随容器**：位图宽高取容器的 CSS 像素（取整），因此逻辑像素 = CSS 像素；
 * DPR > 1 时是整数倍放大。
 */
export function DnaHelixVisual() {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let ready = false;
    let crop: Box = { x: 0, y: 0, w: 0, h: 0 };
    const img = new Image();
    img.onload = () => {
      crop = alphaBBox(img);
      ready = true;
    };
    img.src = IMG_SRC;

    let raf = 0;
    let w = 0;
    let h = 0;
    let last = 0;
    /** 已滚动的距离（CSS px，单调递增；取模在绘制时做）。 */
    let scroll = 0;

    const resize = () => {
      w = Math.max(MIN_W, Math.round(wrap.clientWidth));
      h = Math.max(MIN_H, Math.round(wrap.clientHeight));
      // 只在尺寸真的变了时改 canvas 属性：改属性会清空画布，且会触发一次 layout。
      if (canvas.width !== w) canvas.width = w;
      if (canvas.height !== h) canvas.height = h;
    };

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      if (!ready || crop.h === 0) return;
      // 素材高度 -> 容器高度 × ZOOM；横向居中；纵向平铺（三份，视图窗口恒被覆盖）。
      const scale = (h * ZOOM) / crop.h;
      const dw = Math.max(1, Math.round(crop.w * scale));
      const dh = Math.max(1, Math.round(crop.h * scale));
      // 缩小时用平滑（素材像素密度高于显示区，nearest 会丢像素/出摩尔纹）；
      // 放大时关掉，保住像素硬边（与 Arena 素材同规）。
      ctx.imageSmoothingEnabled = scale < 1;
      const x = Math.round((w - dw) / 2);
      // 向上滚动：offset ∈ (-dh, 0]
      const offset = -(((scroll % dh) + dh) % dh);
      // 纵向平铺足够多份：`ceil(h/dh) + 2` 保证任意缩放/任意 ZOOM 下视图窗口都被覆盖（无缝）。
      const copies = Math.ceil(h / dh) + 2;
      for (let i = -1; i < copies; i++) {
        ctx.drawImage(img, crop.x, crop.y, crop.w, crop.h, x, Math.round(offset + i * dh), dw, dh);
      }
    };

    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (now - last < 1000 / FPS) return;
      const dt = last === 0 ? 0 : Math.min(0.25, (now - last) / 1000);
      last = now;
      scroll += SCROLL_PX_PER_SEC * dt;
      resize();
      draw();
    };

    resize();
    draw();
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
      <canvas ref={canvasRef} aria-hidden className="block h-full w-full" />
    </div>
  );
}
