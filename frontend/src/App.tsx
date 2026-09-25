import { Pause, Play, RotateCcw } from "lucide-react";
import { DNA2BrainPanel } from "@/panels/DNA2BrainPanel";
import { BrainForgePanel } from "@/panels/BrainForgePanel";
import { DanioArenaPanel } from "@/panels/DanioArenaPanel";
import { useUiStore } from "@/store/ui";

const stats = [
  { label: "Env", value: "Food Rich" },
  { label: "Generation", value: "0" },
  { label: "Population", value: "0" },
  { label: "Seed", value: "—" },
];

function App() {
  const running = useUiStore((state) => state.running);
  const toggleRunning = useUiStore((state) => state.toggleRunning);
  const reset = useUiStore((state) => state.reset);

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      <header className="flex items-center gap-6 border-b border-border px-4 py-2">
        <span className="font-semibold tracking-wide">EvoGenesis</span>
        <div className="flex gap-5 text-sm text-muted-foreground">
          {stats.map((item) => (
            <span key={item.label}>
              {item.label}{" "}
              <span className="text-foreground">{item.value}</span>
            </span>
          ))}
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
          {running ? (
            <Pause className="size-4" />
          ) : (
            <Play className="size-4" />
          )}
          {running ? "Pause" : "Release"}
        </button>
        <button
          type="button"
          onClick={reset}
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
