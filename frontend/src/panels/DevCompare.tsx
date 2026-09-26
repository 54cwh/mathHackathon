import { BRAND } from "@/design/palette";
import { MetricChart } from "@/visuals/MetricChart";
import { drawPairedBars } from "@/visuals/chartPrimitives";
import type { DevelopmentResult, MutationDiff } from "@/api/types";
import { DOMAIN_NAMES } from "@/visuals/activationReadouts";

/**
 * Before / After 对比（`交互与可视化.md` §5、§11 的 compare 环节）。
 *
 * 数据全部来自 `POST /v1/developments` 的前后两次结果 + 突变记录（`/v1/genomes/{id}/mutations`）。
 *
 * **端点未提供的项，这里明确标「未提供」，不编造**（§5 要求 7 项，其中 3 项当前不可得）：
 *   ✔ DNA difference（突变记录）/ motif affinity `q`（8 维，柱状对比）/ cell composition（六类 fate）/
 *     τ 分布（mean·std）/ 连接数量（`n_edges`，含 Δ）
 *   ✘ edge additions/removals：`dev_trace` **不含边集**，只能给数量差（差集需后端补字段）
 *   ✘ GRN 逐 step 表达：`dev_trace` 无逐 step 状态
 *   ✘ Arena behavior metrics：需把该个体送进 Arena 跑，当前无接口
 */


function cellCounts(result: DevelopmentResult | null): (number | null)[] {
  return DOMAIN_NAMES.map((_, index) => {
    const value = result?.dev_trace.cell_type_counts?.[String(index)];
    return typeof value === "number" ? value : null;
  });
}

function affinity(result: DevelopmentResult | null): (number | null)[] {
  const q = result?.dev_trace.q;
  if (!Array.isArray(q)) return [];
  return q.map((value) => (typeof value === "number" ? value : null));
}

function delta(before: number | undefined, after: number | undefined): string {
  if (typeof before !== "number" || typeof after !== "number") return "—";
  const diff = after - before;
  const sign = diff > 0 ? "+" : "";
  return `${sign}${diff.toFixed(4)}`;
}

function num(value: number | undefined, digits = 3): string {
  return typeof value === "number" ? value.toFixed(digits) : "—";
}

export interface DevCompareProps {
  before: DevelopmentResult | null;
  after: DevelopmentResult | null;
  /** 已应用的突变（按序）；用于 DNA difference。 */
  mutations: MutationDiff[];
}

export function DevCompare({ before, after, mutations }: DevCompareProps) {
  if (!before && !after) {
    return (
      <p className="text-xs text-muted-foreground">
        先点 DEVELOP 取基线，再 MUTATE 后点 DEVELOP，即可对比表型差异。
      </p>
    );
  }

  const rows: Array<[string, string, string, string]> = [
    ["n_neurons", num(before?.phenotype.n_neurons, 0), num(after?.phenotype.n_neurons, 0),
      delta(before?.phenotype.n_neurons, after?.phenotype.n_neurons)],
    ["n_edges", num(before?.phenotype.n_edges, 0), num(after?.phenotype.n_edges, 0),
      delta(before?.phenotype.n_edges, after?.phenotype.n_edges)],
    ["edge_density", num(before?.phenotype.edge_density), num(after?.phenotype.edge_density),
      delta(before?.phenotype.edge_density, after?.phenotype.edge_density)],
    ["tau_mean", num(before?.phenotype.tau_mean), num(after?.phenotype.tau_mean),
      delta(before?.phenotype.tau_mean, after?.phenotype.tau_mean)],
    ["tau_std", num(before?.phenotype.tau_std), num(after?.phenotype.tau_std),
      delta(before?.phenotype.tau_std, after?.phenotype.tau_std)],
    ["viable", before ? String(before.phenotype.viable) : "—", after ? String(after.phenotype.viable) : "—", "—"],
  ];

  return (
    <div className="space-y-2">
      {/* DNA difference：已应用的突变列表（真实坐标与碱基） */}
      <div className="border border-border p-2">
        <div className="mb-1 font-pixel text-[10px] leading-none">DNA DIFFERENCE</div>
        {mutations.length === 0 ? (
          <p className="font-mono text-[10px] text-muted-foreground">
            尚无突变（MUTATE 后在此累计）
          </p>
        ) : (
          <ul className="font-mono text-[10px]">
            {mutations.map((mutation, index) => (
              <li key={`${mutation.position}-${index}`}>
                #{index + 1} pos {mutation.position}: {mutation.from_base} → {mutation.to_base}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* motif affinity q：8 维成对柱（before 灰蓝 / after 琥珀） */}
      <div className="border border-border p-2">
        <div className="mb-1 flex items-center justify-between font-pixel text-[10px] leading-none">
          <span>MOTIF AFFINITY (q)</span>
          <span className="font-mono text-[9px] text-muted-foreground">q∈[0,1]，8 motif</span>
        </div>
        <MetricChart
          height={40}
          ariaLabel="motif affinity before and after"
          draw={(ctx: CanvasRenderingContext2D, w: number, h: number) => {
            drawPairedBars(ctx, w, h, affinity(before), affinity(after), BRAND.blueGrey, BRAND.amber);
          }}
        />
      </div>

      {/* cell composition：六类 fate 成对柱 + 表 */}
      <div className="border border-border p-2">
        <div className="mb-1 font-pixel text-[10px] leading-none">CELL COMPOSITION</div>
        <MetricChart
          height={40}
          ariaLabel="cell composition before and after"
          draw={(ctx: CanvasRenderingContext2D, w: number, h: number) => {
            drawPairedBars(ctx, w, h, cellCounts(before), cellCounts(after), BRAND.blueGrey, BRAND.amber);
          }}
        />
        <table className="mt-1 w-full font-mono text-[10px]">
          <thead>
            <tr className="text-muted-foreground">
              <th className="text-left font-normal">type</th>
              {DOMAIN_NAMES.map((name) => (
                <th key={name} className="text-right font-normal">
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="text-muted-foreground">before</td>
              {cellCounts(before).map((value, index) => (
                <td key={index} className="text-right">
                  {value ?? "—"}
                </td>
              ))}
            </tr>
            <tr>
              <td className="text-muted-foreground">after</td>
              {cellCounts(after).map((value, index) => (
                <td key={index} className="text-right">
                  {value ?? "—"}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      {/* 表型汇总表（含 Δ） */}
      <div className="border border-border p-2">
        <div className="mb-1 font-pixel text-[10px] leading-none">PHENOTYPE DELTA</div>
        <table className="w-full font-mono text-[10px]">
          <thead>
            <tr className="text-muted-foreground">
              <th className="text-left font-normal">metric</th>
              <th className="text-right font-normal">before</th>
              <th className="text-right font-normal">after</th>
              <th className="text-right font-normal">Δ</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([metric, beforeValue, afterValue, change]) => (
              <tr key={metric}>
                <td>{metric}</td>
                <td className="text-right">{beforeValue}</td>
                <td className="text-right">{afterValue}</td>
                <td className="text-right text-brand-amber">{change}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="border border-brand-danger-red p-2 font-mono text-[10px] text-brand-danger-red">
        ⚠ Δ 含**发育噪声**：两次发育的差异里混有随机发育成分 —— 即使碱基序列完全相同，不同个体也会
        得到略有差别的表型。故单碱基编辑的 Δ **不可直接读作突变效应**；要分离遗传效应，需多次抽样取均值。
      </p>

      <p className="font-mono text-[10px] text-muted-foreground">
        未展示：边的增删**差集**、GRN 逐步表达、Arena 行为指标。
      </p>
    </div>
  );
}
