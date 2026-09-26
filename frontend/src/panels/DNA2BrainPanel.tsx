import { Dna } from "lucide-react";
import { Panel } from "@/components/panel";
import { DnaHelixVisual } from "@/visuals/DnaHelixVisual";
import { NucleotideStrip } from "@/visuals/NucleotideStrip";

export function DNA2BrainPanel() {
  return (
    // icon 颜色改用色板角色（brand 命名空间 -> text-brand-shallow-water）。
    <Panel title="DNA2Brain Lab" icon={<Dna className="size-4 text-brand-shallow-water" />}>
      {/*
        DNA2Brain Lab
        ├── DnaHelixVisual     （上，吃掉剩余高度）
        └── NucleotideStrip    （下，按内容长高，不传 sequence -> 未初始化一行）
        两个视觉上下排布；min-h-0 + overflow-hidden 保证窄列 / 矮面板下不溢出。
      */}
      <div className="flex h-full min-h-0 flex-col gap-2">
        <div className="min-h-0 flex-1 overflow-hidden">
          <DnaHelixVisual />
        </div>
        {/* shrink-0 + max-h-28：条带只占自己那一格，碱基再多也不会把上面挤扁。 */}
        <div className="min-h-0 max-h-28 shrink-0 overflow-hidden">
          {/* 前端暂无碱基数据的真实来源，故不传 sequence：组件会显示未初始化态。 */}
          <NucleotideStrip />
        </div>
        <p className="shrink-0 text-sm text-muted-foreground">
          DNA 双螺旋与 nucleotide 序列条；碱基序列在后端提供字段前保持未初始化。
        </p>
      </div>
    </Panel>
  );
}
