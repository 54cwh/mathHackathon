"""genome 布局参数的漂移守护与注入测试。

契约：取值 owner 为 ``configs/default_model.yaml`` 的 ``genome`` 节（依据状态见
``docs/参数总表.json`` group=genome）。``GenomeLayout`` 的默认值只是该冻结配置的镜像，
此处断言二者逐字段一致，防止单边漂移。
"""

from pathlib import Path

import numpy as np
import pytest
import yaml

from evogenesis.genome import genome as G
from evogenesis.genome.config import (
    DEFAULT_LAYOUT,
    DEFAULT_MODEL_CONFIG_PATH,
    GenomeLayout,
    load_genome_config,
)

FIELDS = (
    "chromosome_pairs",
    "bp_per_haplotype_chromosome",
    "alphabet",
    "motif_count",
    "motif_length",
    "motif_topk",
    "motif_subset_A",
    "motif_subset_B",
)


def _yaml_genome_section() -> dict:
    assert DEFAULT_MODEL_CONFIG_PATH.is_file(), DEFAULT_MODEL_CONFIG_PATH
    data = yaml.safe_load(Path(DEFAULT_MODEL_CONFIG_PATH).read_text(encoding="utf-8"))
    return data["genome"]


def test_default_layout_mirrors_frozen_config():
    section = _yaml_genome_section()
    for name in FIELDS:
        expected = tuple(section[name]) if name == "alphabet" else section[name]
        assert getattr(DEFAULT_LAYOUT, name) == expected, name


def test_load_genome_config_reads_default_path():
    assert load_genome_config() == DEFAULT_LAYOUT


def test_load_genome_config_applies_overrides():
    layout = load_genome_config(overrides={"genome": {"motif_topk": 5}})
    assert layout.motif_topk == 5
    assert layout.bp_per_haplotype_chromosome == DEFAULT_LAYOUT.bp_per_haplotype_chromosome


def test_load_genome_config_none_returns_mirror():
    assert load_genome_config(None) == GenomeLayout()


def test_layout_derived_diploid_sizes():
    assert DEFAULT_LAYOUT.haploid_bp == 256
    assert DEFAULT_LAYOUT.diploid_bp == 512


def test_injected_layout_drives_validation():
    short = GenomeLayout(bp_per_haplotype_chromosome=64, chromosome_pairs=1)
    pair = G.ChromosomePair("A" * 64, "C" * 64, layout=short)
    assert pair.maternal == "A" * 64
    with pytest.raises(ValueError):
        G.ChromosomePair("A" * 128, "C" * 128, layout=short)
    with pytest.raises(ValueError):
        G.DiploidGenome((pair, pair), layout=short)


def test_injected_layout_drives_motif_topk():
    layout = GenomeLayout(motif_topk=1)
    values = G.window_affinities("A" * 128, "A" * 6)
    assert G.chain_affinity("A" * 128, "A" * 6, layout=layout) == G.top_k_mean(values, 1)


SHORT = GenomeLayout(
    bp_per_haplotype_chromosome=8,
    chromosome_pairs=2,
    motif_count=8,
    motif_length=2,
    motif_topk=1,
    motif_subset_A=3,
    motif_subset_B=5,
)


def test_injected_layout_haploid_bp_uses_layout():
    assert SHORT.haploid_bp == 16
    assert SHORT.diploid_bp == 32


def test_injected_layout_end_to_end():
    pair = G.ChromosomePair("ACGTACGT", "ACGTACGT", layout=SHORT)
    genome = G.DiploidGenome((pair, pair), genome_id="g-0001", layout=SHORT)
    assert genome.haploid_bp == 16

    payload = {
        "genome_id": "g-0001",
        "chromosome_pairs": [
            {"maternal": "ACGTACGT", "paternal": "ACGTACGT"},
            {"maternal": "ACGTACGT", "paternal": "ACGTACGT"},
        ],
    }
    assert G.DiploidGenome.from_dict(payload, layout=SHORT) == genome

    child = G.fertilize(("ACGTACGT", "ACGTACGT"), ("ACGTACGT", "ACGTACGT"), layout=SHORT)
    assert child.haploid_bp == 16
    with pytest.raises(ValueError):
        G.fertilize(("ACGTACGT",), ("ACGTACGT",), layout=SHORT)


def test_injected_alphabet_drives_mutation():
    tiny = GenomeLayout(
        alphabet=("A", "C"),
        bp_per_haplotype_chromosome=4,
        chromosome_pairs=1,
        motif_count=2,
        motif_length=2,
        motif_topk=1,
        motif_subset_A=0,
        motif_subset_B=1,
    )
    mutated = G.mutate_sequence("AAAA", 1.0, np.random.default_rng(0), layout=tiny)
    assert set(mutated) == {"C"}


def test_motif_subset_wired_into_expression():
    catalog = ["GG", "GG", "GG", "AA", "GG", "CC", "GG", "GG"]
    pair_a = G.ChromosomePair("AAGGGGGG", "AAGGGGGG", layout=SHORT)
    pair_b = G.ChromosomePair("CCGGGGGG", "CCGGGGGG", layout=SHORT)
    genome = G.DiploidGenome((pair_a, pair_b), genome_id="g-0001", layout=SHORT)
    assert DEFAULT_LAYOUT.motif_subset("A") == (0,)
    assert DEFAULT_LAYOUT.motif_subset("B") == (1,)
    assert SHORT.motif_subset("A") == (3,)
    assert SHORT.motif_subset("B") == (5,)
    assert G.expression_A(genome, catalog) == pytest.approx(1.0)
    assert G.expression_A(genome, catalog, (3,)) == pytest.approx(1.0)
    assert G.expression_B(genome, catalog) == pytest.approx(1.0)


def test_layout_rejects_invalid_motif_subset():
    with pytest.raises(ValueError):
        GenomeLayout(motif_subset_A=8, motif_subset_B=1)
    with pytest.raises(ValueError):
        GenomeLayout(motif_subset_A=1, motif_subset_B=1)


TINY = GenomeLayout(
    alphabet=("A", "C"),
    bp_per_haplotype_chromosome=4,
    chromosome_pairs=1,
    motif_count=2,
    motif_length=2,
    motif_topk=1,
    motif_subset_A=0,
    motif_subset_B=1,
)


def test_make_gamete_defaults_to_genome_layout():
    pair = G.ChromosomePair("ACAC", "CACA", layout=TINY)
    genome = G.DiploidGenome((pair,), genome_id="g-0001", layout=TINY)
    gamete = G.make_gamete(
        genome,
        mu=1.0,
        crossover_probability=0.0,
        crossover_rng=np.random.default_rng(0),
        mutation_rng=np.random.default_rng(1),
    )
    assert set("".join(gamete)) <= set(TINY.alphabet)


def test_from_dict_rejects_empty_genome_id():
    payload = {
        "genome_id": "",
        "chromosome_pairs": [
            {"maternal": "ACGTACGT", "paternal": "ACGTACGT"},
            {"maternal": "ACGTACGT", "paternal": "ACGTACGT"},
        ],
    }
    with pytest.raises(ValueError):
        G.DiploidGenome.from_dict(payload, layout=SHORT)


def test_mutate_sequence_requires_two_symbol_alphabet():
    single = GenomeLayout(
        alphabet=("A",),
        bp_per_haplotype_chromosome=4,
        chromosome_pairs=1,
        motif_count=2,
        motif_length=2,
        motif_topk=1,
        motif_subset_A=0,
        motif_subset_B=1,
    )
    with pytest.raises(ValueError):
        G.mutate_sequence("AAAA", 1.0, np.random.default_rng(0), layout=single)
