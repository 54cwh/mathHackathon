import { cn } from "@/lib/utils";

/**
 * 分节标签：英文（`.font-pixel`）+ 中文（默认字体）并排。
 *
 * 口径（`交互与可视化.md` §14 Q4）：**英文标签走像素字体、中文走默认字体**（像素字体无 CJK 覆盖）。
 * 界面上的分节标题一律用本组件，避免用户只看到英文缩写看不懂。
 */
export function SectionLabel({
  en,
  zh,
  className,
}: {
  en: string;
  zh?: string;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-baseline gap-1.5", className)}>
      <span className="font-pixel text-xs leading-none">{en}</span>
      {zh && <span className="text-xs leading-none text-muted-foreground">{zh}</span>}
    </span>
  );
}
