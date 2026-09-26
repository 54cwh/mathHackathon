import { cn } from "@/lib/utils";
import { useUiStore, type UiView } from "@/store/ui";

/**
 * 底栏视图切换（§二 item 12）。
 *
 * 改造前：`App.tsx` 里是**一个 `<span>`** —— 没有点击目标、不可能有 active 态
 * （审计 §A.2 规则 8 记为「需从零加功能，不是改样式」）。
 *
 * 三条硬规则：
 *  - **真 `<button>` + `role="tab"`**，active 由 `store.activeView` 驱动；
 *  - 栏间分隔用 `divide-x`（父级唯一拥有），**不加 gap**，与三栏同源；
 *  - 无圆角、无过渡、无投影 —— 底色切换是**瞬变**，不做插值（§十一）。
 *    （谨慎：注释里也**不要写裸的 Tailwind 类名** —— Tailwind 扫的是原始文本、
 *     不剥注释，写了就会被当成用过的类打进 CSS 产物。R6 剥注释，故不报。）
 */

const VIEWS: ReadonlyArray<{ id: UiView; label: string }> = [
  { id: "evolution", label: "Evolution" },
  { id: "experiment", label: "Experiment" },
  { id: "playback", label: "Playback" },
];

export function ViewTabs({ className }: { className?: string }) {
  const activeView = useUiStore((s) => s.activeView);
  const setActiveView = useUiStore((s) => s.setActiveView);

  return (
    <div
      role="tablist"
      aria-label="View"
      className={cn("flex items-stretch divide-x divide-border border border-border", className)}
    >
      {VIEWS.map((view) => {
        const active = view.id === activeView;
        return (
          <button
            key={view.id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => setActiveView(view.id)}
            className={cn(
              "px-3 py-1.5 font-pixel text-[10px] leading-none",
              active
                ? "bg-brand-fish-navy text-brand-bone"
                : "bg-card text-muted-foreground hover:bg-brand-slate-shadow hover:text-brand-bone",
            )}
          >
            {view.label}
          </button>
        );
      })}
    </div>
  );
}
