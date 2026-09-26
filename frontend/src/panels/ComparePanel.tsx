import { useCallback, useEffect, useState } from "react";
import { Scale } from "lucide-react";
import { Panel } from "@/components/Panel";
import { MetricChart } from "@/visuals/MetricChart";
import { drawBars } from "@/visuals/chartPrimitives";
import { BRAND } from "@/design/palette";
import { getComparison, listComparisons } from "@/api/comparisons";
import type { ComparisonTable, ComparisonTableSummary } from "@/api/types";

/**
 * COMPARE 段（`交互与可视化.md` §1）：承载赛题「原模型 → 改后模型 → 结果对比」。
 *
 * 数据来自 `results/tables/*.json`（只读，`API接口.md` §2.5）。**缺失显示「未记录」，不补 0**
 * （老 producer 的表可能缺字段；`null` 只表示该臂未跑）。
 */

/** 一个对照臂（`kind="ablation"`；字段可能缺，故全可选）。 */
interface AblationArm {
  arm?: string;
  kind?: string;
  note?: string;
  metrics?: Record<string, { mean?: number | null } | null> | null;
  complexity?: Record<string, number> | null;
}

/** 列定义：读值路径 + 显示口径。 */
const COLUMNS: Array<{ label: string; get: (a: AblationArm) => number | null | undefined; digits: number }> = [
  { label: "fit", get: (a) => a.metrics?.composite_fitness?.mean, digits: 3 },
  { label: "capture", get: (a) => a.metrics?.capture_rate?.mean, digits: 3 },
  { label: "survival", get: (a) => a.metrics?.survival?.mean, digits: 3 },
  { label: "params", get: (a) => a.complexity?.parameter_count, digits: 0 },
  { label: "edges", get: (a) => a.complexity?.active_edges, digits: 0 },
  { label: "FLOPs", get: (a) => a.complexity?.flops_implemented, digits: 0 },
  { label: "p50ms", get: (a) => a.complexity?.latency_p50_ms, digits: 3 },
];

function fmt(value: number | null | undefined, digits: number): string {
  return typeof value === "number" ? value.toFixed(digits) : "未记录";
}

export function ComparePanel() {
  const [tables, setTables] = useState<ComparisonTableSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [table, setTable] = useState<ComparisonTable | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (id: string) => {
    setError(null);
    try {
      setTable(await getComparison(id));
    } catch (e) {
      setError(String(e));
      setTable(null);
    }
  }, []);

  useEffect(() => {
    let stop = false;
    listComparisons()
      .then((items) => {
        if (stop) return;
        setTables(items);
        const preferred =
          items.find((t) => t.kind === "ablation")?.id ?? items[0]?.id ?? null;
        setSelected(preferred);
        if (preferred) void load(preferred);
      })
      .catch((e) => {
        if (!stop) setError(String(e));
      });
    return () => {
      stop = true;
    };
  }, [load]);

  const arms = Array.isArray(table?.payload.arms)
    ? (table?.payload.arms as AblationArm[])
    : null;

  return (
    <Panel title="Compare" icon={<Scale className="size-4 text-primary" />}>
      <div className="flex h-full min-h-0 flex-col gap-2">
        <p className="shrink-0 text-xs text-muted-foreground">
          原模型 → 改后模型 → 结果对比。缺失项显示「未记录」，不以 0 代替。
        </p>

        {/* 表选择 */}
        <div className="flex shrink-0 flex-wrap gap-1">
          {tables.length === 0 && (
            <span className="font-mono text-[10px] text-muted-foreground">
              暂无对比数据。
            </span>
          )}
          {tables.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => {
                setSelected(t.id);
                void load(t.id);
              }}
              className={`border border-border px-2 py-0.5 font-mono text-[10px] leading-none ${
                t.id === selected ? "bg-brand-fish-navy text-brand-bone" : ""
              }`}
            >
              {t.id}
            </button>
          ))}
        </div>

        {error && <p className="font-mono text-[10px] text-brand-danger-red">{error}</p>}

        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
          {arms && arms.length > 0 && (
            <>
              <div className="border border-border p-2">
                <div className="mb-1 flex items-center justify-between">
                  <span className="font-pixel text-[10px] leading-none">ARMS</span>
                  <span className="font-mono text-[10px] text-muted-foreground">
                    {table?.payload.experiment_id as string} · {arms.length} arms
                  </span>
                </div>
                <table className="w-full font-mono text-[10px]">
                  <thead>
                    <tr className="text-muted-foreground">
                      <th className="text-left font-normal">arm</th>
                      {COLUMNS.map((c) => (
                        <th key={c.label} className="text-right font-normal">
                          {c.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {arms.map((arm, index) => (
                      <tr key={`${arm.arm ?? index}`}>
                        <td className="truncate" title={arm.note ?? undefined}>
                          {arm.arm ?? `arm${index}`}
                        </td>
                        {COLUMNS.map((c) => (
                          <td key={c.label} className="text-right">
                            {fmt(c.get(arm), c.digits)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* 主指标柱状：composite_fitness（缺失的臂不画） */}
              <div className="border border-border p-2">
                <div className="mb-1 font-pixel text-[10px] leading-none">
                  COMPOSITE FITNESS
                </div>
                <MetricChart
                  height={90}
                  ariaLabel="composite fitness by arm"
                  draw={(ctx, w, h) =>
                    void drawBars(
                      ctx,
                      w,
                      h,
                      arms.map((a) => a.metrics?.composite_fitness?.mean ?? null),
                      BRAND.shallowWater,
                    )
                  }
                />
                <div className="mt-1 flex flex-wrap gap-x-2 font-mono text-[10px] text-muted-foreground">
                  {arms.map((a, i) => (
                    <span key={`${a.arm ?? i}`}>
                      {i}: {a.arm ?? `arm${i}`}
                    </span>
                  ))}
                </div>
              </div>
            </>
          )}

          {table && (!arms || arms.length === 0) && (
            <div className="border border-border p-2 font-mono text-[10px] text-muted-foreground">
              <div className="mb-1 font-pixel text-[10px] leading-none text-foreground">
                {table.kind.toUpperCase()}
              </div>
              该表暂未作图。可用字段：
              <ul className="mt-1">
                {Object.keys(table.payload).map((k) => (
                  <li key={k}>· {k}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </Panel>
  );
}
