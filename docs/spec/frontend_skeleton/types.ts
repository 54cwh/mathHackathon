export type Base = "A" | "C" | "G" | "T";
export interface ChromosomePair { maternal: string; paternal: string; }
export interface DiploidGenome {
  genome_id: string;
  chromosome_pairs: [ChromosomePair, ChromosomePair];
}
export type CellType = "sensory"|"prey"|"threat"|"memory"|"inhibitory"|"motor";
export interface FishSummary {
  fish_id: string;
  generation: number;
  genome_id: string;
  viable: boolean;
  fitness: number|null;
  energy: number;
  size: number;
  cell_counts: Record<CellType, number>;
}
export interface MutationRequest {
  genome: DiploidGenome;
  chromosome: 0|1;
  homolog: "maternal"|"paternal";
  position: number;
  new_base: Base;
}
export interface MotorAction { omega: number; speed: number; }
