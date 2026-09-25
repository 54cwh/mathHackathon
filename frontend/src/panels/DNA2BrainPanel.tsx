import { Dna } from "lucide-react";
import { Panel } from "@/components/panel";

export function DNA2BrainPanel() {
  return (
    <Panel title="DNA2Brain Lab" icon={<Dna className="size-4 text-primary" />}>
      <p className="text-sm text-muted-foreground">
        3D DNA 螺旋与 2D nucleotide 编辑条将在此接入后端编辑接口。
      </p>
    </Panel>
  );
}
