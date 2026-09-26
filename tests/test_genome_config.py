"""genome 布局参数的漂移守护与注入测试。

契约：取值 owner 为 ``configs/default_model.yaml`` 的 ``genome`` 节（依据状态见
``docs/参数总表.json`` group=genome）。``GenomeLayout`` 的默认值只是该冻结配置的镜像，
此处断言二者逐字段一致，防止单边漂移。
"""

from pathlib import Path

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
    "motif_window",
    "motif_topk",
    "motif_scan_scope",
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
