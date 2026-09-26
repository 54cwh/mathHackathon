import { create } from "zustand";

export interface ArenaStats {
  generation: number;
  population: number;
  fishAlive: number;
  preyAlive: number;
  seed: number;
  step: number;
}

/** Bottom-bar view tabs (`交互与可视化.md` §1; `视觉规范审计.md` rule 8). */
export type ViewId = "evolution" | "experiment" | "playback";

interface UiState {
  running: boolean;
  sessionId: string | null;
  selectedFishId: string | null;
  resetNonce: number;
  stats: ArenaStats | null;
  activeView: ViewId;
  setSelectedFish: (id: string | null) => void;
  setRunning: (v: boolean) => void;
  setSessionId: (id: string | null) => void;
  setStats: (s: ArenaStats | null) => void;
  setActiveView: (v: ViewId) => void;
  toggleRunning: () => void;
  bumpReset: () => void;
}

export const useUiStore = create<UiState>((set) => ({
  running: false,
  sessionId: null,
  selectedFishId: null,
  resetNonce: 0,
  stats: null,
  /** 默认 Experiment 激活（§二 item 12）。*/
  activeView: "experiment",
  setSelectedFish: (selectedFishId) => set({ selectedFishId }),
  setRunning: (running) => set({ running }),
  setSessionId: (sessionId) => set({ sessionId }),
  setStats: (stats) => set({ stats }),
  setActiveView: (activeView) => set({ activeView }),
  toggleRunning: () => set((state) => ({ running: !state.running })),
  bumpReset: () => set((state) => ({ resetNonce: state.resetNonce + 1, selectedFishId: null })),
}));
