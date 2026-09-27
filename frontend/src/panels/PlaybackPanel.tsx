import { SectionLabel } from "@/components/SectionLabel";
import { useCallback, useEffect, useRef, useState } from "react";
import { Gamepad2 } from "lucide-react";
import { Panel } from "@/components/Panel";
import { useUiStore } from "@/store/ui";
import { arenaAspect, CANVAS } from "@/design/geometry";
import { drawArenaScene, fishHitRadius, hitTestFish, type ArenaScene } from "@/visuals/ArenaScene";
import { getFishCard, getSnapshot, release, type FishCard } from "@/api/arena";
import { getHealth } from "@/api/health";

/**
 * Playback —— **Manual Control 操场**（`交互与可视化.md` §10）。
 *
 * 玩什么：用键盘**临时操控一条鱼**在活着的 Arena 里游；其余鱼仍由 ExpertPolicy 驱动。
 * `Manual Control 不进入正式实验数据`（§10），因此本面板只驱动当前会话，不落任何记录。
 *
 * 键位（最小集，本文与文档同步）：
 *   ← / A  左转（ω = -1）        → / D  右转（ω = +1）
 *   ↑ / W  全速（v = 1）         ↓ / S  停（v = 0）        不按上下 → 巡航 v = 0.5
 * 动作语义：`ω ∈ [-1,1]` rad/s、`v ∈ [0,1]` 世界单位/秒（`arena §461 S1`），后端再裁剪一次。
 *
 * 会话与驱动：用 `store.sessionId`（与 Arena 同一条会话）。Arena 面板在 playback 视图下
 * **让位不驱动**（见 `DanioArenaPanel` 的 `activeView` 判据），避免两处同时推进。
 * 若会话处于暂停（底栏 Pause），后端 `advance` 短路 —— 本面板会给出提示而非默默不动。
 */

const TICK_MS = 100; // 与 Arena 一致：10 Hz 驱动，20 Hz 仿真按 1 步/次推进
const CARD_EVERY = 10; // 每 10 tick ≈ 1s 刷新一次鱼卡
/** 巡航速度：不按上下键时的默认 `v`（避免"一松手就停"，也不必长按）。 */
const CRUISE_SPEED = 0.5;

/** 键位 -> 舵量；返回 [omega, speed]。 */
function actionFor(keys: Set<string>): { omega: number; speed: number } {
  const left = keys.has("ArrowLeft") || keys.has("a") || keys.has("A");
  const right = keys.has("ArrowRight") || keys.has("d") || keys.has("D");
  const up = keys.has("ArrowUp") || keys.has("w") || keys.has("W");
  const down = keys.has("ArrowDown") || keys.has("s") || keys.has("S");
  const omega = (right ? 1 : 0) - (left ? 1 : 0);
  const speed = up ? 1 : down ? 0 : CRUISE_SPEED;
  return { omega, speed };
}

export function PlaybackPanel() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sessionId = useUiStore((s) => s.sessionId);
  const running = useUiStore((s) => s.running);
  const activeView = useUiStore((s) => s.activeView);
  const stats = useUiStore((s) => s.stats);
  const [scene, setScene] = useState<ArenaScene | null>(null);
  const [controlledId, setControlledId] = useState<string | null>(null);
  const [card, setCard] = useState<FishCard | null>(null);
  const [error, setError] = useState<string | null>(null);
  /** 后端能力位：旧进程缺 `manual_control` ⇒ 操控请求会被静默忽略（实测踩过）。 */
  const [staleBackend, setStaleBackend] = useState(false);
  const keysRef = useRef<Set<string>>(new Set());
  const controlledRef = useRef<string | null>(null);
  const tickRef = useRef(0);

  const active = activeView === "playback";

  // 后端能力自检：只在进入本视图时探一次（旧进程会静默忽略手动动作参数）。
  useEffect(() => {
    if (!active) return;
    let stop = false;
    void getHealth()
      .then((h) => !stop && setStaleBackend(h.manual_control !== true))
      .catch(() => !stop && setStaleBackend(true));
    return () => {
      stop = true;
    };
  }, [active]);

  // 键盘：只在 playback 视图监听；方向键要阻止页面滚动。
  useEffect(() => {
    if (!active) return;
    const down = (e: KeyboardEvent) => {
      const k = e.key;
      if (/^(Arrow|wasdWASD)/.test(k)) {
        e.preventDefault();
        keysRef.current.add(k);
      }
    };
    const keys = keysRef.current; // cleanup 里用局部引用（ref.current 那时可能已变）
    const up = (e: KeyboardEvent) => keys.delete(e.key);
    const clearKeys = () => keys.clear();
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    window.addEventListener("blur", clearKeys);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
      window.removeEventListener("blur", clearKeys);
      keys.clear();
    };
  }, [active]);

  // 驱动循环：只有本视图激活时才推进（Arena 面板此时让位）。
  useEffect(() => {
    if (!active || !running || !sessionId) return;
    let stop = false;
    let timer = 0;

    const tick = async () => {
      try {
        const { omega, speed } = actionFor(keysRef.current);
        const target = controlledRef.current;
        const summary = await release(
          sessionId,
          1,
          true,
          target ? { fishId: target, omega, speed } : undefined,
        );
        const snap = await getSnapshot(sessionId);
        if (stop) return;
        setScene({ ...snap });
        // 首次进入或原被控鱼已死：自动接管第一条存活的鱼。
        if (!controlledRef.current || !snap.fish[controlledRef.current]?.alive) {
          const first = Object.entries(snap.fish).find(([, f]) => f.alive)?.[0] ?? null;
          controlledRef.current = first;
          setControlledId(first);
        }
        tickRef.current += 1;
        if (tickRef.current % CARD_EVERY === 0 && controlledRef.current) {
          setCard(await getFishCard(sessionId, controlledRef.current));
        }
        void summary;
      } catch (e) {
        if (stop) return;
        setError(String(e));
        return;
      }
      if (!stop) timer = window.setTimeout(tick, TICK_MS);
    };

    tickRef.current = 0;
    timer = window.setTimeout(tick, TICK_MS);
    return () => {
      stop = true;
      window.clearTimeout(timer);
    };
  }, [active, running, sessionId]);

  // 绘制：被控鱼高亮（复用 Arena 的选中样式）
  useEffect(() => {
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    if (scene) drawArenaScene(ctx, scene, controlledId);
    else ctx.clearRect(0, 0, CANVAS.w, CANVAS.h);
  }, [scene, controlledId]);

  const takeControl = useCallback((fishId: string | null) => {
    controlledRef.current = fishId;
    setControlledId(fishId);
    setCard(null);
  }, []);

  function handleClick(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!scene) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const mx = ((e.clientX - rect.left) / rect.width) * CANVAS.w;
    const my = ((e.clientY - rect.top) / rect.height) * CANVAS.h;
    takeControl(hitTestFish(scene, mx, my, fishHitRadius(rect.width)));
  }

  const alive = scene ? Object.entries(scene.fish).filter(([, f]) => f.alive) : [];
  const held = actionFor(keysRef.current);

  return (
    <Panel title="Playback" titleZh="手动操控" icon={<Gamepad2 className="size-4 text-primary" />}>
      <div className="flex h-full min-h-0 flex-col gap-2">
        <div className="w-full shrink-0" style={{ aspectRatio: arenaAspect() }}>
          <canvas
            ref={canvasRef}
            width={CANVAS.w}
            height={CANVAS.h}
            onClick={handleClick}
            className="pixelated h-full w-full cursor-crosshair"
          />
        </div>

        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
          {/* 被控鱼：点画布上的鱼可切换；默认第一条存活的鱼 */}
          <div className="border border-border p-2">
            <div className="mb-1 flex items-center justify-between">
              <SectionLabel en="CONTROLLED FISH" zh="被控鱼" />
              <span className="whitespace-nowrap font-mono text-[10px] text-muted-foreground">
                {controlledId ?? "—"}
              </span>
            </div>
            <div className="flex flex-wrap gap-1">
              {alive.map(([fid]) => (
                <button
                  key={fid}
                  type="button"
                  onClick={() => takeControl(fid)}
                  className={`border border-border px-2 py-0.5 font-mono text-[10px] ${
                    fid === controlledId ? "bg-brand-fish-navy text-brand-bone" : ""
                  }`}
                >
                  {fid}
                </button>
              ))}
              {alive.length === 0 && (
                <span className="whitespace-nowrap font-mono text-[10px] text-muted-foreground">
                  {sessionId ? "等待会话场景…" : "无会话：Experiment 视图的 Arena 尚未连上后端"}
                </span>
              )}
            </div>
          </div>

          {/* 键位 + 当前动作 + 实时读数 */}
          <div className="grid grid-cols-2 gap-2">
            <div className="border border-border p-2">
              <div className="mb-1"><SectionLabel en="KEYS" zh="按键" /></div>
              <div className="space-y-0.5 font-mono text-[10px] text-muted-foreground">
                <div>← / A · → / D : turn (ω)</div>
                <div>↑ / W · ↓ / S : speed (v)</div>
                <div>click fish : take control</div>
              </div>
              <div className="mt-1 flex justify-between font-mono text-xs">
                <span>ω {held.omega.toFixed(2)}</span>
                <span>v {held.speed.toFixed(2)}</span>
              </div>
            </div>
            <div className="border border-border p-2">
              <div className="mb-1"><SectionLabel en="READOUT" zh="读数" /></div>
              {card ? (
                <dl className="grid grid-cols-2 gap-x-2 font-mono text-xs">
                  {[
                    ["energy", card.energy.toFixed(3)],
                    ["captures", String(card.metrics.captures)],
                    ["steps", String(card.metrics.survival_steps)],
                    ["alive", card.metrics.alive ? "yes" : "no"],
                  ].map(([label, value]) => (
                    <div key={label} className="flex justify-between gap-2">
                      <dt className="text-muted-foreground">{label}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p className="text-xs text-muted-foreground">按 → 起步后出现读数</p>
              )}
            </div>
          </div>

          {staleBackend && (
            <p className="border border-brand-danger-red p-2 text-xs text-brand-danger-red">
              ⚠ 后端版本落后：当前运行的后端不支持手动控制。请重启后端服务后重试
              （后端已升级但未重启时，操控参数会被忽略，按键看起来无效）。
            </p>
          )}

          <p className="text-xs text-muted-foreground">
            {error
              ? `⚠ ${error}`
              : !running
                ? "会话已暂停：底栏按 Release 恢复推进，再操控。"
                : `手动操控：临时操控一条鱼，不进入正式实验数据。step ${
                    stats?.step ?? scene?.step ?? "—"
                  }`}
          </p>
        </div>
      </div>
    </Panel>
  );
}
