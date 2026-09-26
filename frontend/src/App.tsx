import type { ReactNode } from "react";
import { Pause, Play, RotateCcw } from "lucide-react";
import { DNA2BrainPanel } from "@/panels/DNA2BrainPanel";
import { BrainForgePanel } from "@/panels/BrainForgePanel";
import { DanioArenaPanel } from "@/panels/DanioArenaPanel";
import { ViewTabs } from "@/components/ViewTabs";
import { useUiStore } from "@/store/ui";

/**
 * 应用外壳（方案 C：原生 DOM 外壳 + 程序化视觉 + 独立像素素材）。
 *
 * 结构（几何由 `index.css` 的 `.eg-frame` / `.eg-grid` / `.eg-arena` 拥有）：
 *
 *   Viewport
 *   └── .eg-frame  3:2，居中；宽则左右 pillarbox，窄则整体等比变小
 *       ├── TopBar     border-b（自己那一条线）
 *       ├── .eg-grid   **恒 3 列** + divide-x（栏间竖线的唯一 owner）
 *       └── BottomBar  border-t（自己那一条线）
 *
 * 顶栏数值口径（用户最终裁决）：**真实 simulation state 由 DOM 渲染真实数据**，
 * 不换成占位块（StatusPlaceholder 只用于 loading / reference / 未初始化）。
 * 红线只有一条：**数值不得烧进 PNG / sprite / Canvas 背景 / AI 素材**。
 */

function StatusItem({ label, value }: { label: string; value: ReactNode }) {
  return (
    <span>
      {label} <span className="font-mono text-foreground">{value}</span>
    </span>
  );
}

function App() {
  const running = useUiStore((state) => state.running);
  const toggleRunning = useUiStore((state) => state.toggleRunning);
  const bumpReset = useUiStore((state) => state.bumpReset);
  const stats = useUiStore((state) => state.stats);

  const buttonClass =
    "inline-flex items-center gap-2 border border-border bg-card px-3 py-1.5 " +
    "font-pixel text-[10px] leading-none hover:border-brand-shallow-water";

  return (
    <div className="flex h-screen items-center justify-center overflow-hidden bg-background text-foreground">
      <div className="eg-frame flex flex-col border border-border">
        <header className="flex items-center gap-6 border-b border-border px-4 py-2">
          <span className="font-pixel text-xs">EvoGenesis</span>
          <div className="flex gap-5 text-xs text-muted-foreground">
            <StatusItem label="Env" value="Food Rich" />
            <StatusItem label="Gen" value={stats?.generation ?? 0} />
            <StatusItem
              label="Fish"
              value={stats ? `${stats.fishAlive}/${stats.population}` : "—"}
            />
            <StatusItem label="Prey" value={stats?.preyAlive ?? "—"} />
            <StatusItem label="Step" value={stats?.step ?? "—"} />
            <StatusItem label="Seed" value={stats?.seed ?? "—"} />
          </div>
        </header>

        <main className="eg-grid divide-x divide-border">
          <DNA2BrainPanel />
          <BrainForgePanel />
          <DanioArenaPanel />
        </main>

        <footer className="flex items-center gap-2 border-t border-border px-4 py-2">
          <button type="button" onClick={toggleRunning} className={buttonClass}>
            {running ? <Pause className="size-4" /> : <Play className="size-4" />}
            {running ? "Pause" : "Release"}
          </button>
          <button type="button" onClick={bumpReset} className={buttonClass}>
            <RotateCcw className="size-4" />
            Reset
          </button>
          <ViewTabs className="ml-auto" />
        </footer>
      </div>
    </div>
  );
}

export default App;
