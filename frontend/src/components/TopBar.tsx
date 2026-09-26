import { useUiStore } from "@/store/ui";

/**
 * Top bar: all text is real DOM (rule 7); values come from the backend session
 * summary via the store. Note `Env` is still a literal pending `SessionSummary`
 * exposing the environment (`frontend/README.md` §交互与头部统计).
 */
export function TopBar() {
  const stats = useUiStore((state) => state.stats);
  return (
    <header className="flex items-center gap-6 px-4 py-2">
      <span className="font-semibold tracking-wide">EvoGenesis</span>
      <div className="flex gap-5 text-sm text-muted-foreground">
        <StatusItem label="Env" value="Food Rich" />
        <StatusItem label="Generation" value={stats?.generation ?? 0} />
        <StatusItem
          label="Fish"
          value={stats ? `${stats.fishAlive}/${stats.population}` : "—"}
        />
        <StatusItem label="Prey" value={stats?.preyAlive ?? "—"} />
        <StatusItem label="Step" value={stats?.step ?? "—"} />
        <StatusItem label="Seed" value={stats?.seed ?? "—"} />
      </div>
    </header>
  );
}

function StatusItem({ label, value }: { label: string; value: string | number }) {
  return (
    <span>
      {label} <span className="text-foreground">{value}</span>
    </span>
  );
}
