import { Brain } from "lucide-react";
import { Panel } from "@/components/Panel";

export function BrainForgePanel() {
  return (
    <Panel title="Brain Forge" icon={<Brain className="size-4 text-primary" />}>
      <p className="text-sm text-muted-foreground">
        motif → GRN → 发育 → 连接 的发育轨迹与脑网络图将在此渲染。
      </p>
    </Panel>
  );
}
