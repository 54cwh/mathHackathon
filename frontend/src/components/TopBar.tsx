import { useEffect, useState } from "react";
import { useUiStore } from "@/store/ui";
import { getHealth } from "@/api/health";
import { JourneyBar } from "@/components/JourneyBar";

/**
 * Top bar: all text is real DOM (rule 7); values come from the backend session
 * summary via the store. `Env` 取 `SessionSummary.environment`（后端已有该字段），
 * 未起会话时显示 `—`（不再写死 "Food Rich"）。
 *
 * 排版口径（§14 Q4，本文件按该口径补齐）：**英文标题走 .font-pixel，数值走 font-mono**，
 * 中文正文才用默认字体。两个类各自唯一 owner：.font-pixel 在 index.css，font-mono 在
 * tailwind.config.ts 的 fontFamily。
 */
/** 健康探测间隔：现场离线时后端未起也能在顶栏直接看见。 */
const HEALTH_MS = 10_000;

export function TopBar() {
  const stats = useUiStore((state) => state.stats);
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let stop = false;
    const probe = async () => {
      try {
        const h = await getHealth();
        if (!stop) setHealthy(h.status === "ok");
      } catch {
        if (!stop) setHealthy(false);
      }
    };
    void probe();
    const timer = window.setInterval(probe, HEALTH_MS);
    return () => {
      stop = true;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <header className="flex items-center gap-6 px-4 py-2">
      <span className="font-pixel text-xs leading-none">EvoGenesis</span>
      <span
        aria-label={healthy === null ? "backend unknown" : healthy ? "backend ok" : "backend down"}
        title={healthy === null ? "backend unknown" : healthy ? "backend ok" : "backend down"}
        className={`inline-block size-2 shrink-0 ${
          healthy === null
            ? "bg-muted"
            : healthy
              ? "bg-brand-grass-green"
              : "bg-brand-danger-red"
        }`}
      />
      <div className="flex gap-5 text-sm text-muted-foreground">
        <StatusItem label="Env" value={stats?.environment ?? "—"} />
        <StatusItem label="Generation" value={stats?.generation ?? 0} />
        <StatusItem
          label="Fish"
          value={stats ? `${stats.fishAlive}/${stats.population}` : "—"}
        />
        <StatusItem label="Prey" value={stats?.preyAlive ?? "—"} />
        <StatusItem label="Step" value={stats?.step ?? "—"} />
        <StatusItem label="Seed" value={stats?.seed ?? "—"} />
      </div>
      {/* 导演线（`交互与可视化.md` §1）：尾随右对齐，不挤压左侧统计。 */}
      <div className="ml-auto">
        <JourneyBar />
      </div>
    </header>
  );
}

/** 顶栏统计项的中文（悬停提示；顶栏空间有限，不铺开显示）。 */
const STATUS_ZH: Record<string, string> = {
  Env: "环境",
  Generation: "世代",
  Fish: "存活鱼 / 总数",
  Prey: "剩余猎物",
  Step: "仿真步",
  Seed: "主种子",
};

function StatusItem({ label, value }: { label: string; value: string | number }) {
  return (
    <span title={`${label}：${STATUS_ZH[label] ?? ""}`}>
      {label} <span className="font-mono text-foreground">{value}</span>
    </span>
  );
}
