import { Dna } from "lucide-react";
import { Panel } from "@/components/Panel";
import { DnaHelixVisual } from "@/visuals/DnaHelixVisual";
import { NucleotideStrip } from "@/visuals/NucleotideStrip";

export function DNA2BrainPanel() {
  return (
    <Panel title="DNA2Brain Lab" icon={<Dna className="size-4 text-primary" />}>
      {/*
        DNA2Brain Lab
        ├── DnaHelixVisual     （上，吃掉剩余高度）
        └── NucleotideStrip    （下，按内容长高；不传 sequence -> 未初始化一行）

        文案口径修正：**不写**「3D DNA 螺旋 / three.js」——§九 明令本轮不用
        Three.js、不做 glossy/PBR，双螺旋是**2D 像素**画法。
      */}
      <div className="flex h-full min-h-0 flex-col gap-2">
        <div className="min-h-0 flex-1 overflow-hidden">
          <DnaHelixVisual />
        </div>
        {/* shrink-0 + max-h-28：条带只占自己那一格，碱基再多也不会把上面挤扁。 */}
        <div className="min-h-0 max-h-28 shrink-0 overflow-hidden">
          {/* 前端暂无碱基的真实来源（snapshot 不含 genotype），故不传 sequence。 */}
          <NucleotideStrip />
        </div>
        <p className="shrink-0 text-sm text-muted-foreground">
          DNA 双螺旋（2D 像素）与 nucleotide 序列条；碱基序列在后端提供字段前保持未初始化。
        </p>
      </div>
    </Panel>
  );
}
