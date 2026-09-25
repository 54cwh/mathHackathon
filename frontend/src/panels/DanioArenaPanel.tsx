import { useEffect, useRef } from "react";
import { Fish } from "lucide-react";
import { Panel } from "@/components/panel";

export function DanioArenaPanel() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const { width, height } = canvas;
    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = "#1F2A37";
    ctx.lineWidth = 1;
    ctx.strokeRect(0.5, 0.5, width - 1, height - 1);
  }, []);

  return (
    <Panel title="Danio Arena" icon={<Fish className="size-4 text-primary" />}>
      <canvas
        ref={canvasRef}
        width={640}
        height={384}
        className="h-full w-full rounded-md"
      />
    </Panel>
  );
}
