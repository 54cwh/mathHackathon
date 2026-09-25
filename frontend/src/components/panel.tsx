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
        "flex min-h-0 flex-col overflow-hidden rounded-lg border border-border bg-card",
        className,
      )}
    >
      <header className="flex items-center gap-2 border-b border-border px-3 py-2">
        {icon}
        <span className="text-sm font-medium">{title}</span>
      </header>
      <div className="min-h-0 flex-1 p-3">{children}</div>
    </section>
  );
}
