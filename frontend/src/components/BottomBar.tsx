import { Pause, Play, RotateCcw } from "lucide-react";
import { ViewTabs } from "@/components/ViewTabs";
import { useUiStore } from "@/store/ui";
import { pauseSession } from "@/api/arena";

/**
 * Bottom bar: real buttons plus the view tabs (rule 8).
 *
 * Pause/Release 走**后端** `POST /v1/sessions/{id}/pause`（§1.7：toggle，不另开 resume）：
 * 后端的 `running=false` 会让 `release` 不再推进，因此只改前端标志会与后端脱节。
 * 无会话时退化为纯前端标志（面板尚未建会话）。
 */
export function BottomBar() {
  const running = useUiStore((state) => state.running);
  const sessionId = useUiStore((state) => state.sessionId);
  const setRunning = useUiStore((state) => state.setRunning);
  const toggleRunning = useUiStore((state) => state.toggleRunning);
  const bumpReset = useUiStore((state) => state.bumpReset);

  async function handleToggle() {
    if (!sessionId) {
      toggleRunning();
      return;
    }
    const next = !running;
    try {
      const summary = await pauseSession(sessionId);
      setRunning(summary.running);
    } catch {
      // 会话可能已被重置/删除：以本地意图为准，下一轮轮询会自行报错。
      setRunning(next);
    }
  }

  return (
    <footer className="flex items-center gap-2 px-4 py-2">
      <button
        type="button"
        onClick={() => void handleToggle()}
        className="inline-flex items-center gap-2 border border-border bg-card px-3 py-1.5 text-sm"
      >
        {running ? <Pause className="size-4" /> : <Play className="size-4" />}
        {running ? "Pause" : "Release"}
      </button>
      <button
        type="button"
        onClick={bumpReset}
        className="inline-flex items-center gap-2 border border-border bg-card px-3 py-1.5 text-sm"
      >
        <RotateCcw className="size-4" />
        Reset
      </button>
      <div className="ml-auto">
        <ViewTabs />
      </div>
    </footer>
  );
}
