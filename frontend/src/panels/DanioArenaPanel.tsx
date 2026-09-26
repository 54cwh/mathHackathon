import { useEffect, useRef, useState } from "react";
import { Fish } from "lucide-react";
import { Panel } from "@/components/Panel";
import { useUiStore } from "@/store/ui";
import { arenaAspect, CANVAS } from "@/design/geometry";
import { drawArenaScene, fishHitRadius, hitTestFish, type ArenaScene } from "@/visuals/ArenaScene";
import { clearFrames, pushFrame } from "@/visuals/replayBuffer";
import { subscribe } from "@/api/ws";
import {
  MASTER_SEED,
  createSession,
  deleteSession,
  getFishCard,
  getLeaderboard,
  getSnapshot,
  release,
  type ArenaSnapshot,
  type FishCard,
  type FishState,
  type Leaderboard,
} from "@/api/arena";

/**
 * Danio Arena。
 *
 * 数据来源（hybrid，理由见 `API接口.md` §3/§8）：
 *   - **鱼层**：`release` 每步推送 `arena.fish_state`（只含鱼）→ 走 WS，免去每 tick 的 snapshot 往返；
 *   - **场景层**（猎物/捕食者/障碍）：WS 不推送，故每 `SCENE_EVERY` 个 tick 取一次 REST snapshot；
 *   - **兜底**：WS 未连上时，鱼层回退到 snapshot 里的鱼（行为与改造前一致）。
 * 每个 tick 把合成后的场景写入回放缓冲（Playback 视图消费）。
 */

const POLL_MS = 100; // 10 fps render; backend sim runs at 20 Hz
/** 排行榜刷新节奏（每 20 tick ≈ 2s）。 */
const LEADERBOARD_EVERY = 20;
/** 场景层（猎物/捕食者/障碍）刷新节奏：每 5 tick ≈ 0.5s。 */
const SCENE_EVERY = 5;
/** 会话创建失败后的重试间隔（后端未起 / 端口上是旧进程时会走到这里）。 */
const SESSION_RETRY_MS = 3000;

/** 稳定 ID 可能很长；截断只影响显示，不影响 identity。 */
function shortId(id: string): string {
  return id.length > 12 ? `${id.slice(0, 12)}…` : id;
}

export function DanioArenaPanel() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const running = useUiStore((s) => s.running);
  const setRunning = useUiStore((s) => s.setRunning);
  const sessionId = useUiStore((s) => s.sessionId);
  const setSessionId = useUiStore((s) => s.setSessionId);
  const resetNonce = useUiStore((s) => s.resetNonce);
  const selectedFishId = useUiStore((s) => s.selectedFishId);
  const setSelectedFish = useUiStore((s) => s.setSelectedFish);
  const setStats = useUiStore((s) => s.setStats);
  const [scene, setScene] = useState<ArenaScene | null>(null);
  const [card, setCard] = useState<FishCard | null>(null);
  const [board, setBoard] = useState<Leaderboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const tickRef = useRef(0);
  /** WS 最新鱼层；undefined = WS 尚无帧（回退到 snapshot 的鱼）。 */
  const wsFishRef = useRef<Record<string, FishState> | null>(null);
  /** 低频场景层（猎物/捕食者/障碍 + step）。 */
  const sceneRef = useRef<ArenaScene | null>(null);

  // ---- session lifecycle: one live session per mount / reset ---------------
  //  失败要**自愈**：后端未起 / 端口上还是旧进程时，会话创建会失败；若只建一次，
  //  用户不动 Reset 就永远没有会话（Arena 空、Playback 无数据）。故失败后按
  //  `SESSION_RETRY_MS` 重试，直到成功或组件卸载（/ Reset）。
  useEffect(() => {
    let cancelled = false;
    let created: string | null = null;
    let timer = 0;

    const attempt = () => {
      createSession(MASTER_SEED)
        .then((s) => {
          if (cancelled) {
            void deleteSession(s.session_id).catch(() => undefined);
            return;
          }
          created = s.session_id;
          setSessionId(s.session_id);
          setRunning(true);
          setError(null);
          setCard(null);
          setBoard(null);
          tickRef.current = 0;
          wsFishRef.current = null;
          sceneRef.current = null;
          clearFrames();
        })
        .catch((e) => {
          if (cancelled) return;
          setError(`${String(e)} · 重试中`);
          timer = window.setTimeout(attempt, SESSION_RETRY_MS);
        });
    };

    attempt();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      setSessionId(null);
      if (created) void deleteSession(created).catch(() => undefined);
    };
  }, [resetNonce, setSessionId, setRunning]);

  // ---- WS: 鱼层 + 事件 ----------------------------------------------------
  useEffect(() => {
    if (!sessionId) return;
    return subscribe(sessionId, {
      fishState: (payload) => {
        wsFishRef.current = payload.fish;
      },
    });
  }, [sessionId]);

  // ---- poll while running: one release step per tick ----------------------
  useEffect(() => {
    if (!running || !sessionId) return;
    let stop = false;
    let timer = 0;

    const tick = async () => {
      try {
        const summary = await release(sessionId, 1);
        tickRef.current += 1;

        // 场景层：低频刷新（WS 不推猎物/捕食者/障碍）
        if (tickRef.current === 1 || tickRef.current % SCENE_EVERY === 0) {
          const snap: ArenaSnapshot = await getSnapshot(sessionId);
          sceneRef.current = { ...snap };
        }
        if (stop) return;

        const base = sceneRef.current;
        if (base) {
          const composed: ArenaScene = {
            step: base.step,
            prey: base.prey,
            predators: base.predators,
            obstacles: base.obstacles,
            fish: wsFishRef.current ?? base.fish,
          };
          sceneRef.current = composed;
          setScene(composed);
          pushFrame(composed); // 回放缓冲（Playback 视图消费）
        }

        setStats({
          environment: summary.environment,
          generation: summary.generation,
          population: summary.population,
          fishAlive: summary.fish_alive,
          preyAlive: summary.prey_remaining,
          seed: summary.master_seed,
          step: base?.step ?? 0,
        });

        if (tickRef.current % LEADERBOARD_EVERY === 0) {
          setBoard(await getLeaderboard(sessionId));
        }
      } catch (e) {
        if (stop) return;
        setError(String(e));
        setRunning(false);
        return; // stop the loop; the user restarts with Release
      }
      if (!stop) timer = window.setTimeout(tick, POLL_MS);
    };

    timer = window.setTimeout(tick, POLL_MS);
    return () => {
      stop = true;
      window.clearTimeout(timer);
    };
  }, [running, sessionId, setRunning, setStats]);

  // ---- render -------------------------------------------------------------
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    if (!scene) {
      ctx.clearRect(0, 0, CANVAS.w, CANVAS.h);
      return;
    }
    drawArenaScene(ctx, scene, selectedFishId);
  }, [scene, selectedFishId]);

  // Session ids look like "session_ab12cd34ef56" -- show the hex, not the prefix.
  const shortSessionId = sessionId ? sessionId.replace(/^session_/, "").slice(0, 8) : null;

  function handleClick(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!scene) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const mx = ((e.clientX - rect.left) / rect.width) * CANVAS.w;
    const my = ((e.clientY - rect.top) / rect.height) * CANVAS.h;
    const hit = hitTestFish(scene, mx, my, fishHitRadius(rect.width));
    if (hit) {
      setSelectedFish(hit);
      void getFishCard(sessionId ?? "", hit)
        .then(setCard)
        .catch(() => setCard(null));
    } else {
      setSelectedFish(null);
      setCard(null);
    }
  }

  return (
    <Panel title="Danio Arena" icon={<Fish className="size-4 text-primary" />}>
      <div className="flex h-full min-h-0 flex-col gap-2">
        {/* Explicit 5:3 contract (rule 3); the bitmap ratio must equal it, or
            the click hit-test below drifts. */}
        <div className="w-full shrink-0" style={{ aspectRatio: arenaAspect() }}>
          <canvas
            ref={canvasRef}
            width={CANVAS.w}
            height={CANVAS.h}
            onClick={handleClick}
            // .pixelated：只管画布→屏幕的缩放（`imageSmoothingEnabled=false` 只管位图内部）。
            // 640 位图在窄列里被缩小显示，不加会被双线性插值糊掉（§15.4 #10）。
            className="pixelated h-full w-full cursor-crosshair"
          />
        </div>

        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
          {/* Fish Card（§1.5）：点选后的真实读数 */}
          <div className="border border-border p-2">
            <div className="mb-1 flex items-center justify-between">
              <span className="font-pixel text-[10px] leading-none">FISH CARD</span>
              <span className="font-mono text-[10px] text-muted-foreground">
                {card ? shortId(card.fish_id) : "—"}
              </span>
            </div>
            {card ? (
              <>
                <dl className="grid grid-cols-4 gap-x-2 font-mono text-xs">
                  {[
                    ["gen", String(card.generation)],
                    ["energy", card.energy.toFixed(3)],
                    ["size", card.size.toFixed(2)],
                    ["captures", String(card.metrics.captures)],
                    ["steps", String(card.metrics.survival_steps)],
                    ["encounters", String(card.metrics.encounters)],
                    ["escapes", String(card.metrics.escape_successes)],
                    ["viable", card.viable ? "yes" : "no"],
                  ].map(([label, value]) => (
                    <div key={label} className="flex flex-col">
                      <dt className="text-[10px] text-muted-foreground">{label}</dt>
                      <dd className="truncate">{value}</dd>
                    </div>
                  ))}
                </dl>
                <div className="mt-1 truncate font-mono text-[10px] text-muted-foreground">
                  genome {card.genome_id} · fitness {card.fitness === null ? "—" : card.fitness.toFixed(3)}
                </div>
              </>
            ) : (
              <p className="text-xs text-muted-foreground">点选画布上的鱼查看卡片。</p>
            )}
          </div>

          {/* 排行榜（§1.9）：按 (captures, survival_steps) 降序 */}
          <div className="border border-border p-2">
            <div className="mb-1 flex items-center justify-between">
              <span className="font-pixel text-[10px] leading-none">LEADERBOARD</span>
              <button
                type="button"
                onClick={() =>
                  sessionId &&
                  void getLeaderboard(sessionId)
                    .then(setBoard)
                    .catch((e) => setError(String(e)))
                }
                className="border border-border px-2 py-0.5 font-pixel text-[10px] leading-none"
              >
                REFRESH
              </button>
            </div>
            <table className="w-full font-mono text-[10px]">
              <thead>
                <tr className="text-muted-foreground">
                  <th className="text-left font-normal">#</th>
                  <th className="text-left font-normal">fish</th>
                  <th className="text-right font-normal">cap</th>
                  <th className="text-right font-normal">steps</th>
                </tr>
              </thead>
              <tbody>
                {(board?.entries ?? []).slice(0, 12).map((entry) => (
                  <tr key={entry.fish_id}>
                    <td>{entry.rank}</td>
                    <td className="truncate">{shortId(entry.fish_id)}</td>
                    <td className="text-right">{entry.captures}</td>
                    <td className="text-right">{entry.survival_steps}</td>
                  </tr>
                ))}
                {(board?.entries ?? []).length === 0 && (
                  <tr>
                    <td colSpan={4} className="text-muted-foreground">
                      尚无排名（释放若干步后出现）
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="flex shrink-0 items-center justify-between text-xs text-muted-foreground">
          <span>{shortSessionId ? `session ${shortSessionId}` : "connecting..."}</span>
          <span>{error ? `⚠ ${error}` : "click a fish to inspect"}</span>
        </div>
      </div>
    </Panel>
  );
}
