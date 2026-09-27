import { SectionLabel } from "@/components/SectionLabel";
import { useEffect, useMemo, useRef, useState } from "react";
import { Brain } from "lucide-react";
import { Panel } from "@/components/Panel";
import { StatusPlaceholder } from "@/components/StatusPlaceholder";
import { BrainForgeVisual } from "@/visuals/BrainForgeVisual";
import { subscribe, type BrainActivationPayload } from "@/api/ws";
import { DevelopmentPipeline } from "@/panels/DevelopmentPipeline";
import {
  READOUT_DOMAINS,
  activationReadouts,
} from "@/visuals/activationReadouts";


/** 轨迹播放帧率（采样点少，慢放才看得清）。 */
const PIPELINE_FPS = 3;
import { useUiStore } from "@/store/ui";

/**
 * Brain Forge —— 订阅真实 `brain.activation`（`API接口.md` §3）。
 *
 * 触发口径：`brain.activation` 由 `release` 推送——会话里每条鱼都有**它自己的网**（`api/§1.1`），
 * 故默认会话即有真实激活（`api/session.py` release → `publish_brain_activation`）。
 * 驱动者只有一处：Arena 的 release 轮询。本面板**只订阅、不驱动**，避免两处同时
 * 推进同一会话。会话为空或非模型驱动时，本面板恒停在「未初始化」态（§15.1 A2：
 * 未初始化走 placeholder，**不编造**数据）。
 *
 * 降频：推送与 release 同频（~10Hz），状态更新节流到 ~5Hz，避免 React 进 20Hz 热路径
 * （`frontend/README.md` 防坑 3）。
 */

const THROTTLE_MS = 200;
/** 激活条最多画多少根（仅取第一条鱼的向量；按步长抽稀）。 */
const MAX_BARS = 64;

export function BrainForgePanel() {
  const sessionId = useUiStore((s) => s.sessionId);
  const [activation, setActivation] = useState<BrainActivationPayload | null>(null);
  const lastRef = useRef(0);
  // §4 发育时间线：游标/播放由本面板持有，同一游标同时驱动画布几何与曲线（必须同步）。
  // 发育产物来自 store 单一真相（`通用层接口.md` §7）；本面板不自持副本。
  const development = useUiStore((s) => s.development);
  const trace = development?.trace ?? null;
  const genomeId = development?.genomeId ?? null;
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  /** 真实连接图层（用户 2026-09-27 裁决允许"可溯源真图"；默认开，可关）。 */
  const [showEdges, setShowEdges] = useState(true);
  /** `connectome` 阶段的两幕：`"p"` 概率场 / `"a"` 采样邻接（`交互与可视化.md` §4）。 */
  const [connFrame, setConnFrame] = useState<"p" | "a">("a");
  const cursorRef = useRef(0);
  const playingRef = useRef(false);

  // 新轨迹到达即从第 0 帧开始播放；`handledSeq` 记挂载时的序号，避免挂载即重放。
  const devSeq = development?.seq ?? 0;
  const handledSeq = useRef(devSeq);
  useEffect(() => {
    if (devSeq === handledSeq.current) return;
    handledSeq.current = devSeq;
    cursorRef.current = 0;
    setCursor(0);
    playingRef.current = true;
    setPlaying(true);
  }, [devSeq]);

  useEffect(() => {
    let raf = 0;
    let last = 0;
    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (!playingRef.current) return;
      if (now - last < 1000 / PIPELINE_FPS) return;
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

  const currentSample = useMemo(
    () => (trace && trace.length > 0 ? trace[Math.min(cursor, trace.length - 1)] : null),
    [trace, cursor],
  );

  useEffect(() => {
    setActivation(null);
    if (!sessionId) return;
    return subscribe(sessionId, {
      brainActivation: (payload) => {
        const now = Date.now();
        if (now - lastRef.current < THROTTLE_MS) return;
        lastRef.current = now;
        setActivation(payload);
      },
    });
  }, [sessionId]);

  const fishIds = activation ? Object.keys(activation.fish) : [];
  // §7：优先显示**选中的鱼**；无选中时退回该帧第一条并标注"任取一条"（不冒充选中）。
  const selectedFishId = useUiStore((s) => s.selectedFishId);
  const activeGenomeId = useUiStore((s) => s.activeGenomeId);
  // 优先「当前个体」（`activeGenomeId`，DEVELOP 后自然聚焦）→ 再「选中的鱼」→ 最后任取一条。
  const present = (id: string | null): id is string =>
    id !== null && activation !== null && id in activation.fish;
  const shownId = present(activeGenomeId)
    ? activeGenomeId
    : present(selectedFishId)
      ? selectedFishId
      : (fishIds[0] ?? null);
  const isFocal = shownId !== null && shownId === activeGenomeId;
  const vector = activation && shownId ? activation.fish[shownId] : null;
  const stats = summarize(vector);

  // §7 五类语义读数：按该鱼发育产物的逐神经元 cell_type/positions 对 h 分组（`DanioNet §5`）。
  const connSample = useMemo(() => {
    const trace = development?.trace;
    if (!trace) return null;
    for (let i = trace.length - 1; i >= 0; i--) {
      if (trace[i].stage === "connectome") return trace[i];
    }
    return null;
  }, [development]);
  // 配对前提：读数用**该鱼自己的** cell_type/positions。`connSample` 来自 Lab 的发育（= activeGenomeId），
  // 故只有"显示的鱼 == activeGenomeId"时才成立；否则不出读数（避免拿错个体的发育产物）。
  // 表达强度的**全局参考**（整条轨迹固定）：GRN 迭代的"逐渐点亮"才可见（按帧归一化会看不出来）。
  const exprScale = useMemo(() => {
    const samples = development?.trace;
    if (!samples) return null;
    let max = 0;
    for (const sample of samples) for (const value of sample.expr ?? []) max = Math.max(max, value);
    return max > 0 ? max : null;
  }, [development]);

  // 增殖阶段：标出本轮新生子代（前 `nParents` 个是父代；模型 §5 只有一轮分裂）。
  const nParents = useMemo(() => {
    const samples = development?.trace;
    if (!samples || !currentSample || currentSample.stage !== "proliferate") return null;
    const index = samples.indexOf(currentSample);
    return index > 0 ? samples[index - 1].n_neurons : null;
  }, [development, currentSample]);

  // 连接组阶段的两幕（p 概率场 / A 采样邻接）自动交替，避免只看到一幕、也避免与分化阶段"看起来一样"。
  useEffect(() => {
    if (currentSample?.stage !== "connectome") return;
    const timer = window.setInterval(() => setConnFrame((f) => (f === "p" ? "a" : "p")), 1200);
    return () => window.clearInterval(timer);
  }, [currentSample]);

  const readouts = useMemo(() => {
    if (!isFocal) return null;
    return activationReadouts(
      vector ?? [],
      connSample?.cell_type ?? null,
      connSample?.positions ?? null,
    );
  }, [isFocal, vector, connSample]);

  return (
    <Panel title="Brain Forge" titleZh="脑发育" icon={<Brain className="size-4 text-primary" />}>
      <div className="flex h-full min-h-0 flex-col gap-2">
        {/* min-h-40：矮面板下视觉区不被读数块挤没（与 DNA 面板同因）。 */}
        <div className="min-h-32 flex-[2] overflow-hidden">
          <BrainForgeVisual
            activation={vector ?? undefined}
            // 连接层只在「连接组成形」阶段出现 —— 否则它与「细胞分化」画面完全相同（阶段耦合）。
            showEdges={showEdges && currentSample?.stage === "connectome"}
            geometry={
              currentSample?.positions
                ? {
                    stage: currentSample.stage,
                    positions: currentSample.positions,
                    cellType: currentSample.cell_type,
                    edges: currentSample.edges,
                    expr: currentSample.expr,
                    exprScale,
                    nParents,
                    probs: currentSample.probs,
                    connFrame,
                  }
                : null
            }
          />
        </div>

        {/* §4 发育管线（真实逐阶段轨迹；数据来自 DNA 实验室的 with_trace 发育）。
            shrink-0 = 按内容高，避免与下方 ACTIVATION 之间出现空档。 */}
        <div className="min-h-0 shrink-0">
          <div className="flex items-center justify-between">
            <SectionLabel en="CONNECTOME LAYER" zh="连接组图层" />
            <span className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-muted-foreground">
                edges {currentSample?.edges ? currentSample.edges.length : "—"}
              </span>
              <button
                type="button"
                onClick={() => setShowEdges((v) => !v)}
                disabled={!currentSample?.edges}
                className={`border border-border px-2 py-0.5 font-pixel text-[10px] leading-none disabled:cursor-not-allowed disabled:text-muted-foreground ${
                  showEdges && currentSample?.edges ? "bg-brand-fish-navy text-brand-bone" : ""
                }`}
              >
                {showEdges ? "ON" : "OFF"}
              </button>
              {/* 两幕真值：p（概率场）→ A（采样邻接）。仅 connectome 样本可用。 */}
              <button
                type="button"
                onClick={() => setConnFrame((f) => (f === "p" ? "a" : "p"))}
                disabled={!currentSample?.probs}
                title="连接组两幕真值：p = 模型概率场 σ(ℓ)，A = 一次采样得到的邻接"
                className={`border border-border px-2 py-0.5 font-pixel text-[10px] leading-none disabled:cursor-not-allowed disabled:text-muted-foreground ${
                  currentSample?.probs && connFrame === "p" ? "bg-brand-fish-navy text-brand-bone" : ""
                }`}
              >
                {connFrame === "p" ? "P" : "A"}
              </button>
            </span>
          </div>

          <DevelopmentPipeline
            trace={trace}
            genomeId={genomeId}
            activationLive={vector !== null}
            q={development?.result?.dev_trace.q ?? null}
            cursor={cursor}
            playing={playing}
            onCursor={(index) => {
              playingRef.current = false;
              setPlaying(false);
              cursorRef.current = index;
              setCursor(index);
            }}
            onTogglePlay={() => {
              if (!playingRef.current && trace && cursorRef.current >= trace.length - 1) {
                cursorRef.current = 0;
      setConnFrame("p");
                setCursor(0);
              }
              playingRef.current = !playingRef.current;
              setPlaying(playingRef.current);
            }}
          />
        </div>

        <div className="shrink-0 space-y-2 overflow-y-auto border border-border p-2">
          <div className="flex items-center justify-between">
            <SectionLabel en="ACTIVATION" zh="神经活动" />
            <span className="font-mono text-[10px] text-muted-foreground">
              {activation ? `step ${activation.step} · fish ${fishIds.length}` : ""}
            </span>
          </div>

          {activation && vector && stats ? (
            <>
              <dl className="grid grid-cols-3 gap-x-2 font-mono text-xs">
                {[
                  ["neurons", stats.n],
                  ["mean", stats.mean],
                  ["peak", stats.peak],
                ].map(([label, value]) => (
                  <div key={String(label)} className="flex flex-col">
                    <dt className="text-[10px] text-muted-foreground">{String(label)}</dt>
                    <dd className="truncate">
                      {label === "neurons" ? String(value) : Number(value).toFixed(3)}
                    </dd>
                  </div>
                ))}
              </dl>
              {/* §7 五类语义读数（由 cell_type + positions 复算，缺失记「未定义」不补 0） */}
              {readouts && (
                <dl className="grid grid-cols-2 gap-x-2 font-mono text-[10px]">
                  {READOUT_DOMAINS.map((name) => {
                    const value = readouts.perDomain[name];
                    return (
                      <div key={name} className="flex justify-between gap-2">
                        <dt className="text-muted-foreground">{name}</dt>
                        <dd>{value === null ? "未定义" : value.toFixed(3)}</dd>
                      </div>
                    );
                  })}
                  <div className="flex justify-between gap-2">
                    <dt className="text-muted-foreground">motor L−R (ω)</dt>
                    <dd>{readouts.omegaDriver === null ? "未定义" : readouts.omegaDriver.toFixed(3)}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-muted-foreground">motor L·R</dt>
                    <dd>
                      {readouts.motorLeft === null || readouts.motorRight === null
                        ? "未定义"
                        : `${readouts.motorLeft.toFixed(2)}·${readouts.motorRight.toFixed(2)}`}
                    </dd>
                  </div>
                </dl>
              )}
              <div
                className="flex h-16 w-full items-end gap-px border border-border p-1"
                role="img"
                aria-label={`${shownId ?? "activation"} activation`}
              >
                {stats.samples.map((value, i) => (
                  <span
                    key={i}
                    className="min-w-px flex-1 bg-primary"
                    style={{ height: `${Math.max(2, Math.round(value * 100))}%` }}
                  />
                ))}
              </div>
              <div className="truncate font-mono text-[10px] text-muted-foreground">
                {shownId ?? "—"}
                {isFocal ? "（当前个体）" : "（任取一条）"} · {stats.samples.length}/{stats.n} 维
              </div>
            </>
          ) : (
            <StatusPlaceholder label="activation" />
          )}
        </div>

        <p className="shrink-0 text-xs text-muted-foreground">
          神经活动来自当前会话中该个体自己的 DanioNet，随 Arena 推进实时更新。
        </p>
      </div>
    </Panel>
  );
}

function summarize(vector: number[] | null) {
  if (!vector || vector.length === 0) return null;
  let sum = 0;
  let peak = Number.NEGATIVE_INFINITY;
  for (const v of vector) {
    sum += v;
    if (v > peak) peak = v;
  }
  const stride = Math.max(1, Math.ceil(vector.length / MAX_BARS));
  const samples: number[] = [];
  for (let i = 0; i < vector.length; i += stride) samples.push(clamp01(vector[i]));
  return { n: vector.length, mean: sum / vector.length, peak, samples };
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}
