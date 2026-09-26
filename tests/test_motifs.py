"""motif 目录：固定、均匀 i.i.d.、可复现（genome §6）。"""

from evogenesis.core.seed import SeedManager
from evogenesis.genome.config import GenomeLayout
from evogenesis.genome.motifs import generate_motif_catalog, motif_catalog_for

MASTER_SEED = 250927


def test_catalog_shape_and_alphabet():
    layout = GenomeLayout()
    catalog = motif_catalog_for(MASTER_SEED, layout)
    assert len(catalog) == layout.motif_count
    assert all(len(motif) == layout.motif_length for motif in catalog)
    assert all(set(motif) <= set(layout.alphabet) for motif in catalog)


def test_catalog_reproducible_by_seed():
    assert motif_catalog_for(MASTER_SEED) == motif_catalog_for(MASTER_SEED)
    assert motif_catalog_for(MASTER_SEED) != motif_catalog_for(MASTER_SEED + 1)


def test_catalog_uses_given_layout():
    layout = GenomeLayout(motif_count=4, motif_length=3)
    catalog = generate_motif_catalog(layout, rng=SeedManager(7).rng("motif_catalog"))
    assert len(catalog) == 4
    assert all(len(motif) == 3 for motif in catalog)


def test_catalog_positions_cover_alphabet():
    layout = GenomeLayout(motif_count=8, motif_length=6)
    rng = SeedManager(MASTER_SEED).rng("motif_catalog")
    seen = set()
    for _ in range(200):
        for motif in generate_motif_catalog(layout, rng=rng):
            seen.update(motif)
    assert seen == set(layout.alphabet)
