import { Brain } from "lucide-react";
import { Panel } from "@/components/Panel";
import { BrainForgeVisual } from "@/visuals/BrainForgeVisual";

export function BrainForgePanel() {
  return (
    <Panel title="Brain Forge" icon={<Brain className="size-4 text-primary" />}>
      <div className="flex h-full min-h-0 flex-col gap-2">
        {/* 视觉吃掉剩余高度；min-h-0 + overflow-hidden 保证窄列 / 矮面板下不撑破。 */}
        <div className="min-h-0 flex-1 overflow-hidden">
          <BrainForgeVisual />
        </div>
        {/* 文案口径修正：**不写**「脑网络图」——§八 明令禁止 node-edge 图 / 树 /
            hub-spoke / NN 拓扑，本视觉是程序化装饰纹理，且不绑定 cell type 契约
            （core §10 的「六类 cell type owner」尚未定稿）。 */}
        <p className="shrink-0 text-sm text-muted-foreground">
          motif → GRN → 发育 → 连接 的轨迹将在此接入；当前为程序化装饰纹理。
        </p>
      </div>
    </Panel>
  );
}
