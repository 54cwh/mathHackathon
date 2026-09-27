import { SectionLabel } from "@/components/SectionLabel";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useUiStore } from "@/store/ui";
import { Dna } from "lucide-react";
import { Panel } from "@/components/Panel";
import { DnaHelixVisual } from "@/visuals/DnaHelixVisual";
import { NucleotideStrip } from "@/visuals/NucleotideStrip";
import { createGenome, develop, getGenome, mutateGenome } from "@/api/lab";
import type { Base, DevelopmentResult, GenomeRecord, MutationDiff, MutationResult } from "@/api/types";
import { DevCompare } from "@/panels/DevCompare";

import { spawnIndividual } from "@/api/arena";
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
/** 每条单倍体一次显示的碱基数（4 行 × 1 行高，面板放得下；选中位点居中开窗）。 */
const STRIP_WINDOW = 20;

const BASES: Base[] = ["A", "C", "G", "T"];

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
  const sessionId = useUiStore((s) => s.sessionId);
  /** 单一真相：已入 Arena 的实验室个体（store 持有；本面板只读，`通用层接口.md` §7）。 */
  const individuals = useUiStore((s) => s.individuals);
  const addIndividual = useUiStore((s) => s.addIndividual);
  const publishDevelopment = useUiStore((s) => s.publishDevelopment);
  const intent = useUiStore((s) => s.intent);
  /** 已请求过 spawn 的 genome（UI 本地簿记：防重复请求；不属领域状态）。 */
  const requestedRef = useRef<Set<string>>(new Set());

  /**
   * 4 条**同源**单倍体（pair0.mat / pair0.pat / pair1.mat / pair1.pat），顺序即 `position ∈ [0,512)`
   * 的线性坐标（`API接口.md` §2.3 已定稿）。
   *
   * ⚠️ **不是碱基配对**：本模型的两条同源链是各自独立抽取的随机序列（实测互补性 0、
   * 相同率 22.7% ≈ 随机），不存在 Watson–Crick 配对关系。旧版把 512 碱基**折行**显示，
   * 上下相邻看着像配对 —— 这是误导，已改为按单倍体分行并标注。
   */
  const haplotypes = useMemo(() => {
    if (!genome) return [] as Array<{ label: string; seq: string; start: number }>;
    const order: Array<[number, "maternal" | "paternal"]> = [
      [0, "maternal"],
      [0, "paternal"],
      [1, "maternal"],
      [1, "paternal"],
    ];
    let start = 0;
    return order.map(([pairIndex, key]) => {
      const seq = genome.chromosome_pairs[pairIndex]?.[key] ?? "";
      const row = {
        label: `P${pairIndex} ${key === "maternal" ? "MAT" : "PAT"}`,
        seq,
        start,
      };
      start += seq.length;
      return row;
    });
  }, [genome]);

  /** 当前选中位点落在哪条单倍体上（螺旋只画这一条，避免把 4 条混在一起）。 */
  const activeRow = useMemo(
    () => haplotypes.find((row) => position >= row.start && position < row.start + row.seq.length),
    [haplotypes, position],
  );
  const sequence = activeRow?.seq ?? haplotypes[0]?.seq ?? "";

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
      publishDevelopment(fresh.genome_id, null); // 新基因组尚未发育
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }, [publishDevelopment]);

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

  /** 待送入 Arena 的 genome（会话尚未建立时先排队，会话就绪后自动补送）。 */
  const [pendingSpawn, setPendingSpawn] = useState<string[]>([]);

  /** 把某 genome 送进 Arena（幂等：同 genome 只送一次；无会话则排队）。 */
  const sendToArena = useCallback(
    async (genomeId: string) => {
      // 已在会话内（初始种群 / 早先追加）→ 无需再送，避免 409 噪声。
      if (individuals.some((it) => it.genome_id === genomeId)) return;
      if (!sessionId) {
        setPendingSpawn((current) =>
          current.includes(genomeId) ? current : [...current, genomeId],
        );
        return;
      }
      if (requestedRef.current.has(genomeId)) return;
      requestedRef.current.add(genomeId);
      try {
        const individual = await spawnIndividual(sessionId, genomeId);
        addIndividual(individual); // → store.individuals（去重/门控用）
      } catch (e) {
        requestedRef.current.delete(genomeId); // 失败允许重试
        // 已存在（409）/ 非 viable（422）等：不打断开发流程，只在提示区显示
        setError(String(e));
      }
    },
    [sessionId, addIndividual, individuals],
  );

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
        const result = await develop({ genome_id: genomeId, seed: DEV_SEED }, true);
        setBaseline(result);
        setDevelopment(result);
        publishDevelopment(genomeId, result, result.trace ?? null);
        void sendToArena(genomeId);
      } catch (e) {
        setError(String(e));
      } finally {
        setBusy(false);
      }
    },
    [sendToArena, publishDevelopment],
  );

  // 会话就绪后补送排队中的个体（例如先点了 DEVELOP、Arena 会话还在建）
  useEffect(() => {
    if (!sessionId || pendingSpawn.length === 0) return;
    for (const genomeId of pendingSpawn) void sendToArena(genomeId);
    setPendingSpawn([]);
  }, [sessionId, pendingSpawn, sendToArena]);

  // 点 Arena 里的实验室鱼 / chip → 把它的基因组载入本面板（§15.6 三栏联动）。
  // store 的 `focusNonce` 自增即一次焦点事件；用 ref 防止挂载时误触发与重复处理。
  const focusNonce = useUiStore((s) => s.focusNonce);
  const activeGenomeId = useUiStore((s) => s.activeGenomeId);
  const handledFocus = useRef(0);
  useEffect(() => {
    if (focusNonce === 0 || focusNonce === handledFocus.current) return;
    handledFocus.current = focusNonce;
    if (activeGenomeId) void adoptGenome(activeGenomeId);
  }, [focusNonce, activeGenomeId, adoptGenome]);

  async function handleDevelop() {
    if (!genome) return;
    setBusy(true);
    setError(null);
    try {
      const result = await develop({ genome_id: genome.genome_id, seed: DEV_SEED }, true);
      // 首次 DEVELOP = 基线；之后每次都是「改后」，与基线对比（§5）。
      setBaseline((current) => current ?? result);
      setDevelopment(result);
      // → Brain Forge 的 §4 分阶段动画（真实过程，见 API接口.md §2.3）
      publishDevelopment(genome.genome_id, result, result.trace ?? null);
      void sendToArena(genome.genome_id); // → Arena 追加该个体（§1.11）
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  // 导演线意图（`交互与可视化.md` §1）：`GENOME` 段造基因组、`DEVELOP` 段发育。
  // 用 ref 去重（同 `focusNonce` 口径）；`developRef` 持有最新 `handleDevelop`，避免每渲染换引用。
  const developRef = useRef(handleDevelop);
  developRef.current = handleDevelop;
  const handledIntent = useRef(0);
  useEffect(() => {
    if (!intent || intent.nonce === handledIntent.current) return;
    handledIntent.current = intent.nonce;
    if (intent.stage === "genome") {
      if (!genome) void loadFresh();
    } else if (intent.stage === "develop") {
      developRef.current();
    }
  }, [intent, genome, loadFresh]);

  /** 每条单倍体各自开窗，窗口以选中位点为中心（保证选中格可见；无 offset 参数故由本面板切片）。 */
  const rowWindow = (row: { seq: string; start: number }) => {
    const start = Math.max(
      0,
      Math.min(
        position - row.start - Math.floor(STRIP_WINDOW / 2),
        Math.max(0, row.seq.length - STRIP_WINDOW),
      ),
    );
    const index = position - row.start - start;
    return {
      start,
      text: row.seq.slice(start, start + STRIP_WINDOW),
      selected: index >= 0 && index < STRIP_WINDOW ? index : undefined,
    };
  };

  return (
    <Panel title="DNA2Brain Lab" titleZh="基因 → 大脑" icon={<Dna className="size-4 text-primary" />}>
      <div className="flex h-full min-h-0 flex-col gap-2">
        {/* min-h-40 + flex-[3]：面板矮时视觉区不被下方内容挤成 0 高（实测过 0 高黑块）。 */}
        <div className="min-h-32 flex-[3] overflow-hidden">
          <div className="flex items-baseline justify-between">
            <span className="font-pixel text-[11px] leading-none text-muted-foreground">
              HELIX (SCHEMATIC)
            </span>
            <span className="whitespace-nowrap font-mono text-[11px] text-muted-foreground">
              显示 {activeRow?.label ?? "—"} · 非互补配对
            </span>
          </div>
          <DnaHelixVisual
            sequence={sequence}
            highlightPosition={activeRow ? position - activeRow.start : position}
          />
        </div>

        {/* 下方内容（条带 + 编辑器 + 表型 + 提示）独立成可滚区，矮面板下不裁剪。 */}
        <div className="flex min-h-0 flex-[2] flex-col gap-2 overflow-y-auto pr-1">

        {/* 4 条同源单倍体（§2 的 chromosome pair / maternal / paternal / locus 四项）：可点选。 */}
        <div className="min-h-0 shrink-0 space-y-0.5">
          {haplotypes.map((row) => {
            const view = rowWindow(row);
            return (
              <div key={row.label} className="flex items-center gap-1">
                <span className="w-[52px] shrink-0 font-pixel text-[11px] leading-none text-muted-foreground">
                  {row.label}
                </span>
                <div className="min-w-0 flex-1">
                  <NucleotideStrip
                    sequence={view.text}
                    selectedPosition={view.selected}
                    onSelectPosition={(i) => setPosition(row.start + view.start + i)}
                    maxBases={STRIP_WINDOW}
                  />
                </div>
              </div>
            );
          })}
          <p className="font-mono text-[11px] leading-tight text-muted-foreground">
            四条单倍体：P0/P1 × 母源 MAT / 父源 PAT，共 512 个位点。
            <span className="text-brand-amber"> 同源位点之间不是碱基配对</span>
            （每条链各自独立随机，不存在 A–T / C–G 互补）。
          </p>
        </div>

        {/* 编辑器：genome_id / 位置 / 碱基 / 两个动作 */}
        <div className="shrink-0 space-y-2 border border-border p-2">
          <div className="flex items-center justify-between gap-2">
            <SectionLabel en="GENOME" zh="基因组" />
            <span className="truncate font-mono text-xs text-muted-foreground">
              {genome ? shortId(genome.genome_id) : busy ? "…" : "—"}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <label className="font-pixel text-[11px] leading-none" htmlFor="dna-position">
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
            <label className="font-pixel text-[11px] leading-none" htmlFor="dna-base">
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
            <span className="whitespace-nowrap font-mono text-[11px] text-muted-foreground">/ {MAX_POSITION}</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void handleMutate()}
              disabled={busy || !genome}
              className="flex flex-col items-center border border-border px-2 py-1 leading-none disabled:cursor-not-allowed disabled:text-muted-foreground"
            >
              <span className="font-pixel text-[11px]">MUTATE</span>
              <span className="text-[11px] text-muted-foreground">突变</span>
            </button>
            <button
              type="button"
              onClick={() => void handleDevelop()}
              disabled={busy || !genome}
              className="flex flex-col items-center border border-border px-2 py-1 leading-none disabled:cursor-not-allowed disabled:text-muted-foreground"
            >
              <span className="font-pixel text-[11px]">DEVELOP</span>
              <span className="text-[11px] text-muted-foreground">发育</span>
            </button>
            <button
              type="button"
              onClick={() => void loadFresh()}
              disabled={busy}
              className="flex flex-col items-center border border-border px-2 py-1 leading-none disabled:cursor-not-allowed disabled:text-muted-foreground"
            >
              <span className="font-pixel text-[11px]">NEW</span>
              <span className="text-[11px] text-muted-foreground">新基因组</span>
            </button>
          </div>

          {mutation && (
            <div className="font-mono text-[11px] leading-relaxed text-muted-foreground">
              pos {mutation.diff.position}: {mutation.diff.from_base} → {mutation.diff.to_base} · new{" "}
              {shortId(mutation.new_genome_id)}
            </div>
          )}
        </div>

        {/* 发育结果：真实数值（DOM 渲染，§15.1 A2 允许且应当显示真实 simulation state） */}
        <div className="shrink-0 border border-border p-2">
          <div className="mb-1 flex items-center justify-between">
            <SectionLabel en="PHENOTYPE" zh="表型" />
            <span className="whitespace-nowrap font-mono text-[11px] text-muted-foreground">
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
                <dt className="text-[11px] text-muted-foreground">{String(label)}</dt>
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
              <SectionLabel en="BEFORE / AFTER" zh="改前 / 改后" />
              <button
                type="button"
                onClick={() => {
                  setBaseline(development);
                  setMutations([]);
                }}
                disabled={!development}
                className="border border-border px-2 py-0.5 font-pixel text-[11px] leading-none disabled:cursor-not-allowed disabled:text-muted-foreground"
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
