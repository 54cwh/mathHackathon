import { useUiStore, type ViewId } from "@/store/ui";
import { cn } from "@/lib/utils";

const VIEWS: { id: ViewId; label: string }[] = [
  { id: "evolution", label: "Evolution" },
  { id: "experiment", label: "Experiment" },
  { id: "playback", label: "Playback" },
];

/** Real view tabs with an active state (`视觉规范审计.md` rule 8). */
export function ViewTabs() {
  const activeView = useUiStore((state) => state.activeView);
  const setActiveView = useUiStore((state) => state.setActiveView);
  return (
    <div className="flex items-center gap-1" role="tablist">
      {VIEWS.map((view) => (
        <button
          key={view.id}
          type="button"
          role="tab"
          aria-selected={view.id === activeView}
          onClick={() => setActiveView(view.id)}
          className={cn(
            "px-2 py-1 text-sm",
            view.id === activeView ? "text-foreground" : "text-muted-foreground",
          )}
        >
          {view.label}
        </button>
      ))}
    </div>
  );
}
