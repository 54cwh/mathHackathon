import { useUiStore } from "@/store/ui";

/**
 * Top bar: all text is real DOM (rule 7); values come from the backend session
 * summary via the store. Note `Env` is still a literal pending `SessionSummary`
 * exposing the environment (`frontend/README.md` §交互与头部统计).
 *
 * 排版口径（§14 Q4，本文件按该口径补齐）：**英文标题走 .font-pixel，数值走 font-mono**，
 * 中文正文才用默认字体。两个类各自唯一 owner：.font-pixel 在 index.css，font-mono 在
 * tailwind.config.ts 的 fontFamily。
 */
export function TopBar() {
  const stats = useUiStore((state) => state.stats);
  return (
    <header className="flex items-center gap-6 px-4 py-2">
      <span className="font-pixel text-xs leading-none">EvoGenesis</span>
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
      {label} <span className="font-mono text-foreground">{value}</span>
    </span>
  );
}
