import { useEffect, useMemo, useRef, useState } from "react";
import { Brain } from "lucide-react";
import { Panel } from "@/components/Panel";
import { StatusPlaceholder } from "@/components/StatusPlaceholder";
import { BrainForgeVisual } from "@/visuals/BrainForgeVisual";
import { subscribe, type BrainActivationPayload } from "@/api/ws";
import { DevelopmentPipeline } from "@/panels/DevelopmentPipeline";
import { getLatestDevelopment, subscribeDevelopment } from "@/store/labBus";
import type { DevelopmentTraceSample } from "@/api/types";

/** 轨迹播放帧率（采样点少，慢放才看得清）。 */
const PIPELINE_FPS = 3;
import { useUiStore } from "@/store/ui";

/**
 * Brain Forge —— 订阅真实 `brain.activation`（`API接口.md` §3）。
 *
 * 触发口径：`brain.activation` 由 `release` 在**模型驱动会话**（`model_driven=true`
 * 且带 `checkpoint_path`）上推送（`api/session.py` release → `publish_brain_activation`）。
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
  // §4 发育时间线：游标/播放由本面板持有，同一游标同时驱动画布几何与曲线（必须同步）
  const [trace, setTrace] = useState<DevelopmentTraceSample[] | null>(
    () => getLatestDevelopment().trace,
  );
  const [genomeId, setGenomeId] = useState<string | null>(() => getLatestDevelopment().genomeId);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const cursorRef = useRef(0);
  const playingRef = useRef(false);

  useEffect(
    () =>
      subscribeDevelopment((payload) => {
        setTrace(payload.trace);
        setGenomeId(payload.genomeId);
        // 新轨迹到达即从第 0 帧开始播放
        cursorRef.current = 0;
        setCursor(0);
        playingRef.current = true;
        setPlaying(true);
      }),
    [],
  );

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
  const firstId = fishIds[0];
  const vector = activation && firstId ? activation.fish[firstId] : null;
  const stats = summarize(vector);

  return (
    <Panel title="Brain Forge" icon={<Brain className="size-4 text-primary" />}>
      <div className="flex h-full min-h-0 flex-col gap-2">
        {/* min-h-40：矮面板下视觉区不被读数块挤没（与 DNA 面板同因）。 */}
        <div className="min-h-32 flex-[2] overflow-hidden">
          <BrainForgeVisual
            activation={vector ?? undefined}
            geometry={
              currentSample?.positions
                ? {
                    stage: currentSample.stage,
                    positions: currentSample.positions,
                    cellType: currentSample.cell_type,
                  }
                : null
            }
          />
        </div>

        {/* §4 发育管线（真实逐阶段轨迹；数据来自 DNA 实验室的 with_trace 发育）。
            shrink-0 = 按内容高，避免与下方 ACTIVATION 之间出现空档。 */}
        <div className="min-h-0 shrink-0">
          <DevelopmentPipeline
            trace={trace}
            genomeId={genomeId}
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
                setCursor(0);
              }
              playingRef.current = !playingRef.current;
              setPlaying(playingRef.current);
            }}
          />
        </div>

        <div className="shrink-0 space-y-2 overflow-y-auto border border-border p-2">
          <div className="flex items-center justify-between">
            <span className="font-pixel text-[10px] leading-none">ACTIVATION</span>
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
              <div
                className="flex h-16 w-full items-end gap-px border border-border p-1"
                role="img"
                aria-label={`${firstId} activation`}
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
                {firstId} · {stats.samples.length}/{stats.n} 维
              </div>
            </>
          ) : (
            <StatusPlaceholder label="activation" />
          )}
        </div>

        <p className="shrink-0 text-xs text-muted-foreground">
          模型驱动会话（DanioNet + 冻结 checkpoint）经 release 推送激活；当前会话由 Arena 驱动。
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
