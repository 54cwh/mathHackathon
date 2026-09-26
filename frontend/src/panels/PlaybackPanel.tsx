import { useEffect, useRef, useState } from "react";
import { History, Pause, Play, Rewind } from "lucide-react";
import { Panel } from "@/components/Panel";
import { arenaAspect, CANVAS } from "@/design/geometry";
import { drawArenaScene, type ArenaScene } from "@/visuals/ArenaScene";
import { REPLAY_CAPACITY, frameCount, getFrame, latestFrame } from "@/visuals/replayBuffer";

/**
 * Playback —— 回放**本次会话**（前端本地缓冲，`src/visuals/replayBuffer.ts`）。
 *
 * 语义状态：**草案待确认（2026-09-27）**。上游（`交互与可视化.md` §1）只有底栏词
 * 「Playback」，未定义正式契约；后端也**没有**回放端点（`app.py` 只挂前端 dist），
 * 而已定稿的整群回放资产 `behavior_trace`（`schemas/behavior_trace.schema.json`）
 * 尚无 HTTP 出口。故本轮实现为「回放刚看过的会话」：数据由 `DanioArenaPanel`
 * 逐 tick 写入环形缓冲，本面板只读。若后端补上 behavior_trace 端点，替换点只有
 * `replayBuffer` 一处。
 *
 * 渲染复用 `ArenaScene` 原语（与 Arena 同源，命中半径/配色/取整都不重写）。
 */

/** 播放帧率：与 Arena 采集节奏一致（10Hz）。 */
const FPS = 10;

export function PlaybackPanel() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [cursor, setCursor] = useState(0);
  const [total, setTotal] = useState(0);
  const [playing, setPlaying] = useState(false);
  const cursorRef = useRef(0);
  const playingRef = useRef(false);

  // 播放循环：只在本地读缓冲，不把逐帧数据放进 React state（README 防坑 3）。
  useEffect(() => {
    let raf = 0;
    let last = 0;
    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      const count = frameCount();
      if (count !== total) setTotal(count);
      if (!playingRef.current) return;
      if (now - last < 1000 / FPS) return;
      last = now;
      const next = cursorRef.current + 1;
      if (next >= count) {
        playingRef.current = false;
        setPlaying(false);
        return;
      }
      cursorRef.current = next;
      setCursor(next);
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [total]);

  // 绘制当前帧
  useEffect(() => {
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    const scene: ArenaScene | undefined = getFrame(Math.min(cursor, Math.max(0, total - 1)));
    if (scene) drawArenaScene(ctx, scene);
    else {
      ctx.clearRect(0, 0, CANVAS.w, CANVAS.h);
    }
  }, [cursor, total]);

  const atEnd = total > 0 && cursor >= total - 1;

  function jumpTo(index: number) {
    const clamped = Math.max(0, Math.min(total - 1, index));
    cursorRef.current = clamped;
    setCursor(clamped);
  }

  function togglePlay() {
    if (total === 0) return;
    // 已在末尾再点播放 = 从头放（与录像机行为一致）。
    if (!playing && atEnd) jumpTo(0);
    playingRef.current = !playingRef.current;
    setPlaying(playingRef.current);
  }

  return (
    <Panel title="Playback" icon={<History className="size-4 text-primary" />}>
      <div className="flex h-full min-h-0 flex-col gap-2">
        <div className="w-full shrink-0" style={{ aspectRatio: arenaAspect() }}>
          <canvas
            ref={canvasRef}
            width={CANVAS.w}
            height={CANVAS.h}
            aria-hidden
            className="pixelated h-full w-full"
          />
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={togglePlay}
            disabled={total === 0}
            className="inline-flex items-center gap-1 border border-border px-2 py-1 font-pixel text-[10px] leading-none disabled:cursor-not-allowed disabled:text-muted-foreground"
          >
            {playing ? <Pause className="size-3" /> : <Play className="size-3" />}
            {playing ? "PAUSE" : "PLAY"}
          </button>
          <button
            type="button"
            onClick={() => jumpTo(0)}
            disabled={total === 0}
            className="inline-flex items-center gap-1 border border-border px-2 py-1 font-pixel text-[10px] leading-none disabled:cursor-not-allowed disabled:text-muted-foreground"
          >
            <Rewind className="size-3" />
            START
          </button>
          <input
            type="range"
            min={0}
            max={Math.max(0, total - 1)}
            value={Math.min(cursor, Math.max(0, total - 1))}
            onChange={(e) => jumpTo(Number(e.target.value))}
            disabled={total === 0}
            aria-label="replay position"
            className="ml-1 min-w-0 flex-1"
          />
          <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
            {total === 0 ? "0/0" : `${cursor + 1}/${total}`}
          </span>
        </div>

        <div className="min-h-0 flex-1 space-y-1 overflow-y-auto border border-border p-2 font-mono text-[10px]">
          <div className="flex justify-between">
            <span className="text-muted-foreground">buffered</span>
            <span>
              {total}/{REPLAY_CAPACITY} 帧
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">step</span>
            <span>{getFrame(cursor)?.step ?? latestFrame()?.step ?? "—"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">fish alive</span>
            <span>
              {
                Object.values(getFrame(cursor)?.fish ?? {}).filter((f) => f.alive).length
              }
            </span>
          </div>
          <p className="pt-1 font-sans text-xs text-muted-foreground">
            回放本次会话（缓冲上限 {REPLAY_CAPACITY} 帧 ≈ 1 episode）。切到 Experiment 视图继续跑，
            缓冲会持续增长；Reset 会清空。
          </p>
        </div>
      </div>
    </Panel>
  );
}
