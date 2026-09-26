import { AppFrame } from "@/components/AppFrame";
import { TopBar } from "@/components/TopBar";
import { BottomBar } from "@/components/BottomBar";
import { Panel } from "@/components/Panel";
import { DNA2BrainPanel } from "@/panels/DNA2BrainPanel";
import { BrainForgePanel } from "@/panels/BrainForgePanel";
import { DanioArenaPanel } from "@/panels/DanioArenaPanel";
import { EvolutionDashboardPanel } from "@/panels/EvolutionDashboardPanel";
import { cn } from "@/lib/utils";
import { useUiStore, type ViewId } from "@/store/ui";

const VIEW_LABELS: Record<ViewId, string> = {
  evolution: "Evolution Dashboard",
  experiment: "Experiment Bench",
  playback: "Playback",
};

function App() {
  const activeView = useUiStore((state) => state.activeView);
  return (
    <AppFrame>
      <TopBar />
      {/*
        三个视图**常驻挂载**、用 hidden 切换 —— 不用条件渲染。
        原因（实测）：条件渲染会在切视图时卸载面板，Arena 面板的 cleanup 会顺手
        `deleteSession`，于是 Evolution 视图里「会话内演化」永远拿不到会话；
        切换回来还会重建会话、重抽 genome、丢失任务列表。常驻挂载后各面板状态连续。
        分隔线归各自 grid 父级（`divide-x`），不用面板自带边框。
      */}
      <main className="min-h-0 flex-1 border border-border">
        <div
          className={cn(
            "grid h-full min-h-0 grid-cols-3 divide-x divide-border",
            activeView !== "experiment" && "hidden",
          )}
        >
          <DNA2BrainPanel />
          <BrainForgePanel />
          <DanioArenaPanel />
        </div>

        <div className={cn("h-full min-h-0", activeView !== "evolution" && "hidden")}>
          <EvolutionDashboardPanel />
        </div>

        <div className={cn("h-full min-h-0", activeView !== "playback" && "hidden")}>
          <Panel title={VIEW_LABELS.playback} className="h-full">
            <p className="text-sm text-muted-foreground">此视图待实现。</p>
          </Panel>
        </div>
      </main>
      <BottomBar />
    </AppFrame>
  );
}

export default App;
