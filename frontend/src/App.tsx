import { AppFrame } from "@/components/AppFrame";
import { TopBar } from "@/components/TopBar";
import { BottomBar } from "@/components/BottomBar";
import { Panel } from "@/components/Panel";
import { DNA2BrainPanel } from "@/panels/DNA2BrainPanel";
import { BrainForgePanel } from "@/panels/BrainForgePanel";
import { DanioArenaPanel } from "@/panels/DanioArenaPanel";
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
      <main className="grid min-h-0 flex-1 grid-cols-3 divide-x divide-border border border-border">
        {activeView === "experiment" ? (
          <>
            <DNA2BrainPanel />
            <BrainForgePanel />
            <DanioArenaPanel />
          </>
        ) : (
          <Panel title={VIEW_LABELS[activeView]} className="col-span-3">
            <p className="text-sm text-muted-foreground">此视图待实现。</p>
          </Panel>
        )}
      </main>
      <BottomBar />
    </AppFrame>
  );
}

export default App;
