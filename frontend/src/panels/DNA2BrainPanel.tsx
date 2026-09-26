import { useCallback, useEffect, useMemo, useState } from "react";
import { Dna } from "lucide-react";
import { Panel } from "@/components/Panel";
import { DnaHelixVisual } from "@/visuals/DnaHelixVisual";
import { NucleotideStrip } from "@/visuals/NucleotideStrip";
import { createGenome, develop, getGenome, mutateGenome } from "@/api/lab";
import type { Base, DevelopmentResult, GenomeRecord, MutationDiff, MutationResult } from "@/api/types";
import { DevCompare } from "@/panels/DevCompare";
import { BreedingLab } from "@/panels/BreedingLab";

/**
 * DNA2Brain Lab —— 真编辑器（原模型 → 突变 → 发育 的界面证据链）。
 *
 * 数据全部来自后端（`api/API接口.md` §2.3 基因组实验室），**不造数据**：
 *   `POST /v1/genomes`            参考种子个体（`configs/demo_seed.yaml`）
 *   `POST /v1/genomes/{id}/mutations`  单点 Free Edit
 *   `POST /v1/developments`       RGCD 发育 → 真实 phenotype
 *
 * 坐标口径（`API接口.md` §2.3，已定稿）：`position ∈ [0, 512)` 线性覆盖二倍体，
 * 顺序 `pair0.maternal → pair0.paternal → pair1.maternal → pair1.paternal`。
 * 本文件的 `flatten()` 与该顺序**必须一致**，否则点选位置与后端突变位置会错位。
 */

/** `DevelopmentRequest.seed` 缺省值（`api/schemas.py`）；固定以复现。 */
const DEV_SEED = 0;
/** 二倍体碱基总长（`API接口.md` §2.3：`[0, 512)`）。 */
const MAX_POSITION = 512;
/** strip 一次显示的碱基数：以选中位置为中心开窗（组件本身按序切前 N 个，故由本面板开窗）。 */
const STRIP_WINDOW = 60;
/** 单染色体对的两个单倍体，拼接顺序见上文坐标口径。 */
const HAPLOID_ORDER = ["maternal", "paternal"] as const;

const BASES: Base[] = ["A", "C", "G", "T"];

function flatten(chromosomePairs: Record<string, string>[]): string {
  let out = "";
  for (const pair of chromosomePairs) {
    for (const haploid of HAPLOID_ORDER) out += pair[haploid] ?? "";
  }
  return out;
}

function shortId(id: string): string {
  return id.length > 14 ? `${id.slice(0, 14)}…` : id;
}

export function DNA2BrainPanel() {
  const [genome, setGenome] = useState<GenomeRecord | null>(null);
  const [position, setPosition] = useState(0);
  const [base, setBase] = useState<Base>("A");
  const [mutation, setMutation] = useState<MutationResult | null>(null);
  const [development, setDevelopment] = useState<DevelopmentResult | null>(null);
  /** 基线发育结果（§5 Before）：首次 DEVELOP 即设为基线，之后每次 DEVELOP 都是 After。 */
  const [baseline, setBaseline] = useState<DevelopmentResult | null>(null);
  /** 已应用突变（§5 DNA difference 的真实记录）。 */
  const [mutations, setMutations] = useState<MutationDiff[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sequence = useMemo(
    () => (genome ? flatten(genome.chromosome_pairs) : ""),
    [genome],
  );

  const loadFresh = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const fresh = await createGenome();
      setGenome(fresh);
      setMutation(null);
      setDevelopment(null);
      setBaseline(null);
      setMutations([]);
      setPosition(0);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void loadFresh();
  }, [loadFresh]);

  async function handleMutate() {
    if (!genome) return;
    setBusy(true);
    setError(null);
    try {
      const result = await mutateGenome(genome.genome_id, { position, base });
      setMutation(result);
      setMutations((current) => [...current, result.diff]);
      setDevelopment(null); // 序列已变，旧发育结果作废
      setGenome(await getGenome(result.new_genome_id));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  /** 把某个 genome 载入编辑器并**立即发育**（育种产出的子代走这条路）。 */
  const adoptGenome = useCallback(
    async (genomeId: string) => {
      setBusy(true);
      setError(null);
      try {
        const record = await getGenome(genomeId);
        setGenome(record);
        setMutation(null);
        setMutations([]);
        setPosition(0);
        const result = await develop({ genome_id: genomeId, seed: DEV_SEED });
        setBaseline(result);
        setDevelopment(result);
      } catch (e) {
        setError(String(e));
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  async function handleDevelop() {
    if (!genome) return;
    setBusy(true);
    setError(null);
    try {
      const result = await develop({ genome_id: genome.genome_id, seed: DEV_SEED });
      // 首次 DEVELOP = 基线；之后每次都是「改后」，与基线对比（§5）。
      setBaseline((current) => current ?? result);
      setDevelopment(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  // 以选中位置为中心开窗，保证选中格始终可见（组件按序取前 N 个，无 offset 参数）。
  const windowStart = Math.max(
    0,
    Math.min(position - Math.floor(STRIP_WINDOW / 2), Math.max(0, sequence.length - STRIP_WINDOW)),
  );
  const windowSequence = sequence.slice(windowStart, windowStart + STRIP_WINDOW);

  return (
    <Panel title="DNA2Brain Lab" icon={<Dna className="size-4 text-primary" />}>
      <div className="flex h-full min-h-0 flex-col gap-2">
        {/* min-h-40 + flex-[3]：面板矮时视觉区不被下方内容挤成 0 高（实测过 0 高黑块）。 */}
        <div className="min-h-40 flex-[3] overflow-hidden">
          <DnaHelixVisual sequence={sequence} highlightPosition={position} />
        </div>

        {/* 下方内容（条带 + 编辑器 + 表型 + 提示）独立成可滚区，矮面板下不裁剪。 */}
        <div className="flex min-h-0 flex-[2] flex-col gap-2 overflow-y-auto pr-1">

        {/* Nucleotide strip：真实序列；窗口内可点选（点选 index 需加回 windowStart）。 */}
        <div className="max-h-20 min-h-0 shrink-0 overflow-hidden">
          <NucleotideStrip
            sequence={windowSequence}
            selectedPosition={position - windowStart}
            onSelectPosition={(i) => setPosition(windowStart + i)}
          />
        </div>

        {/* 编辑器：genome_id / 位置 / 碱基 / 两个动作 */}
        <div className="shrink-0 space-y-2 border border-border p-2">
          <div className="flex items-center justify-between gap-2">
            <span className="font-pixel text-[10px] leading-none">GENOME</span>
            <span className="truncate font-mono text-xs text-muted-foreground">
              {genome ? shortId(genome.genome_id) : busy ? "…" : "—"}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <label className="font-pixel text-[10px] leading-none" htmlFor="dna-position">
              POS
            </label>
            <input
              id="dna-position"
              type="number"
              min={0}
              max={MAX_POSITION - 1}
              value={position}
              onChange={(e) => {
                const next = Number(e.target.value);
                if (Number.isFinite(next)) {
                  setPosition(Math.max(0, Math.min(MAX_POSITION - 1, Math.trunc(next))));
                }
              }}
              className="w-20 border border-border bg-transparent px-1 py-0.5 font-mono text-xs"
            />
            <label className="font-pixel text-[10px] leading-none" htmlFor="dna-base">
              BASE
            </label>
            <select
              id="dna-base"
              value={base}
              onChange={(e) => setBase(e.target.value as Base)}
              className="border border-border bg-transparent px-1 py-0.5 font-mono text-xs"
            >
              {BASES.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
            <span className="font-mono text-[10px] text-muted-foreground">/ {MAX_POSITION}</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void handleMutate()}
              disabled={busy || !genome}
              className="border border-border px-2 py-1 font-pixel text-[10px] leading-none disabled:cursor-not-allowed disabled:text-muted-foreground"
            >
              MUTATE
            </button>
            <button
              type="button"
              onClick={() => void handleDevelop()}
              disabled={busy || !genome}
              className="border border-border px-2 py-1 font-pixel text-[10px] leading-none disabled:cursor-not-allowed disabled:text-muted-foreground"
            >
              DEVELOP
            </button>
            <button
              type="button"
              onClick={() => void loadFresh()}
              disabled={busy}
              className="border border-border px-2 py-1 font-pixel text-[10px] leading-none disabled:cursor-not-allowed disabled:text-muted-foreground"
            >
              NEW
            </button>
          </div>

          {mutation && (
            <div className="font-mono text-[10px] leading-relaxed text-muted-foreground">
              pos {mutation.diff.position}: {mutation.diff.from_base} → {mutation.diff.to_base} · new{" "}
              {shortId(mutation.new_genome_id)}
            </div>
          )}
        </div>

        {/* 发育结果：真实数值（DOM 渲染，§15.1 A2 允许且应当显示真实 simulation state） */}
        <div className="shrink-0 border border-border p-2">
          <div className="mb-1 flex items-center justify-between">
            <span className="font-pixel text-[10px] leading-none">PHENOTYPE</span>
            <span className="font-mono text-[10px] text-muted-foreground">
              seed {DEV_SEED} · {development ? (development.phenotype.viable ? "viable" : "non-viable") : "—"}
            </span>
          </div>
          <dl className="grid grid-cols-4 gap-x-2 gap-y-1 font-mono text-xs">
            {[
              ["neurons", development?.phenotype.n_neurons],
              ["edges", development?.phenotype.n_edges],
              ["density", development?.phenotype.edge_density],
              ["tau", development?.phenotype.tau_mean],
            ].map(([label, value]) => (
              <div key={String(label)} className="flex flex-col">
                <dt className="text-[10px] text-muted-foreground">{String(label)}</dt>
                <dd className="truncate">
                  {typeof value === "number"
                    ? label === "density" || label === "tau"
                      ? value.toFixed(3)
                      : Math.round(value)
                    : "—"}
                </dd>
              </div>
            ))}
          </dl>
        </div>

          {/* §5 / §11 compare：基线 vs 改后 */}
          <section className="border border-border p-2">
            <div className="mb-1 flex items-center justify-between">
              <span className="font-pixel text-[10px] leading-none">BEFORE / AFTER</span>
              <button
                type="button"
                onClick={() => {
                  setBaseline(development);
                  setMutations([]);
                }}
                disabled={!development}
                className="border border-border px-2 py-0.5 font-pixel text-[10px] leading-none disabled:cursor-not-allowed disabled:text-muted-foreground"
              >
                SET BASELINE
              </button>
            </div>
            <DevCompare before={baseline} after={development} mutations={mutations} />
          </section>

          <BreedingLab current={genome} onAdopt={(id) => void adoptGenome(id)} />

          <p className="shrink-0 text-xs text-muted-foreground">
            {error ? `⚠ ${error}` : "点选碱基或用 POS 定位，MUTATE 单点突变后 DEVELOP 重算表型。"}
          </p>
        </div>
      </div>
    </Panel>
  );
}
