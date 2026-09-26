import { useEffect, useRef } from "react";

/**
 * 图表画布壳：位图 = 容器 CSS 像素（与 `DnaHelixVisual` / `BrainForgeVisual` 同源），
 * 尺寸变化时重画。绘制逻辑由 `draw(ctx, w, h)` 提供（见 `MetricChart.ts` 的原语）。
 *
 * 不做帧循环：指标只在数据变化时重画（没有动画需求，也不该有——A10 禁缩放/淡出类动画）。
 */
export interface MetricChartProps {
  /** 画布高度（CSS px）。 */
  height: number;
  draw: (ctx: CanvasRenderingContext2D, w: number, h: number) => void;
  ariaLabel: string;
}

export function MetricChart({ height, draw, ariaLabel }: MetricChartProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawRef = useRef(draw);
  drawRef.current = draw;

  useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas) return;

    const render = () => {
      const w = Math.max(8, Math.round(wrap.clientWidth));
      const h = Math.max(8, Math.round(wrap.clientHeight));
      if (canvas.width !== w) canvas.width = w;
      if (canvas.height !== h) canvas.height = h;
      const ctx = canvas.getContext("2d");
      if (ctx) drawRef.current(ctx, w, h);
    };

    render();
    const ro = new ResizeObserver(render);
    ro.observe(wrap);
    return () => ro.disconnect();
  }, [draw]);

  return (
    <div ref={wrapRef} className="w-full" style={{ height }}>
      <canvas ref={canvasRef} role="img" aria-label={ariaLabel} className="pixelated block h-full w-full" />
    </div>
  );
}
