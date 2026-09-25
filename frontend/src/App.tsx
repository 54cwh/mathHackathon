import { Pause, Play, RotateCcw } from "lucide-react";
import { DNA2BrainPanel } from "@/panels/DNA2BrainPanel";
import { BrainForgePanel } from "@/panels/BrainForgePanel";
import { DanioArenaPanel } from "@/panels/DanioArenaPanel";
import { useUiStore } from "@/store/ui";

function App() {
  const running = useUiStore((state) => state.running);
  const toggleRunning = useUiStore((state) => state.toggleRunning);
  const bumpReset = useUiStore((state) => state.bumpReset);
  const stats = useUiStore((state) => state.stats);

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      <header className="flex items-center gap-6 border-b border-border px-4 py-2">
        <span className="font-semibold tracking-wide">EvoGenesis</span>
        <div className="flex gap-5 text-sm text-muted-foreground">
          <span>
            Env <span className="text-foreground">Food Rich</span>
          </span>
          <span>
            Generation <span className="text-foreground">{stats?.generation ?? 0}</span>
          </span>
          <span>
            Fish <span className="text-foreground">
              {stats ? `${stats.fishAlive}/${stats.population}` : "—"}
            </span>
          </span>
          <span>
            Prey <span className="text-foreground">{stats?.preyAlive ?? "—"}</span>
          </span>
          <span>
            Step <span className="text-foreground">{stats?.step ?? "—"}</span>
          </span>
          <span>
            Seed <span className="text-foreground">{stats?.seed ?? "—"}</span>
          </span>
        </div>
      </header>

      <main className="grid min-h-0 flex-1 grid-cols-1 gap-3 p-3 lg:grid-cols-3">
        <DNA2BrainPanel />
        <BrainForgePanel />
        <DanioArenaPanel />
      </main>

      <footer className="flex items-center gap-2 border-t border-border px-4 py-2">
        <button
          type="button"
          onClick={toggleRunning}
          className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 text-sm transition-colors hover:border-primary"
        >
          {running ? <Pause className="size-4" /> : <Play className="size-4" />}
          {running ? "Pause" : "Release"}
        </button>
        <button
          type="button"
          onClick={bumpReset}
          className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 text-sm transition-colors hover:border-primary"
        >
          <RotateCcw className="size-4" />
          Reset
        </button>
        <span className="ml-auto text-xs text-muted-foreground">
          Evolution / Experiment / Playback
        </span>
      </footer>
    </div>
  );
}

export default App;
