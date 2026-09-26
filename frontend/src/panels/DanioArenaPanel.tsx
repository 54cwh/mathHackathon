import { useEffect, useRef, useState } from "react";
import { Fish } from "lucide-react";
import { Panel } from "@/components/Panel";
import { useUiStore } from "@/store/ui";
import { ARENA } from "@/design/palette";
import { CANVAS, arenaAspect, sr, sx, sy } from "@/design/geometry";
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
  type Leaderboard,
} from "@/api/arena";

/** 稳定 ID 可能很长（`fish_00` / `session_xxx`）；截断只影响显示，不影响 identity。 */
function shortId(id: string): string {
  return id.length > 12 ? `${id.slice(0, 12)}…` : id;
}

const POLL_MS = 100; // 10 fps render; backend sim runs at 20 Hz
/** 排行榜刷新节奏（每 20 个 tick ≈ 2s）：够新，又不给后端添堵。 */
const LEADERBOARD_EVERY = 20;

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
  const [snap, setSnap] = useState<ArenaSnapshot | null>(null);
  const [card, setCard] = useState<FishCard | null>(null);
  const [board, setBoard] = useState<Leaderboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const tickRef = useRef(0);

  // ---- session lifecycle: one live session per mount / reset ---------------
  //  The store holds exactly one session at a time. A reset therefore releases
  //  the previous session and tears the store's id down first, so the poll loop
  //  can never fire against an already-deleted session.
  useEffect(() => {
    let cancelled = false;
    let created: string | null = null;
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
      })
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
      setSessionId(null);
      if (created) void deleteSession(created).catch(() => undefined);
    };
  }, [resetNonce, setSessionId, setRunning]);

  // ---- poll while running: one release step + one snapshot per tick ---------
  //  Self-scheduling rather than setInterval, so a slow backend delays the next
  //  tick instead of stacking overlapping requests.
  useEffect(() => {
    if (!running || !sessionId) return;
    let stop = false;
    let timer = 0;

    const tick = async () => {
      try {
        const summary = await release(sessionId, 1);
        const s = await getSnapshot(sessionId);
        if (stop) return;
        setSnap(s);
        setStats({
          environment: summary.environment,
          generation: summary.generation,
          population: summary.population,
          fishAlive: summary.fish_alive,
          preyAlive: summary.prey_remaining,
          seed: summary.master_seed,
          step: s.step,
        });
        tickRef.current += 1;
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
    ctx.imageSmoothingEnabled = false; // hard pixel edges (rule 9(b))
    ctx.clearRect(0, 0, CANVAS.w, CANVAS.h);
    ctx.fillStyle = ARENA.canvas;
    ctx.fillRect(0, 0, CANVAS.w, CANVAS.h);

    if (!snap) return;

    for (const o of snap.obstacles) {
      ctx.beginPath();
      ctx.arc(sx(o.x), sy(o.y), sr(o.radius), 0, Math.PI * 2);
      ctx.fillStyle = ARENA.obstacleDark;
      ctx.fill();
      ctx.strokeStyle = ARENA.obstacleLight;
      ctx.stroke();
    }

    for (const p of Object.values(snap.prey)) {
      if (!p.alive) continue;
      ctx.beginPath();
      ctx.arc(sx(p.x), sy(p.y), Math.max(2, sr(p.size) * 1.5), 0, Math.PI * 2);
      ctx.fillStyle = ARENA.prey;
      ctx.fill();
    }

    for (const d of Object.values(snap.predators)) {
      ctx.beginPath();
      ctx.arc(sx(d.x), sy(d.y), sr(d.size) * 3, 0, Math.PI * 2);
      ctx.fillStyle = ARENA.predator;
      ctx.fill();
      ctx.strokeStyle = ARENA.outline;
      ctx.stroke();
    }

    for (const [fid, f] of Object.entries(snap.fish)) {
      if (!f.alive) continue;
      const x = sx(f.x);
      const y = sy(f.y);
      const len = Math.max(8, sr(f.size) * 10);
      const headX = x + Math.cos(f.heading) * len;
      const headY = y + Math.sin(f.heading) * len;
      const leftX = x + Math.cos(f.heading + 2.6) * (len * 0.6);
      const leftY = y + Math.sin(f.heading + 2.6) * (len * 0.6);
      const rightX = x + Math.cos(f.heading - 2.6) * (len * 0.6);
      const rightY = y + Math.sin(f.heading - 2.6) * (len * 0.6);
      const isSelected = fid === selectedFishId;
      ctx.beginPath();
      ctx.moveTo(headX, headY);
      ctx.lineTo(leftX, leftY);
      ctx.lineTo(rightX, rightY);
      ctx.closePath();
      ctx.fillStyle = isSelected ? ARENA.fishSelected : ARENA.fishUnselected;
      ctx.fill();
      ctx.strokeStyle = ARENA.outline; // 统一轮廓（像素画惯例；见 design/palette.ts 的 ARENA 说明）
      ctx.lineWidth = isSelected ? 2 : 1;
      ctx.stroke();

      if (isSelected) {
        ctx.beginPath();
        ctx.arc(x, y, len + 4, -Math.PI / 2, -Math.PI / 2 + f.energy * Math.PI * 2);
        ctx.strokeStyle = f.energy > 0.3 ? ARENA.energyOk : ARENA.energyLow;
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }
  }, [snap, selectedFishId]);

  // Session ids look like "session_ab12cd34ef56" -- show the hex, not the prefix.
  const shortSessionId = sessionId ? sessionId.replace(/^session_/, "").slice(0, 8) : null;

  function handleClick(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!snap) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const mx = ((e.clientX - rect.left) / rect.width) * CANVAS.w;
    const my = ((e.clientY - rect.top) / rect.height) * CANVAS.h;
    let best: string | null = null;
    let bestDist = Infinity;
    for (const [fid, f] of Object.entries(snap.fish)) {
      if (!f.alive) continue;
      const d = Math.hypot(sx(f.x) - mx, sy(f.y) - my);
      if (d < bestDist) {
        bestDist = d;
        best = fid;
      }
    }
    // 命中半径按**屏幕**尺度给（24 CSS px 折回位图像素）：画布在窄列里被缩小显示
    // （640 位图 -> ~220 CSS px），若沿用固定 20 位图像素，实际只有 ~7 CSS px，人几乎点不中。
    const hitRadius = 24 * (CANVAS.w / rect.width);
    if (best && bestDist < hitRadius) {
      setSelectedFish(best);
      void getFishCard(sessionId ?? "", best)
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
            the click hit-test below drifts. 置顶（不再垂直居中，省下的纵向空间给读数）。 */}
        <div className="w-full shrink-0" style={{ aspectRatio: arenaAspect() }}>
          <canvas
            ref={canvasRef}
            width={CANVAS.w}
            height={CANVAS.h}
            onClick={handleClick}
            className="h-full w-full cursor-crosshair"
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
