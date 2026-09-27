import { cn } from "@/lib/utils";
import { useUiStore, type ViewId } from "@/store/ui";

/**
 * 底栏视图切换（§二 item 12）。
 *
 * 改造前：`App.tsx` 里是**一个 `<span>`** —— 没有点击目标、不可能有 active 态
 * （审计 §A.2 规则 8 记为「需从零加功能，不是改样式」）。
 *
 * 三条硬规则：
 *  - **真 `<button>` + `role="tab"`**，active 由 `store.activeView` 驱动；
 *  - 栏间分隔由**本容器自己**拥有（`divide-x`），与三栏网格同源，**不加 gap**；
 *  - 无圆角、无过渡、无投影 —— 底色切换是**瞬变**，不做插值（§十一）。
 *
 * 踩过的坑（写给后来改它的人）：**注释里不要写裸的 Tailwind 类名**。
 * Tailwind 扫的是原始文本、不剥注释，写了就会被当成「用过的类」打进 CSS 产物；
 * 而静态检查剥注释，抓不到 —— 两边口径不一致，是真实发生过的泄漏。
 */

const VIEWS: ReadonlyArray<{ id: ViewId; label: string; zh: string }> = [
  { id: "evolution", label: "Evolution", zh: "演化" },
  { id: "experiment", label: "Experiment", zh: "实验台" },
  { id: "playback", label: "Playback", zh: "手动操控" },
];

export function ViewTabs() {
  const activeView = useUiStore((s) => s.activeView);
  const setActiveView = useUiStore((s) => s.setActiveView);

  return (
    <div
      role="tablist"
      aria-label="View"
      className="flex items-stretch divide-x divide-border border border-border"
    >
      {VIEWS.map((view) => {
        const active = view.id === activeView;
        return (
          <button
            key={view.id}
            type="button"
            role="tab"
            aria-selected={active}
            title={view.zh}
            onClick={() => setActiveView(view.id)}
            className={cn(
              "px-3 py-1.5 font-pixel text-xs leading-none",
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
