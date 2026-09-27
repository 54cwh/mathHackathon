import { SectionLabel } from "@/components/SectionLabel";
import { useMemo, useState } from "react";
import { BRAND } from "@/design/palette";
import { MetricChart } from "@/visuals/MetricChart";
import {
  drawEventMarkers,
  drawHistogram,
  drawLineChart,
  type SeriesDef,
} from "@/visuals/chartPrimitives";
import type { RunEvolution, RunGeneration } from "@/api/types";

/**
 * §8 Evolution Dashboard 的九项指标（`交互与可视化.md` §8）。
 *
 * 数据来源：`/v1/runs/{id}/evolution`（`API接口.md` §2.4），逐代行 + 逐个体 fitness。
 * **诚实口径**：老 producer 的 run 缺 `p_A`/`mean_*` 等字段 —— 缺失一律显示「未记录」，
 * 不补 0、不画点（`禁止 AI 填空`）。
 *
 * 九项对照：generation ✔ / p(A)·p(B) ✔ / phenotype 频率 ✔ / fitness 分布 ✔（含直方图）/
 * viability rate ✔ / mean neuron·edge·tau ✔ / environment-change marker ✔（红色竖线标记）。
 */

const LINE_HEIGHT = 44;
const HIST_HEIGHT = 56;

function fmt(value: number | undefined, digits = 3): string {
  return typeof value === "number" ? value.toFixed(digits) : "—";
}

function pick(generations: RunGeneration[], key: keyof RunGeneration): (number | null)[] {
  return generations.map((row) => {
    const value = row[key];
    return typeof value === "number" ? value : null;
  });
}

export function EvolutionMetrics({ evolution }: { evolution: RunEvolution }) {
  const generations = evolution.generations;
  const last = generations[generations.length - 1];
  const [histGeneration, setHistGeneration] = useState<number | null>(null);

  const markedIndices = useMemo(
    () =>
      generations
        .map((row, index) => (row.event ? index : -1))
        .filter((index) => index >= 0),
    [generations],
  );

  const histIndex = useMemo(() => {
    if (generations.length === 0) return 0;
    if (histGeneration === null) return generations.length - 1;
    const found = generations.findIndex((row) => row.generation === histGeneration);
    return found >= 0 ? found : generations.length - 1;
  }, [generations, histGeneration]);

  const hist = useMemo(
    () => evolution.fitness.find((item) => item.generation === generations[histIndex]?.generation),
    [evolution.fitness, generations, histIndex],
  );

  if (generations.length === 0) {
    return (
      <div className="border border-border p-2 font-mono text-[10px] text-muted-foreground">
        该 run 没有 evolution.jsonl（或没有有效行）——无逐代指标可显示。
      </div>
    );
  }

  const pSeries: SeriesDef[] = [
    { label: "p(A)", color: BRAND.fishBlue, values: pick(generations, "p_A") },
    { label: "p(B)", color: BRAND.amber, values: pick(generations, "p_B") },
  ];
  const morphSeries: SeriesDef[] = [
    { label: "neurons", color: BRAND.shallowWater, values: pick(generations, "mean_neuron") },
    { label: "edges", color: BRAND.grassGreen, values: pick(generations, "mean_edge") },
  ];
  const tauSeries: SeriesDef[] = [
    { label: "tau", color: BRAND.mutationViolet, values: pick(generations, "mean_tau") },
  ];
  const viabilitySeries: SeriesDef[] = [
    {
      label: "viability",
      color: BRAND.lightGrass,
      values: generations.map((row) =>
        typeof row.n_viable === "number" && typeof row.n_individuals === "number" && row.n_individuals > 0
          ? row.n_viable / row.n_individuals
          : null,
      ),
    },
  ];
  const fitnessSeries: SeriesDef[] = [
    { label: "fitness mean", color: BRAND.amber, values: pick(generations, "fitness_mean") },
  ];

  return (
    <div className="space-y-2">
      {/* 头部：代数 + 环境变更标记 */}
      <div className="flex items-center justify-between border border-border p-2 font-mono text-[10px]">
        <span>
          generation <span className="text-brand-bone">{last.generation}</span> / {generations.length}
        </span>
        <span className={markedIndices.length ? "text-brand-danger-red" : "text-muted-foreground"}>
          env marker {markedIndices.length ? `×${markedIndices.length}` : "无"}
        </span>
        <span className="text-muted-foreground">
          n {last.n_viable ?? "—"}/{last.n_individuals ?? "—"}
        </span>
      </div>

      {/* p(A) / p(B) + 等位频率表 */}
      <section className="border border-border p-2">
        <div className="mb-1 flex items-center justify-between">
          <SectionLabel en="P(A) / P(B)" zh="表型比例" />
          <span className="font-mono text-[10px] text-muted-foreground">
            {fmt(last.p_A, 2)} / {fmt(last.p_B, 2)}
          </span>
        </div>
        <MetricChart
          height={LINE_HEIGHT}
          ariaLabel="p(A) and p(B) over generations"
          draw={(ctx: CanvasRenderingContext2D, w: number, h: number) => {
            const ok = drawLineChart(ctx, w, h, pSeries, 0);
            if (ok) drawEventMarkers(ctx, w, h, generations.length, markedIndices);
          }}
        />
        <table className="mt-1 w-full font-mono text-[10px]">
          <thead>
            <tr className="text-muted-foreground">
              <th className="text-left font-normal">phenotype</th>
              {Object.keys(last.phenotype_freq ?? {}).map((key) => (
                <th key={key} className="text-right font-normal">
                  {key}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="text-muted-foreground">freq</td>
              {Object.keys(last.phenotype_freq ?? {}).length === 0 ? (
                <td className="text-muted-foreground">未记录</td>
              ) : (
                Object.values(last.phenotype_freq ?? {}).map((value, index) => (
                  <td key={index} className="text-right">
                    {value.toFixed(2)}
                  </td>
                ))
              )}
            </tr>
          </tbody>
        </table>
      </section>

      {/* fitness：均值折线 + 标准差 + 逐个体分布直方图 */}
      <section className="border border-border p-2">
        <div className="mb-1 flex items-center justify-between">
          <SectionLabel en="FITNESS" zh="适应度" />
          <span className="font-mono text-[10px] text-muted-foreground">
            mean {fmt(last.fitness_mean)} ± {fmt(last.fitness_std)}
          </span>
        </div>
        <MetricChart
          height={LINE_HEIGHT}
          ariaLabel="fitness mean over generations"
          draw={(ctx: CanvasRenderingContext2D, w: number, h: number) => {
            const ok = drawLineChart(ctx, w, h, fitnessSeries);
            if (ok) drawEventMarkers(ctx, w, h, generations.length, markedIndices);
          }}
        />
        <div className="mt-1 flex items-center justify-between font-mono text-[10px] text-muted-foreground">
          <span>distribution @ gen {generations[histIndex]?.generation ?? "—"}</span>
          <span>{hist ? `${hist.values.length} 个体` : "未记录逐个体 fitness"}</span>
        </div>
        {hist && hist.values.length > 0 && (
          <MetricChart
            height={HIST_HEIGHT}
            ariaLabel={`fitness histogram at generation ${hist.generation}`}
            draw={(ctx: CanvasRenderingContext2D, w: number, h: number) =>
              drawHistogram(ctx, w, h, hist.values)
            }
          />
        )}
        {generations.length > 1 && (
          <input
            type="range"
            min={0}
            max={generations.length - 1}
            value={histIndex}
            onChange={(e) => setHistGeneration(generations[Number(e.target.value)]?.generation ?? null)}
            aria-label="histogram generation"
            className="mt-1 w-full"
          />
        )}
      </section>

      {/* 形态与 tau */}
      <section className="border border-border p-2">
        <div className="mb-1 flex items-center justify-between font-mono text-[10px]">
          <SectionLabel en="MORPHOLOGY" zh="形态" />
          <span className="text-muted-foreground">
            neurons {fmt(last.mean_neuron, 1)} · edges {fmt(last.mean_edge, 1)} · tau {fmt(last.mean_tau, 2)}
          </span>
        </div>
        <MetricChart
          height={LINE_HEIGHT}
          ariaLabel="mean neurons and edges over generations"
          draw={(ctx: CanvasRenderingContext2D, w: number, h: number) => {
            const ok = drawLineChart(ctx, w, h, morphSeries);
            if (ok) drawEventMarkers(ctx, w, h, generations.length, markedIndices);
          }}
        />
        <MetricChart
          height={LINE_HEIGHT}
          ariaLabel="mean tau over generations"
          draw={(ctx: CanvasRenderingContext2D, w: number, h: number) => {
            const ok = drawLineChart(ctx, w, h, tauSeries);
            if (ok) drawEventMarkers(ctx, w, h, generations.length, markedIndices);
          }}
        />
        {typeof last.mean_neuron !== "number" && (
          <p className="font-mono text-[10px] text-muted-foreground">
            该 run 未记录神经元数 / 连接数 / τ 均值（早期版本），形态与 τ 曲线为空。
          </p>
        )}
      </section>

      {/* viability rate */}
      <section className="border border-border p-2">
        <div className="mb-1 flex items-center justify-between">
          <SectionLabel en="VIABILITY" zh="可育性" />
          <span className="font-mono text-[10px] text-muted-foreground">
            {typeof last.n_viable === "number" && typeof last.n_individuals === "number" && last.n_individuals > 0
              ? `${((last.n_viable / last.n_individuals) * 100).toFixed(0)}%`
              : "—"}
          </span>
        </div>
        <MetricChart
          height={LINE_HEIGHT}
          ariaLabel="viability rate over generations"
          draw={(ctx: CanvasRenderingContext2D, w: number, h: number) => {
            const ok = drawLineChart(ctx, w, h, viabilitySeries, 0);
            if (ok) drawEventMarkers(ctx, w, h, generations.length, markedIndices);
          }}
        />
      </section>
    </div>
  );
}
