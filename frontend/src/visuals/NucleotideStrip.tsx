import { cn } from "@/lib/utils";
import { STRIP } from "@/design/palette";

/* ===========================================================================
   Nucleotide strip —— 用**真实数据**渲染 A/C/G/T。

   类型口径（必须写清，避免"悄悄新增契约"）：
     契约 owner 是 frontend/types.ts:1 的
         export type Base = "A" | "C" | "G" | "T";
     但该文件当前**不在** tsconfig.app.json 的 include 内（include 只有 ["src"]，
     而 types.ts 在 frontend/ 根下），且全库没有任何文件 import 它。
     故此处**镜像**同一个字面量联合，**不 import、不新增契约**。
     若将来 types.ts 移入 src/，本文件应改为
         import type { Base } from "../types";
     并删除下面这个镜像。

   数据来源现状（**不要为了好看去造数据**）：
     当前前端**没有**碱基序列的真实来源。GET /v1/sessions/{id}/snapshot 的响应
     不含 genotype / chromosome / sequence 字段（见 frontend/src/api/arena.ts 的
     ArenaSnapshot 类型；research/notes/前端驱动-API实现清单.md 记录了这一取捨）。
     因此在后端补上该字段之前，本组件在调用方不传 sequence 时会**一直**显示
     未初始化状态 —— 这是刻意的，不是遗漏。

   颜色：全部取自 @/design/palette 的 STRIP，本文件**没有**任何 hex 字面量。
   =========================================================================== */

type Base = "A" | "C" | "G" | "T";

/** 四色的唯一映射表；查表比 switch 更难写漏。 */
const BASE_FILL: Record<Base, string> = {
  A: STRIP.A,
  C: STRIP.C,
  G: STRIP.G,
  T: STRIP.T,
};

/** 默认最多渲染多少格（超出部分以 +N 提示，而不是静默丢掉）。 */
const DEFAULT_MAX_BASES = 48;

/**
 * 只把**精确的**大写 A/C/G/T 当作已知碱基。
 * 刻意**不做** toUpperCase() 之类的"清洗"：真实数据长什么样就渲染什么样，
 * 未知字符（N、小写、'-' 等）原样显示并走 idle 色，不静默改写后端数据。
 */
function isBase(ch: string): ch is Base {
  return ch === "A" || ch === "C" || ch === "G" || ch === "T";
}

export interface NucleotideStripProps {
  /** 真实碱基串。缺省 = 未初始化（不会生成随机序列冒充数据）。 */
  sequence?: string;
  /** 高亮第 i 格（0-based） */
  selectedPosition?: number;
  /** 有回调才可点：点击第 i 格时调用 */
  onSelectPosition?: (index: number) => void;
  maxBases?: number;
}

export function NucleotideStrip({
  sequence,
  selectedPosition,
  onSelectPosition,
  maxBases = DEFAULT_MAX_BASES,
}: NucleotideStripProps) {
  const bases = sequence ? sequence.split("") : [];

  /* --- 未初始化：一行 muted 文字，绝不编造序列 --- */
  if (bases.length === 0) {
    return (
      <div
        // 不写 h-full：未初始化态只占一行的高度，别把面板撑成一大块空底色。
        className="flex w-full items-center overflow-hidden px-2 py-2"
        style={{ backgroundColor: STRIP.band }}
      >
        {/* **刻意不写 font-mono**：JetBrains Mono 不含 CJK 字形，中文会回退到
            系统字体，`font-mono` 在这里是"看着像有效、其实没生效"的误导写法。
            文本口径（§14 Q4）：数值走等宽，**中文叙述走默认字体**。 */}
        <span className="text-xs text-muted-foreground">等待后端提供碱基序列</span>
      </div>
    );
  }

  const limit = Math.max(0, Math.floor(maxBases));
  const shown = bases.slice(0, limit);
  const hidden = bases.length - shown.length;
  const clickable = typeof onSelectPosition === "function";

  return (
    <div
      // 同样不写 h-full：条带按内容长高（上限由面板那一格给），
      // max-h-full 保证碱基再多也只在自己那一格里被裁切，不会挤掉别的面板内容。
      className="flex max-h-full w-full flex-wrap content-start gap-px overflow-hidden p-1"
      style={{ backgroundColor: STRIP.band }}
    >
      {shown.map((ch, i) => {
        const known = isBase(ch);
        const selected = i === selectedPosition;
        return (
          <button
            key={i}
            type="button"
            disabled={!clickable}
            onClick={clickable ? () => onSelectPosition?.(i) : undefined}
            className={cn(
              // size-5 = 20x20 的方格；本项目无圆角（R2-4），格子上不加任何圆角类。
              "flex size-5 shrink-0 items-center justify-center font-mono text-[10px] leading-none",
              clickable ? "cursor-pointer" : "cursor-default",
            )}
            style={{
              // 已知碱基：四色填充 + 条带底作字色（四色都偏亮，深字对比够）。
              // 未知字符：不打四色，退回条带底 + idle 字色，保持"未知"可辨。
              backgroundColor: known ? BASE_FILL[ch] : STRIP.band,
              color: known ? STRIP.band : STRIP.idle,
              // 选中态用 outline 而不是 border：outline 不参与布局，不会让格子尺寸跳动。
              // 也不用 box-shadow（本项目禁用）。内缩 2px 让描边落在格子内侧。
              outline: selected ? "2px solid" : "none",
              outlineColor: selected ? STRIP.selected : undefined,
              outlineOffset: -2,
            }}
          >
            {ch}
          </button>
        );
      })}
      {hidden > 0 && (
        <span
          className="flex size-5 shrink-0 items-center justify-center font-mono text-[10px] leading-none"
          style={{ color: STRIP.idle }}
        >
          +{hidden}
        </span>
      )}
    </div>
  );
}
