import { create } from "zustand";

interface UiState {
  running: boolean;
  selectedFishId: string | null;
  setSelectedFish: (id: string | null) => void;
  toggleRunning: () => void;
  reset: () => void;
}

export const useUiStore = create<UiState>((set) => ({
  running: false,
  selectedFishId: null,
  setSelectedFish: (selectedFishId) => set({ selectedFishId }),
  toggleRunning: () => set((state) => ({ running: !state.running })),
  reset: () => set({ running: false, selectedFishId: null }),
}));
