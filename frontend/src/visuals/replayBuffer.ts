/**
 * 会话回放缓冲（Playback 视图的数据源）。
 *
 * 状态放在**模块级**而非 store：数据以 ~10Hz 增长，进 React state/store 会把
 * 20Hz 热路径塞进渲染（`frontend/README.md` 防坑 3）。Playback 视图只在自己
 * 的播放循环里读它。
 *
 * 语义状态：**草案待确认（2026-09-27）**——「回放本次会话」是前端本地功能，
 * 上限 600 帧 ≈ 1 个 episode（`arena` 默认 `episode_steps=600`）。上游未定义
 * Playback 的正式契约；若将来改为回放 `behavior_trace` 资产（后端端点就绪后），
 * 本模块是唯一替换点。
 */

import type { ArenaScene } from "@/visuals/ArenaScene";

/** 缓冲上限：600 帧 ≈ 600 步（`ArenaConfig.episode_steps` 默认值）。 */
export const REPLAY_CAPACITY = 600;

const frames: ArenaScene[] = [];

/** 追加一帧；超容量丢最旧（环形语义，用数组 shift 实现，容量小、代价可忽略）。 */
export function pushFrame(scene: ArenaScene): void {
  frames.push(scene);
  if (frames.length > REPLAY_CAPACITY) frames.shift();
}

/** 会话切换/重置时清空。 */
export function clearFrames(): void {
  frames.length = 0;
}

export function frameCount(): number {
  return frames.length;
}

/** 只读快照（按 index 取帧；index 越界返回 undefined）。 */
export function getFrame(index: number): ArenaScene | undefined {
  return frames[index];
}

/** 最新一帧（无则 undefined）。 */
export function latestFrame(): ArenaScene | undefined {
  return frames.length ? frames[frames.length - 1] : undefined;
}
