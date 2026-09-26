import { Brain } from "lucide-react";
import { Panel } from "@/components/panel";
import { BrainForgeVisual } from "@/visuals/BrainForgeVisual";

export function BrainForgePanel() {
  return (
    // icon 颜色改用色板角色（brand 命名空间 -> text-brand-shallow-water），
    // 不再用 text-primary。Tailwind 里品牌色前缀是 brand，不是裸的 ink/foam。
    <Panel title="Brain Forge" icon={<Brain className="size-4 text-brand-shallow-water" />}>
      <div className="flex h-full min-h-0 flex-col gap-2">
        {/* 视觉占满可分配高度；min-h-0 + overflow-hidden 保证窄列下不撑破面板。 */}
        <div className="min-h-0 flex-1 overflow-hidden">
          <BrainForgeVisual />
        </div>
        <p className="text-sm text-muted-foreground">
          motif → GRN → 发育 → 连接 的发育轨迹将在此渲染；当前为装饰纹理，不绑定 cell type 契约。
        </p>
      </div>
    </Panel>
  );
}
