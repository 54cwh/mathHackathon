import { create } from "zustand";

/** 底栏视图档位（§二 item 12）。默认 `experiment`（用户裁决）。 */
export type UiView = "evolution" | "experiment" | "playback";

export interface ArenaStats {
  generation: number;
  population: number;
  fishAlive: number;
  preyAlive: number;
  seed: number;
  step: number;
}

interface UiState {
  running: boolean;
  sessionId: string | null;
  selectedFishId: string | null;
  resetNonce: number;
  stats: ArenaStats | null;
  activeView: UiView;
  setSelectedFish: (id: string | null) => void;
  setRunning: (v: boolean) => void;
  setSessionId: (id: string | null) => void;
  setStats: (s: ArenaStats | null) => void;
  setActiveView: (view: UiView) => void;
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
