import type { ReactNode } from "react";
import { frameAspect, frameWidth } from "@/design/geometry";

/**
 * Overall frame: 3:2 with pillarbox (rule 1). The only component allowed to
 * constrain the app's aspect ratio.
 */
export function AppFrame({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen w-screen items-center justify-center bg-background">
      <div
        className="flex flex-col overflow-hidden bg-background text-foreground"
        style={{ aspectRatio: frameAspect(), width: frameWidth(), maxHeight: "100dvh" }}
      >
        {children}
      </div>
    </div>
  );
}
