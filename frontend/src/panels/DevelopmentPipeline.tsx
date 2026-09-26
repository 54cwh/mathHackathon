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
  grn: "GRN 表达迭代",
  proliferate: "前体细胞增殖",
  fate: "细胞分化落定",
  connectome: "连接组成形",
};

export interface DevelopmentPipelineProps {
  trace: DevelopmentTraceSample[] | null;
  genomeId: string | null;
  cursor: number;
  playing: boolean;
  /** 该个体是否正在推送实时神经活动（点亮阶段轨末端的 DANIONET）。 */
  activationLive?: boolean;
  onCursor: (index: number) => void;
  onTogglePlay: () => void;
}

/** §4 的发育阶段序列（`交互与可视化.md` §4）：阶段轨的固定顺序。 */
const PIPELINE_STAGES = [
  "MOTIF",
  "q(S)",
  "GRN",
  "DIVISION",
  "DIFFERENTIATION",
  "CONNECTIONS",
  "DANIONET",
] as const;

/** 阶段轨（§4）：整条序列一目了然，当前项高亮；末端 DANIONET 仅在收到实时激活时点亮。 */
function stageRail(activeIndex: number) {
  return (
    <div role="list" aria-label="development stages" className="flex flex-wrap items-center gap-1">
      {PIPELINE_STAGES.map((label, index) => {
        const active = index === activeIndex;
        return (
          <span
            key={label}
            role="listitem"
            aria-current={active ? "step" : undefined}
            className={`border border-border px-1.5 py-0.5 font-pixel text-[9px] leading-none ${
              active ? "bg-brand-fish-navy text-brand-bone" : "text-muted-foreground"
            }`}
          >
            {label}
          </span>
        );
      })}
    </div>
  );
}

/** 由"当前轨迹阶段 + 是否走完 + 是否在推激活"决定阶段轨高亮项（不猜、不跳段）。 */
function stageIndex(
  current: DevelopmentTraceSample["stage"] | null,
  complete: boolean,
  activationLive: boolean,
): number {
  if (!current) return 0; // 尚未发育：停在起点 MOTIF
  if (complete && activationLive) return 6; // 发育走完且收到激活：DANIONET
  switch (current) {
    case "grn":
      return 2;
    case "proliferate":
      return 3;
    case "fate":
      return 4;
    case "connectome":
      return 5;
  }
}

export function DevelopmentPipeline({
  trace,
  genomeId,
  cursor,
  playing,
  activationLive = false,
  onCursor,
  onTogglePlay,
}: DevelopmentPipelineProps) {
  const revealed = useMemo(() => (trace ? trace.slice(0, cursor + 1) : []), [trace, cursor]);
  const current = revealed[revealed.length - 1];

  if (!trace || trace.length === 0) {
    return (
      <div className="space-y-2 border border-border p-2">
        <div className="font-pixel text-[10px] leading-none">DEVELOPMENT PIPELINE</div>
        {stageRail(0)}
        <p className="font-mono text-[10px] text-muted-foreground">
          尚无发育轨迹。在左侧 DNA2Brain Lab 点 DEVELOP 开始。
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
  const activeIndex = stageIndex(
    current ? current.stage : null,
    cursor >= sliderMax,
    activationLive,
  );

  return (
    <div className="space-y-2 border border-border p-2">
      <div className="flex items-center justify-between gap-2">
        <span className="font-pixel text-[10px] leading-none">DEVELOPMENT PIPELINE</span>
        <span className="truncate font-mono text-[10px] text-muted-foreground">
          {genomeId ?? "—"}
        </span>
      </div>

      {stageRail(activeIndex)}

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
          <span>神经元数</span>
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
          <span>平均表达 |g|</span>
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
          分裂数 {current?.n_divisions ?? "—"} · 连接数 {current?.n_edges ?? "—"}
        </span>
        <span>{current ? `max|g| ${current.max_abs.toFixed(3)}` : ""}</span>
      </div>

      <p className="font-mono text-[10px] text-muted-foreground">
        真实发育过程：GRN 表达迭代 {trace.filter((s) => s.stage === "grn").length - 1} 步 →
        前体细胞增殖 → 细胞分化 → 连接组成形。均为模型真实中间状态。
      </p>
    </div>
  );
}
