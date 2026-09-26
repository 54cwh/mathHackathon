import { useEffect } from "react";
import { ChevronRight, Play, Square } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  JOURNEY_STAGES,
  STAGE_COUNT,
  isStageReady,
  useUiStore,
  type JourneyStage,
} from "@/store/ui";

/**
 * 导演线（`交互与可视化.md` §1 状态机表）：六段进度条 + 单一「下一步」+ AUTO DEMO。
 *
 * 口径：
 *  - **前端门控**：`isStageReady(state, 目标段)` 为 `false` 时「下一步」不可点（title 说明缺口）。
 *  - 点击 = `requestIntent(目标段)`：置 `journey` 并自增 `intent.nonce`，由该段面板执行动作。
 *  - **AUTO DEMO**：定时循环「下一步」；目标段门控未通过即**停在该段**（`autoPlay=false`），不跳段。
 *
 * 样式：英文段名走 `.font-pixel`；无圆角/无过渡/无投影（`视觉规范审计.md` 规则 4/§十一）。
 */

const LABELS: Record<JourneyStage, string> = {
  seed: "SEED",
  genome: "GENOME",
  develop: "DEVELOP",
  arena: "ARENA",
  evolve: "EVOLVE",
  compare: "COMPARE",
};

/** AUTO DEMO 每步间隔：给面板留出执行动作的时间。 */
const AUTO_DEMO_MS = 1200;

/** 目标段未就绪时展示的缺口提示（与 `isStageReady` 一一对应）。 */
const GATE_HINT: Record<JourneyStage, string> = {
  seed: "",
  genome: "",
  develop: "需要先有基因组（Lab）",
  arena: "需要先产出发育结果（DEVELOP）",
  evolve: "需要 Arena 已有会话与个体",
  compare: "需要先推进一代（P4 落地）",
};

export function JourneyBar() {
  const journey = useUiStore((s) => s.journey);
  const requestIntent = useUiStore((s) => s.requestIntent);
  const autoPlay = useUiStore((s) => s.autoPlay);
  const setAutoPlay = useUiStore((s) => s.setAutoPlay);
  const activeGenomeId = useUiStore((s) => s.activeGenomeId);
  const development = useUiStore((s) => s.development);
  const sessionId = useUiStore((s) => s.sessionId);
  const individuals = useUiStore((s) => s.individuals);
  const generation = useUiStore((s) => s.generation);

  const index = JOURNEY_STAGES.indexOf(journey);
  const next = index < STAGE_COUNT - 1 ? JOURNEY_STAGES[index + 1] : null;
  const nextReady =
    next !== null && isStageReady({ activeGenomeId, development, sessionId, individuals, generation }, next);

  // AUTO DEMO：门控未过即停，不跳段。
  useEffect(() => {
    if (!autoPlay) return;
    if (next === null) {
      setAutoPlay(false);
      return;
    }
    if (!nextReady) {
      setAutoPlay(false);
      return;
    }
    const timer = window.setTimeout(() => requestIntent(next), AUTO_DEMO_MS);
    return () => window.clearTimeout(timer);
  }, [autoPlay, next, nextReady, requestIntent, setAutoPlay]);

  return (
    <div className="flex items-center gap-2">
      <div
        role="list"
        aria-label="Demo journey"
        className="flex items-stretch divide-x divide-border border border-border"
      >
        {JOURNEY_STAGES.map((stage, i) => {
          const state = i === index ? "active" : i < index ? "done" : "locked";
          return (
            <span
              key={stage}
              role="listitem"
              aria-current={state === "active" ? "step" : undefined}
              className={cn(
                "px-2 py-1 font-pixel text-[10px] leading-none",
                state === "active" && "bg-brand-fish-navy text-brand-bone",
                state === "done" && "bg-card text-foreground",
                state === "locked" && "bg-muted text-muted-foreground",
              )}
            >
              {LABELS[stage]}
            </span>
          );
        })}
      </div>

      <button
        type="button"
        disabled={!nextReady}
        title={next === null ? "已是末段" : nextReady ? `进入 ${LABELS[next]}` : GATE_HINT[next]}
        onClick={() => next && requestIntent(next)}
        className={cn(
          "inline-flex items-center gap-1 border border-border px-2 py-1 font-pixel text-[10px] leading-none",
          nextReady
            ? "bg-card text-foreground hover:bg-brand-slate-shadow hover:text-brand-bone"
            : "bg-muted text-muted-foreground",
        )}
      >
        Next <ChevronRight className="size-3" />
      </button>

      <button
        type="button"
        aria-pressed={autoPlay}
        title="AUTO DEMO：自动推进到门控未通过的段为止"
        onClick={() => setAutoPlay(!autoPlay)}
        className={cn(
          "inline-flex items-center gap-1 border border-border px-2 py-1 font-pixel text-[10px] leading-none",
          autoPlay
            ? "bg-brand-fish-navy text-brand-bone"
            : "bg-card text-foreground hover:bg-brand-slate-shadow hover:text-brand-bone",
        )}
      >
        {autoPlay ? <Square className="size-3" /> : <Play className="size-3" />}
        Auto
      </button>
    </div>
  );
}
