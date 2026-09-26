import { useMemo } from "react";
import { Pause, Play } from "lucide-react";
import { BRAND } from "@/design/palette";
import { MetricChart } from "@/visuals/MetricChart";
import { drawLineChart, type SeriesDef } from "@/visuals/chartPrimitives";
import type { DevelopmentTraceSample } from "@/api/types";

/**
 * §4 发育管线的**时间线控件 + 曲线**（受控组件）。
 *
 * 状态（游标/播放）由 `BrainForgePanel` 持有 —— 因为同一游标还要驱动
 * `BrainForgeVisual` 的**真实几何**，两边必须同一个游标，否则图与曲线不同步。
 */

const STAGE_LABEL: Record<DevelopmentTraceSample["stage"], string> = {
  grn: "GRN 表达迭代（§4）",
  proliferate: "precursor 增殖（§5）",
  connectome: "连接组成形（§6）",
};

export interface DevelopmentPipelineProps {
  trace: DevelopmentTraceSample[] | null;
  genomeId: string | null;
  cursor: number;
  playing: boolean;
  onCursor: (index: number) => void;
  onTogglePlay: () => void;
}

export function DevelopmentPipeline({
  trace,
  genomeId,
  cursor,
  playing,
  onCursor,
  onTogglePlay,
}: DevelopmentPipelineProps) {
  const revealed = useMemo(() => (trace ? trace.slice(0, cursor + 1) : []), [trace, cursor]);
  const current = revealed[revealed.length - 1];

  if (!trace || trace.length === 0) {
    return (
      <div className="border border-border p-2">
        <div className="mb-1 font-pixel text-[10px] leading-none">DEVELOPMENT PIPELINE</div>
        <p className="font-mono text-[10px] text-muted-foreground">
          尚无发育轨迹：在左侧 DNA2Brain Lab 点 DEVELOP（会以 `with_trace=true` 拉取真实过程）。
        </p>
      </div>
    );
  }

  const neurons: SeriesDef[] = [
    { label: "n_neurons", color: BRAND.grassGreen, values: revealed.map((s) => s.n_neurons) },
  ];
  const expression: SeriesDef[] = [
    { label: "mean|g|", color: BRAND.shallowWater, values: revealed.map((s) => s.mean_abs) },
  ];

  const sliderMax = Math.max(0, trace.length - 1);

  return (
    <div className="space-y-2 border border-border p-2">
      <div className="flex items-center justify-between gap-2">
        <span className="font-pixel text-[10px] leading-none">DEVELOPMENT PIPELINE</span>
        <span className="truncate font-mono text-[10px] text-muted-foreground">
          {genomeId ?? "—"}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onTogglePlay}
          className="inline-flex items-center gap-1 border border-border px-2 py-0.5 font-pixel text-[10px] leading-none"
        >
          {playing ? <Pause className="size-3" /> : <Play className="size-3" />}
          {playing ? "PAUSE" : "PLAY"}
        </button>
        <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
          {cursor + 1}/{trace.length}
        </span>
        <span className="truncate font-mono text-[10px]">
          {current ? STAGE_LABEL[current.stage] : ""}
          {current?.stage === "grn" ? ` · step ${current.step}` : ""}
        </span>
      </div>

      <input
        type="range"
        min={0}
        max={sliderMax}
        value={cursor}
        onChange={(e) => onCursor(Number(e.target.value))}
        aria-label="development stage"
        className="w-full"
      />

      <div>
        <div className="mb-0.5 flex justify-between font-mono text-[10px] text-muted-foreground">
          <span>n_neurons</span>
          <span>{current?.n_neurons ?? "—"}</span>
        </div>
        <MetricChart
          height={34}
          ariaLabel="neuron count along development"
          draw={(ctx: CanvasRenderingContext2D, w: number, h: number) =>
            void drawLineChart(ctx, w, h, neurons, 0)
          }
        />
      </div>

      <div>
        <div className="mb-0.5 flex justify-between font-mono text-[10px] text-muted-foreground">
          <span>mean|g|（表达量代理）</span>
          <span>{current ? current.mean_abs.toFixed(4) : "—"}</span>
        </div>
        <MetricChart
          height={34}
          ariaLabel="mean expression along development"
          draw={(ctx: CanvasRenderingContext2D, w: number, h: number) =>
            void drawLineChart(ctx, w, h, expression)
          }
        />
      </div>

      <div className="flex justify-between font-mono text-[10px] text-muted-foreground">
        <span>
          n_divisions {current?.n_divisions ?? "—"} · n_edges {current?.n_edges ?? "—"}
        </span>
        <span>{current ? `max|g| ${current.max_abs.toFixed(3)}` : ""}</span>
      </div>

      <p className="font-mono text-[10px] text-muted-foreground">
        真实轨迹：GRN {trace.filter((s) => s.stage === "grn").length - 1} 步 → 增殖 → 连接组
        （`/v1/developments?with_trace=true`）。开关该参数不改变任何数值。
      </p>
    </div>
  );
}
