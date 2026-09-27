import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PanelProps {
  title: string;
  /** 中文副标题（与英文标题并排；英文走 `.font-pixel`，中文走默认字体）。 */
  titleZh?: string;
  icon?: ReactNode;
  className?: string;
  children?: ReactNode;
}

/**
 * Panel shell: no radius (rule 4) and no outer/inter-column border — the grid
 * parent owns every dividing line (rule 5). Only the internal title separator
 * is drawn here.
 *
 * 标题字体（风格 owner 裁决 Q4(b)）：面板标题都是**英文标签**，故走 .font-pixel；
 * .font-pixel 的唯一 owner 是 index.css（除 font-family 外还带
 * -webkit-font-smoothing: none，Tailwind 的 fontFamily 表达不了该属性）。
 * 文本口径：英文标签 -> font-pixel；数值 -> font-mono；中文正文 -> 默认 font-sans。
 */
export function Panel({ title, titleZh, icon, className, children }: PanelProps) {
  return (
    <section className={cn("flex min-h-0 flex-col overflow-hidden bg-card", className)}>
      <header className="flex items-center gap-2 border-b border-border px-3 py-2">
        {icon}
        <span className="font-pixel text-[10px] leading-none">{title}</span>
        {titleZh && (
          <span className="text-[10px] leading-none text-muted-foreground">{titleZh}</span>
        )}
      </header>
      <div className="min-h-0 flex-1 p-3">{children}</div>
    </section>
  );
}
