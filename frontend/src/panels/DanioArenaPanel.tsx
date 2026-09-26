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
import { ARENA } from "@/design/palette";

const WORLD_W = 100;
const WORLD_H = 60;
const CANVAS_W = 640;
const CANVAS_H = 384;
const POLL_MS = 100; // 10 fps render; backend sim runs at 20 Hz

/**
 * 世界 -> 画布映射。**这三个 helper 一律返回整数**。
 *
 * 小数坐标会让 `ctx.arc` / `moveTo`+`lineTo` 的边缘被抗锯齿柔化 —— 这是审计
 * §A.2 规则 9(b) 认定的**当前唯一真像素缺陷**。取整集中放在这里，所有调用点
 * 一次性生效（含 `handleClick` 的命中测试，±0.5px 不影响判定）。
 */
function sx(x: number): number {
  return Math.round((x / WORLD_W) * CANVAS_W);
}
function sy(y: number): number {
  return Math.round((y / WORLD_H) * CANVAS_H);
}
function sr(r: number): number {
  return Math.round((r / WORLD_W) * CANVAS_W);
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
    // 关掉插值：将来 drawImage 贴像素精灵时不会被双线性放大糊掉（§十一）。
    // 注意：几何图元的锐度靠**整数坐标**保证，不是靠这一行。
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
    ctx.fillStyle = ARENA.canvas;
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

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

    // 原来此处把 `step N` 用 fillText 烧进位图（审计 §A.2 规则 6 的唯一硬违规）——
    // 已删除。按用户裁决，数值一律由 DOM 渲染真实数据，见下方状态行。
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
        {/* 视口**恒 5:3**（`.eg-arena`，owner = `index.css` 的几何契约区）。
            位图 640x384 同为 5:3，故 `w-full h-full` 不会变形；命中测试走
            `getBoundingClientRect` 线性映射，只有等比才不会系统性偏移。
            **不再 `flex-1` 撑满纵向** —— Arena 不为了填满右栏而拉伸（§七）；
            余下纵向空间留给下方状态行与留白。 */}
        <div className="eg-arena">
          <canvas
            ref={canvasRef}
            width={CANVAS_W}
            height={CANVAS_H}
            onClick={handleClick}
            className="block h-full w-full cursor-crosshair"
          />
        </div>
        <div className="mt-auto flex items-center justify-between gap-2 text-xs text-muted-foreground">
          <span className="font-mono">
            {shortSessionId ? `session ${shortSessionId}` : "connecting..."}
          </span>
          {/* step 是真实 simulation state，由 DOM 渲染（用户裁决：数值不得烧进位图）。 */}
          <span className="font-mono">{snap ? `step ${snap.step}` : "—"}</span>
          <span>{error ? `⚠ ${error}` : "click a fish to inspect"}</span>
        </div>
      </div>
    </Panel>
  );
}
