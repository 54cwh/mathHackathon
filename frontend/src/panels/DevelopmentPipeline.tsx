import { useEffect, useMemo, useRef, useState } from "react";
import { Pause, Play } from "lucide-react";
import { BRAND } from "@/design/palette";
import { MetricChart } from "@/visuals/MetricChart";
import { drawLineChart, type SeriesDef } from "@/visuals/chartPrimitives";
import { getLatestDevelopment, subscribeDevelopment } from "@/store/labBus";
import type { DevelopmentTraceSample } from "@/api/types";

/**
 * §4 发育管线分阶段视图（`交互与可视化.md` §4 的动画顺序）。
 *
 * 数据：`POST /v1/developments?with_trace=true` 返回的**真实逐阶段轨迹**
 * （GRN 逐步 → 增殖 → 连接组；`API接口.md` §2.3）。记录只读、不抽随机数，故看到的过程
 * 就是该个体真实发育的中间态，不是叙事动画。
 *
 * 播放：把轨迹当时间线，用 `cursor` 逐步揭示（PLAY/PAUSE + 拖动）。播放不引入新数据，
 * 也不改任何后端状态。
 */

const STAGE_FPS = 3; // 轨迹只有 14 个采样点，慢放才看得清
/** 阶段 -> 中文说明（顺序与后端列表一致）。 */
const STAGE_LABEL: Record<DevelopmentTraceSample["stage"], string> = {
  grn: "GRN 表达迭代（§4）",
  proliferate: "precursor 增殖（§5）",
  connectome: "连接组成形（§6）",
};

export function DevelopmentPipeline() {
  const [trace, setTrace] = useState<DevelopmentTraceSample[] | null>(
    () => getLatestDevelopment().trace,
  );
  const [genomeId, setGenomeId] = useState<string | null>(
    () => getLatestDevelopment().genomeId,
  );
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const cursorRef = useRef(0);
  const playingRef = useRef(false);

  // 订阅 DNA 实验室的发育结果（模块级总线，不进 React 热路径）
  useEffect(
    () =>
      subscribeDevelopment((payload) => {
        setTrace(payload.trace);
        setGenomeId(payload.genomeId);
        cursorRef.current = payload.trace ? payload.trace.length - 1 : 0;
        setCursor(cursorRef.current);
        playingRef.current = true; // 新数据到达即从头播放
        setPlaying(true);
        cursorRef.current = 0;
        setCursor(0);
      }),
    [],
  );

  // 播放循环
  useEffect(() => {
    let raf = 0;
    let last = 0;
    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (!playingRef.current) return;
      if (now - last < 1000 / STAGE_FPS) return;
      last = now;
      const total = trace?.length ?? 0;
      if (total === 0) return;
      const next = cursorRef.current + 1;
      if (next >= total) {
        playingRef.current = false;
        setPlaying(false);
        return;
      }
      cursorRef.current = next;
      setCursor(next);
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [trace]);

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
          onClick={() => {
            if (!playing && cursor >= sliderMax) {
              cursorRef.current = 0;
              setCursor(0);
            }
            playingRef.current = !playingRef.current;
            setPlaying(playingRef.current);
          }}
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
        onChange={(e) => {
          playingRef.current = false;
          setPlaying(false);
          const next = Number(e.target.value);
          cursorRef.current = next;
          setCursor(next);
        }}
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
