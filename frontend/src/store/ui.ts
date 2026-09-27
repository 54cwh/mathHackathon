import { create } from "zustand";

import type { DevelopmentResult, DevelopmentTraceSample, SpawnedIndividual } from "@/api/types";

export interface ArenaStats {
  /** 会话摘要里的 `environment`（`API接口.md` §1.2）；顶栏 Env 由它渲染。 */
  environment: string;
  generation: number;
  population: number;
  fishAlive: number;
  preyAlive: number;
  seed: number;
  step: number;
}

/** Bottom-bar view tabs (`交互与可视化.md` §1; `视觉规范审计.md` rule 8). */
export type ViewId = "evolution" | "experiment" | "playback";

/** 演示流程段（`交互与可视化.md` §1 导演线；`通用层接口.md` §7）。 */
export type JourneyStage = "seed" | "genome" | "develop" | "arena" | "evolve";

/** 导演线的固定顺序：唯一的推进依据（不在面板里另写一份）。 */
export const JOURNEY_STAGES: readonly JourneyStage[] = [
  "seed",
  "genome",
  "develop",
  "arena",
  "evolve",
];

/** 导演线段数。 */
export const STAGE_COUNT = JOURNEY_STAGES.length;

/** 门控判据所依赖的最小状态切片（`交互与可视化.md` §1 状态机表）。 */
export interface JourneyGateState {
  activeGenomeId: string | null;
  development: LabDevelopment | null;
  sessionId: string | null;
  individuals: SpawnedIndividual[];
  generation: number;
}

/**
 * 某段能否进入（前端门控，`交互与可视化.md` §1）。
 *
 * 「下一步」只在**目标段**返回 `true` 时可点；`seed`/`genome` 无前置依赖。
 */
export function isStageReady(state: JourneyGateState, stage: JourneyStage): boolean {
  switch (stage) {
    case "seed":
    case "genome":
      return true;
    case "develop":
      return state.activeGenomeId !== null;
    case "arena":
      return state.development?.result != null;
    case "evolve":
      return state.sessionId !== null && state.individuals.length > 0;
  }
}

/** 最近一次发育产物（DNA2Brain Lab 产出 → Brain Forge 消费；`API接口.md` §2.3）。 */
export interface LabDevelopment {
  genomeId: string | null;
  result: DevelopmentResult | null;
  trace: DevelopmentTraceSample[] | null;
  /** 发布序号：订阅方据此判断"是新的一次发育"。 */
  seq: number;
}

interface UiState {
  // ---- 壳层（shell） -------------------------------------------------------
  running: boolean;
  sessionId: string | null;
  selectedFishId: string | null;
  resetNonce: number;
  stats: ArenaStats | null;
  activeView: ViewId;
  // ---- 领域层（domain）：演示流程与"当前个体" ------------------------------
  journey: JourneyStage;
  activeGenomeId: string | null;
  activeIndividual: SpawnedIndividual | null;
  activeRunId: string | null;
  generation: number;
  /** 会话内演化一步进行中（长请求的"进行中"反馈，`交互与可视化.md` §1）。 */
  evolutionBusy: boolean;
  development: LabDevelopment | null;
  individuals: SpawnedIndividual[];
  /** 焦点事件计数；`focusGenome()` 自增，使"同一个体再点一次"也能被订阅到。 */
  focusNonce: number;
  /** 导演线「下一步」下发的段意图；面板用 ref 去重后执行该段动作。 */
  intent: { stage: JourneyStage; nonce: number } | null;
  /** AUTO DEMO 开关：定时循环「下一步」，门控未通过即停。 */
  autoPlay: boolean;
  /**
   * 步速档（Arena 与 Playback 共用）：直接就是**每 tick 推几步**（tick 间隔 100 ms）。
   * 演示默认 `20`（= 20 步/tick = 200 步/s）。只改前端 `release` 的步数，不改模型时长。
   */
  simSpeed: number;
  // ---- 动作 ---------------------------------------------------------------
  setSelectedFish: (id: string | null) => void;
  setRunning: (v: boolean) => void;
  setSessionId: (id: string | null) => void;
  setStats: (s: ArenaStats | null) => void;
  setActiveView: (v: ViewId) => void;
  toggleRunning: () => void;
  bumpReset: () => void;
  setJourney: (stage: JourneyStage) => void;
  nextStage: () => void;
  prevStage: () => void;
  setActiveGenome: (id: string | null) => void;
  setActiveIndividual: (individual: SpawnedIndividual | null) => void;
  setActiveRun: (id: string | null) => void;
  setGeneration: (generation: number) => void;
  setEvolutionBusy: (v: boolean) => void;
  publishDevelopment: (
    genomeId: string | null,
    result: DevelopmentResult | null,
    trace?: DevelopmentTraceSample[] | null,
  ) => void;
  addIndividual: (individual: SpawnedIndividual) => void;
  setIndividuals: (individuals: SpawnedIndividual[]) => void;
  focusGenome: (genomeId: string) => void;
  requestIntent: (stage: JourneyStage) => void;
  setAutoPlay: (v: boolean) => void;
  setSimSpeed: (v: number) => void;
  resetJourney: () => void;
}

export const useUiStore = create<UiState>((set) => ({
  running: false,
  sessionId: null,
  selectedFishId: null,
  resetNonce: 0,
  stats: null,
  /** 默认 Experiment 激活（§二 item 12）。*/
  activeView: "experiment",
  journey: "seed",
  activeGenomeId: null,
  activeIndividual: null,
  activeRunId: null,
  generation: 0,
  evolutionBusy: false,
  development: null,
  individuals: [],
  focusNonce: 0,
  intent: null,
  autoPlay: false,
  simSpeed: 20,
  setSelectedFish: (selectedFishId) => set({ selectedFishId }),
  setRunning: (running) => set({ running }),
  setSessionId: (sessionId) => set({ sessionId }),
  setStats: (stats) => set({ stats }),
  setActiveView: (activeView) => set({ activeView }),
  toggleRunning: () => set((state) => ({ running: !state.running })),
  bumpReset: () => set((state) => ({ resetNonce: state.resetNonce + 1, selectedFishId: null })),
  setJourney: (journey) => set({ journey }),
  nextStage: () =>
    set((state) => {
      const index = JOURNEY_STAGES.indexOf(state.journey);
      return { journey: JOURNEY_STAGES[Math.min(index + 1, JOURNEY_STAGES.length - 1)] };
    }),
  prevStage: () =>
    set((state) => {
      const index = JOURNEY_STAGES.indexOf(state.journey);
      return { journey: JOURNEY_STAGES[Math.max(index - 1, 0)] };
    }),
  setActiveGenome: (activeGenomeId) => set({ activeGenomeId }),
  setActiveIndividual: (activeIndividual) => set({ activeIndividual }),
  setActiveRun: (activeRunId) => set({ activeRunId }),
  setGeneration: (generation) => set({ generation }),
  setEvolutionBusy: (evolutionBusy) => set({ evolutionBusy }),
  publishDevelopment: (genomeId, result, trace = null) =>
    set((state) => ({
      activeGenomeId: genomeId,
      development: { genomeId, result, trace, seq: (state.development?.seq ?? 0) + 1 },
    })),
  addIndividual: (individual) =>
    set((state) => ({
      activeIndividual: individual,
      individuals: state.individuals.some((it) => it.fish_id === individual.fish_id)
        ? state.individuals.map((it) => (it.fish_id === individual.fish_id ? individual : it))
        : [...state.individuals, individual],
    })),
  setIndividuals: (individuals) => set({ individuals }),
  focusGenome: (genomeId) =>
    set((state) => ({ activeGenomeId: genomeId, focusNonce: state.focusNonce + 1 })),
  requestIntent: (stage) =>
    set((state) => ({ journey: stage, intent: { stage, nonce: (state.intent?.nonce ?? 0) + 1 } })),
  setAutoPlay: (autoPlay) => set({ autoPlay }),
  setSimSpeed: (simSpeed) => set({ simSpeed }),
  resetJourney: () =>
    set({
      journey: "seed",
      activeGenomeId: null,
      activeIndividual: null,
      activeRunId: null,
      generation: 0,
      development: null,
      autoPlay: false,
    }),
}));
