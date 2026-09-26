import { Pause, Play, RotateCcw } from "lucide-react";
import { ViewTabs } from "@/components/ViewTabs";
import { useUiStore } from "@/store/ui";

/** Bottom bar: real buttons plus the view tabs (rule 8). */
export function BottomBar() {
  const running = useUiStore((state) => state.running);
  const toggleRunning = useUiStore((state) => state.toggleRunning);
  const bumpReset = useUiStore((state) => state.bumpReset);
  return (
    <footer className="flex items-center gap-2 px-4 py-2">
      <button
        type="button"
        onClick={toggleRunning}
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
