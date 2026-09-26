import { useEffect, useRef, useState } from "react";
import { Fish } from "lucide-react";
import { Panel } from "@/components/panel";
import { useUiStore } from "@/store/ui";
import {
  MASTER_SEED,
  createSession,
  deleteSession,
  getSnapshot,
  release,
  type ArenaSnapshot,
} from "@/api/arena";

const WORLD_W = 100;
const WORLD_H = 60;
const CANVAS_W = 640;
const CANVAS_H = 384;
const POLL_MS = 100; // 10 fps render; backend sim runs at 20 Hz

function sx(x: number): number {
  return (x / WORLD_W) * CANVAS_W;
}
function sy(y: number): number {
  return (y / WORLD_H) * CANVAS_H;
}
function sr(r: number): number {
  return (r / WORLD_W) * CANVAS_W;
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
    ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
    ctx.fillStyle = "#0B1220";
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

    if (!snap) return;

    for (const o of snap.obstacles) {
      ctx.beginPath();
      ctx.arc(sx(o.x), sy(o.y), sr(o.radius), 0, Math.PI * 2);
      ctx.fillStyle = "#374151";
      ctx.fill();
      ctx.strokeStyle = "#6B7280";
      ctx.stroke();
    }

    for (const p of Object.values(snap.prey)) {
      if (!p.alive) continue;
      ctx.beginPath();
      ctx.arc(sx(p.x), sy(p.y), Math.max(2, sr(p.size) * 1.5), 0, Math.PI * 2);
      ctx.fillStyle = "#34D399";
      ctx.fill();
    }

    for (const d of Object.values(snap.predators)) {
      ctx.beginPath();
      ctx.arc(sx(d.x), sy(d.y), sr(d.size) * 3, 0, Math.PI * 2);
      ctx.fillStyle = "#F87171";
      ctx.fill();
      ctx.strokeStyle = "#DC2626";
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
      ctx.fillStyle = isSelected ? "#FBBF24" : "#60A5FA";
      ctx.fill();
      ctx.strokeStyle = isSelected ? "#F59E0B" : "#2563EB";
      ctx.lineWidth = isSelected ? 2 : 1;
      ctx.stroke();

      if (isSelected) {
        ctx.beginPath();
        ctx.arc(x, y, len + 4, -Math.PI / 2, -Math.PI / 2 + f.energy * Math.PI * 2);
        ctx.strokeStyle = f.energy > 0.3 ? "#34D399" : "#F87171";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }

    ctx.fillStyle = "#9CA3AF";
    ctx.font = "12px monospace";
    ctx.fillText(`step ${snap.step}`, 8, 16);
  }, [snap, selectedFishId]);

  // Session ids look like "session_ab12cd34ef56" -- show the hex, not the prefix.
  const shortSessionId = sessionId ? sessionId.replace(/^session_/, "").slice(0, 8) : null;

  function handleClick(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!snap) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const mx = ((e.clientX - rect.left) / rect.width) * CANVAS_W;
    const my = ((e.clientY - rect.top) / rect.height) * CANVAS_H;
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
        {/* The canvas bitmap carries the arena's 100:60 intrinsic ratio; letting
            it fill the column non-uniformly would stretch every fish vertically. */}
        <div className="flex min-h-0 flex-1 items-center justify-center">
          <canvas
            ref={canvasRef}
            width={CANVAS_W}
            height={CANVAS_H}
            onClick={handleClick}
            className="max-h-full max-w-full cursor-crosshair rounded-md"
          />
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{shortSessionId ? `session ${shortSessionId}` : "connecting..."}</span>
          <span>{error ? `⚠ ${error}` : "click a fish to inspect"}</span>
        </div>
      </div>
    </Panel>
  );
}
