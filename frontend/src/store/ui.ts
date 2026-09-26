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
export type JourneyStage = "seed" | "genome" | "develop" | "arena" | "evolve" | "compare";

/** 导演线的固定顺序：唯一的推进依据（不在面板里另写一份）。 */
export const JOURNEY_STAGES: readonly JourneyStage[] = [
  "seed",
  "genome",
  "develop",
  "arena",
  "evolve",
  "compare",
];

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
  development: LabDevelopment | null;
  individuals: SpawnedIndividual[];
  /** 焦点事件计数；`focusGenome()` 自增，使"同一个体再点一次"也能被订阅到。 */
  focusNonce: number;
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
  publishDevelopment: (
    genomeId: string | null,
    result: DevelopmentResult | null,
    trace?: DevelopmentTraceSample[] | null,
  ) => void;
  addIndividual: (individual: SpawnedIndividual) => void;
  focusGenome: (genomeId: string) => void;
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
  development: null,
  individuals: [],
  focusNonce: 0,
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
  focusGenome: (genomeId) =>
    set((state) => ({ activeGenomeId: genomeId, focusNonce: state.focusNonce + 1 })),
  resetJourney: () =>
    set({
      journey: "seed",
      activeGenomeId: null,
      activeIndividual: null,
      activeRunId: null,
      generation: 0,
      development: null,
    }),
}));
