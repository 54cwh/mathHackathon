import { SectionLabel } from "@/components/SectionLabel";
import { useState } from "react";
import { Dna } from "lucide-react";
import { breed } from "@/api/lab";
import type { BreedingResult, GenomeRecord } from "@/api/types";

/**
 * Mendel / 育种（`交互与可视化.md` Phase D 的 Mendel Mode；端点 `API接口.md` §2.3 `/v1/breedings`）。
 *
 * 流程：把当前基因组放进 A / B 两个槽 → `POST /v1/breedings` → 子代列表 → 点某子代**载入编辑器**
 * （`onAdopt` 回调由 DNA2Brain 面板提供：拉回 genome 记录 → 立即发育 → 设为新基线）。
 *
 * 只消费既有端点，无新增契约。`meiosis_trace` 里的 `mu` / `crossover_probability` 原样展示
 * （来自 `configs/evolution.yaml`，不是前端假定值）。
 */

export interface BreedingLabProps {
  current: GenomeRecord | null;
  onAdopt: (genomeId: string) => void;
}

function shortId(id: string): string {
  return id.length > 16 ? `${id.slice(0, 16)}…` : id;
}

export function BreedingLab({ current, onAdopt }: BreedingLabProps) {
  const [slotA, setSlotA] = useState<GenomeRecord | null>(null);
  const [slotB, setSlotB] = useState<GenomeRecord | null>(null);
  const [result, setResult] = useState<BreedingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleBreed() {
    if (!slotA || !slotB) return;
    setBusy(true);
    setError(null);
    try {
      setResult(
        await breed({ genome_a: slotA.genome_id, genome_b: slotB.genome_id, n_offspring: 2 }),
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="border border-border p-2">
      <div className="mb-1 flex items-center justify-between">
        <SectionLabel en="MENDEL / BREEDING" zh="孟德尔 / 育种" />
        <span className="font-mono text-[10px] text-muted-foreground">
          {slotA ? shortId(slotA.genome_id) : "A —"} × {slotB ? shortId(slotB.genome_id) : "B —"}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={!current}
          onClick={() => setSlotA(current)}
          className="border border-border px-2 py-1 font-pixel text-[10px] leading-none disabled:cursor-not-allowed disabled:text-muted-foreground"
        >
          SET A
        </button>
        <button
          type="button"
          disabled={!current}
          onClick={() => setSlotB(current)}
          className="border border-border px-2 py-1 font-pixel text-[10px] leading-none disabled:cursor-not-allowed disabled:text-muted-foreground"
        >
          SET B
        </button>
        <button
          type="button"
          disabled={!slotA || !slotB || busy}
          onClick={() => void handleBreed()}
          className="inline-flex items-center gap-1 border border-border px-2 py-1 font-pixel text-[10px] leading-none disabled:cursor-not-allowed disabled:text-muted-foreground"
        >
          <Dna className="size-3" />
          BREED
        </button>
        <button
          type="button"
          onClick={() => {
            setSlotA(current ?? null);
            setSlotB(null);
            setResult(null);
            setError(null);
          }}
          className="border border-border px-2 py-1 font-pixel text-[10px] leading-none"
        >
          SELF
        </button>
      </div>

      <p className="mt-1 font-mono text-[10px] text-muted-foreground">
        SET A/B 把当前基因组放进亲本槽；SELF = 同一个个体的自交（A=B=当前）。
      </p>

      {result && (
        <div className="mt-2 space-y-1">
          <div className="font-mono text-[10px] text-muted-foreground">
            mu {String(result.meiosis_trace.mu ?? "—")} · crossover{" "}
            {String(result.meiosis_trace.crossover_probability ?? "—")} · offspring{" "}
            {result.offspring.length}
          </div>
          <ul className="space-y-0.5">
            {result.offspring.map((childId) => (
              <li key={childId}>
                <button
                  type="button"
                  onClick={() => onAdopt(childId)}
                  className="w-full truncate border border-border px-2 py-0.5 text-left font-mono text-[10px]"
                  title={`载入 ${childId} 到编辑器并立即发育`}
                >
                  载入 {shortId(childId)}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && <p className="mt-1 font-mono text-[10px] text-brand-danger-red">⚠ {error}</p>}
    </section>
  );
}
