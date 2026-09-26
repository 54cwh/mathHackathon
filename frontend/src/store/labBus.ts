/**
 * DNA 实验室 → Brain Forge 的**进程内总线**（前端本地，无网络）。
 *
 * 为什么需要它：`交互与可视化.md` §4 要求 Brain Forge 显示「来自真实模型状态」的中间量，
 * 而这些量由 DNA2Brain 面板的 `POST /v1/developments` 产出（`dev_trace`：q、六类计数、
 * τ、n_neurons/n_edges）。两个面板是同级的，故用模块级总线传递，避免把大对象塞进 zustand
 * （README 防坑 3：低频摘要才进 store）。
 *
 * 契约：§4 的中间量。2026-09-27 起后端 `POST /v1/developments?with_trace=true` 提供
 * **逐阶段轨迹**（GRN 逐步 → 增殖 → 连接组，`API接口.md` §2.3），故总线同时承载
 * `trace`（过程）与 `result`（终态）。
 */

import type { DevelopmentResult, DevelopmentTraceSample } from "@/api/types";

export interface LabDevelopment {
  genomeId: string | null;
  result: DevelopmentResult | null;
  /** 发育轨迹（`API接口.md` §2.3）；`null` = 未请求 / 尚未发育。 */
  trace: DevelopmentTraceSample[] | null;
  /** 发布序号：订阅方据此判断"是新的一次发育"。 */
  seq: number;
}

let latest: LabDevelopment = { genomeId: null, result: null, trace: null, seq: 0 };
const listeners = new Set<(payload: LabDevelopment) => void>();

export function publishDevelopment(
  genomeId: string | null,
  result: DevelopmentResult | null,
  trace: DevelopmentTraceSample[] | null = null,
): void {
  latest = { genomeId, result, trace, seq: latest.seq + 1 };
  for (const listener of listeners) listener(latest);
}

export function getLatestDevelopment(): LabDevelopment {
  return latest;
}

export function subscribeDevelopment(listener: (payload: LabDevelopment) => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

// --- 焦点：Arena 点鱼 -> Lab 载入该个体（`交互与可视化.md` §15.6 三栏联动） --------

type FocusListener = (genomeId: string) => void;
const focusListeners = new Set<FocusListener>();

/** 请求把某个实验室个体载入 DNA2Brain Lab（由 Arena 面板在点选实验室鱼时调用）。 */
export function focusGenome(genomeId: string): void {
  for (const listener of focusListeners) listener(genomeId);
}

export function subscribeFocus(listener: FocusListener): () => void {
  focusListeners.add(listener);
  return () => focusListeners.delete(listener);
}
