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
  getSnapshot,
  release,
  type ArenaSnapshot,
} from "@/api/arena";

const POLL_MS = 100; // 10 fps render; backend sim runs at 20 Hz

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
  const [error, setError] = useState<string | null>(null);

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
          generation: summary.generation,
          population: summary.population,
          fishAlive: summary.fish_alive,
          preyAlive: summary.prey_remaining,
          seed: summary.master_seed,
          step: s.step,
        });
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
    if (best && bestDist < 20) setSelectedFish(best);
    else setSelectedFish(null);
  }

  return (
    <Panel title="Danio Arena" icon={<Fish className="size-4 text-primary" />}>
      <div className="flex h-full flex-col gap-2">
        {/* Explicit 5:3 contract (rule 3); the bitmap ratio must equal it, or
            the click hit-test below drifts. */}
        <div className="flex min-h-0 flex-1 items-center justify-center">
          <div className="w-full" style={{ aspectRatio: arenaAspect() }}>
            <canvas
              ref={canvasRef}
              width={CANVAS.w}
              height={CANVAS.h}
              onClick={handleClick}
              className="h-full w-full cursor-crosshair"
            />
          </div>
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{shortSessionId ? `session ${shortSessionId}` : "connecting..."}</span>
          <span>{error ? `⚠ ${error}` : "click a fish to inspect"}</span>
        </div>
      </div>
    </Panel>
  );
}
