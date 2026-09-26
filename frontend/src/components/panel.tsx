import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PanelProps {
  title: string;
  icon?: ReactNode;
  className?: string;
  children?: ReactNode;
}

export function Panel({ title, icon, className, children }: PanelProps) {
  return (
    <section
      className={cn(
        // 不画 border：栏间竖线由父级 .eg-grid 的 divide-x 唯一拥有（§十二）。
        // 外框由 .eg-frame 拥有。
        "flex min-h-0 flex-col overflow-hidden bg-card",
        className,
      )}
    >
      <header className="flex items-center gap-2 border-b border-border px-3 py-2">
        {icon}
        <span className="font-pixel text-[10px] leading-none">{title}</span>
      </header>
      <div className="min-h-0 flex-1 p-3">{children}</div>
    </section>
  );
}
