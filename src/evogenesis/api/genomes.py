"""基因组侧端点（`API接口.md` §2.3，批 A）。

`POST /v1/genomes` 创建一个随机基因组；`GET /v1/genomes/{genome_id}` 取回；
`POST /v1/genomes/{id}/mutations` 单点 Free Edit；`POST /v1/developments` 发育；
`POST /v1/breedings` 繁殖。store 与基因组原语见 `genome_lab.py`（**草案待确认**）。

另两条（`story-mutations`、`sessions/{id}/evolutions`）判据/语义未定义，仍 501（§2.1）。
"""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, HTTPException

from evogenesis.api import genome_lab as lab
from evogenesis.api.schemas import (
    BreedingRequest,
    BreedingResult,
    DevelopmentRequest,
    DevelopmentResult,
    GenomeCreate,
    GenomeRecord,
    MutationRequest,
    MutationResult,
    Problem,
)
from evogenesis.evolution.config import load_evolution_config
from evogenesis.pipeline import phenotype_of

router = APIRouter(
    prefix="/v1",
    responses={404: {"model": Problem, "description": "基因组不存在"}},
)


def _record(genome) -> GenomeRecord:
    data = genome.to_dict()
    return GenomeRecord(
        genome_id=data["genome_id"],
        chromosome_pairs=data["chromosome_pairs"],
        lineage=lab.lineage(genome.genome_id),
    )


def _get(genome_id: str):
    genome = lab.get(genome_id)
    if genome is None:
        raise HTTPException(status_code=404, detail=f"genome {genome_id} not found")
    return genome


@router.post("/genomes", status_code=201, response_model=GenomeRecord)
def create_genome(req: GenomeCreate) -> GenomeRecord:
    return _record(lab.create(req.seed))


@router.get("/genomes/{genome_id}", response_model=GenomeRecord)
def get_genome(genome_id: str) -> GenomeRecord:
    return _record(_get(genome_id))


@router.post("/genomes/{genome_id}/mutations", status_code=201, response_model=MutationResult)
def mutate_genome(genome_id: str, req: MutationRequest) -> MutationResult:
    genome = _get(genome_id)
    try:
        from_base = lab.base_at(genome, req.position)
        child = lab.mutate_at_site(genome, req.position, req.base)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return MutationResult(
        genome_id=genome_id,
        new_genome_id=child.genome_id,
        diff={"position": req.position, "from_base": from_base, "to_base": req.base},
    )


@router.post("/developments", response_model=DevelopmentResult)
def develop(req: DevelopmentRequest) -> DevelopmentResult:
    genome = _get(req.genome_id)
    phenotype = phenotype_of(
        genome,
        lab.motifs(),
        master_seed=req.seed,
        index=lab.stable_index(req.genome_id),
    )
    active = phenotype.active_mask.bool()
    adjacency = phenotype.adjacency
    tau = phenotype.tau.float()
    n_neurons = int(active.sum())
    n_edges = int((adjacency != 0).sum())
    tau_active = tau[active] if bool(active.any()) else tau
    cell_counts = Counter(int(value) for value in phenotype.cell_type.reshape(-1).tolist())
    summary = {
        "n_neurons": n_neurons,
        "n_edges": n_edges,
        "edge_density": (n_edges / (n_neurons * n_neurons)) if n_neurons else 0.0,
        "tau_mean": float(tau_active.mean()) if tau_active.numel() else 0.0,
        "tau_std": float(tau_active.std(unbiased=False)) if tau_active.numel() else 0.0,
        "viable": bool(phenotype.viable),
    }
    trace = {
        "q": [float(value) for value in lab.affinity(genome)],
        "cell_type_counts": {str(i): int(c) for i, c in enumerate(cell_counts)},
        "tau": {"mean": summary["tau_mean"], "std": summary["tau_std"]},
        "n_neurons": n_neurons,
        "n_edges": n_edges,
        "viable": bool(phenotype.viable),
        "viability_reason": phenotype.viability_reason,
    }
    return DevelopmentResult(genome_id=req.genome_id, dev_trace=trace, phenotype=summary)


@router.post("/breedings", status_code=201, response_model=BreedingResult)
def breed(req: BreedingRequest) -> BreedingResult:
    parent_a = _get(req.genome_a)
    parent_b = _get(req.genome_b)
    if req.n_offspring < 1:
        raise HTTPException(status_code=422, detail="n_offspring 须 ≥ 1")
    config = load_evolution_config()
    offspring = lab.breed(
        parent_a,
        parent_b,
        n_offspring=req.n_offspring,
        mu=config.mutation_rate_per_base_per_gamete,
        crossover_probability=config.crossover_probability_per_chromosome,
    )
    return BreedingResult(
        offspring=[child.genome_id for child in offspring],
        meiosis_trace={
            "n_offspring": len(offspring),
            "mu": config.mutation_rate_per_base_per_gamete,
            "crossover_probability": config.crossover_probability_per_chromosome,
        },
    )
