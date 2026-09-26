import { create } from "zustand";

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
  setSelectedFish: (id: string | null) => void;
  setRunning: (v: boolean) => void;
  setSessionId: (id: string | null) => void;
  setStats: (s: ArenaStats | null) => void;
  toggleRunning: () => void;
  bumpReset: () => void;
}

export const useUiStore = create<UiState>((set) => ({
  running: false,
  sessionId: null,
  selectedFishId: null,
  resetNonce: 0,
  stats: null,
  setSelectedFish: (selectedFishId) => set({ selectedFishId }),
  setRunning: (running) => set({ running }),
  setSessionId: (sessionId) => set({ sessionId }),
  setStats: (stats) => set({ stats }),
  toggleRunning: () => set((state) => ({ running: !state.running })),
  bumpReset: () => set((state) => ({ resetNonce: state.resetNonce + 1, selectedFishId: null })),
}));
