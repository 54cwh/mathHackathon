import torch

from evogenesis.core.seed import SeedManager
from evogenesis.development.config import DEFAULT_CONFIG
from evogenesis.development.development import (
    DevelopmentState,
    block_origins,
    cell_identity,
    division_probability,
    place_precursors,
    proliferate,
)


def test_block_origins_tile_unit_square():
    origins = block_origins(DEFAULT_CONFIG.domains)
    assert origins.shape == (6, 2)
    assert origins.dtype == torch.float32
    # 3 列 × 2 行：x ∈ {0, 1/3, 2/3}，y ∈ {0, 1/2}
    assert torch.allclose(
        origins[:, 0].sort().values, torch.tensor([0.0, 0.0, 1 / 3, 1 / 3, 2 / 3, 2 / 3])
    )
    assert torch.allclose(origins[:, 1].sort().values, torch.tensor([0.0, 0.0, 0.0, 0.5, 0.5, 0.5]))


def test_place_precursors_within_their_block():
    gen = SeedManager(7).torch_generator("development", 0)
    positions, domain_index = place_precursors(
        DEFAULT_CONFIG.domains, DEFAULT_CONFIG.precursors_per_domain, generator=gen
    )
    assert positions.shape == (24, 2)
    assert domain_index.shape == (24,)
    assert set(domain_index.tolist()) == set(range(6))
    assert torch.all(positions >= 0.0) and torch.all(positions <= 1.0)

    origins = block_origins(DEFAULT_CONFIG.domains)
    for domain in range(6):
        block = positions[domain_index == domain]
        assert block.shape[0] == DEFAULT_CONFIG.precursors_per_domain
        lower = origins[domain]
        upper = lower + torch.tensor([1.0 / 3.0, 1.0 / 2.0])
        assert torch.all(block >= lower - 1e-6)
        assert torch.all(block <= upper + 1e-6)


def test_division_probability_in_unit_interval():
    gen = SeedManager(3).torch_generator("development", 0)
    grn = torch.randn(10, 8, generator=gen)
    w_div = torch.randn(8, generator=gen)
    b_div = torch.zeros(())
    prob = division_probability(grn, w_div, b_div)
    assert prob.shape == (10,)
    assert torch.all((prob >= 0) & (prob <= 1))


def test_cell_identity_is_softmax():
    gen = SeedManager(4).torch_generator("development", 0)
    grn = torch.randn(9, 8, generator=gen)
    U = torch.randn(6, 8, generator=gen)
    bias = torch.randn(9, 6, generator=gen)
    z = cell_identity(grn, U, bias)
    assert z.shape == (9, 6)
    assert torch.allclose(z.sum(dim=-1), torch.ones(9), atol=1e-5)
    assert torch.all(z >= 0)


def test_proliferate_daughters_perturb_and_bounds():
    gen = SeedManager(5).torch_generator("development", 0)
    grn = torch.zeros(4, 8)
    grn[:, 0] = 100.0  # 分裂概率饱和为 1
    positions = torch.tensor([[0.0, 0.0], [1.0, 1.0], [0.5, 0.5], [0.25, 0.75]])
    domain_index = torch.arange(4)
    state = proliferate(
        grn,
        positions,
        domain_index,
        torch.zeros(8),
        torch.tensor(-100.0),  # 分裂概率 ~0
        split_noise=DEFAULT_CONFIG.split_noise,
        gene_noise=DEFAULT_CONFIG.gene_noise,
        max_divisions_per_precursor=1,
        generator=gen,
    )
    assert isinstance(state, DevelopmentState)
    assert state.grn.shape[0] == 4  # 全不分裂
    assert torch.all(state.active_mask)

    state2 = proliferate(
        grn,
        positions,
        domain_index,
        torch.zeros(8),
        torch.tensor(100.0),  # 分裂概率 ~1
        split_noise=DEFAULT_CONFIG.split_noise,
        gene_noise=DEFAULT_CONFIG.gene_noise,
        max_divisions_per_precursor=1,
        generator=gen,
    )
    assert state2.grn.shape[0] == 8
    assert torch.all(state2.positions >= 0.0) and torch.all(state2.positions <= 1.0)
    assert torch.equal(state2.domain_index[:4], domain_index)
    assert torch.equal(state2.domain_index[4:], domain_index)
    # 子代 GRN 与原细胞不同（ε_g 非零）
    assert not torch.equal(state2.grn[4:], state2.grn[:4])


def test_proliferate_is_reproducible():
    def run() -> DevelopmentState:
        gen = SeedManager(11).torch_generator("development", 0)
        grn = torch.randn(24, 8, generator=gen)
        positions = torch.rand(24, 2, generator=gen)
        domain_index = torch.arange(24) % 6
        return proliferate(
            grn,
            positions,
            domain_index,
            torch.randn(8, generator=gen),
            torch.zeros(()),
            split_noise=DEFAULT_CONFIG.split_noise,
            gene_noise=DEFAULT_CONFIG.gene_noise,
            max_divisions_per_precursor=1,
            generator=gen,
        )

    first, second = run(), run()
    assert torch.equal(first.grn, second.grn)
    assert torch.equal(first.positions, second.positions)
    assert torch.equal(first.domain_index, second.domain_index)

def test_division_probability_defaults_are_bit_identical():
    """默认参数（``drive_gain=1.0`` / ``locus_gain=0.0``）必须与 §5 原式**逐位一致** ——
    这是「改变是 opt-in」的保证，也是全仓下游数字不被无意改动的守卫。"""
    g = torch.Generator().manual_seed(0)
    grn = torch.randn(6, 8, generator=g)
    w_div = torch.randn(8, generator=g)
    b_div = torch.tensor(0.3)
    assert torch.equal(division_probability(grn, w_div, b_div),
                       torch.sigmoid(grn @ w_div + b_div))


def test_division_probability_locus_channel_is_monotone():
    """基因组通道 β·q_A 必须**单调**抬升分裂概率（A 位点亲和越高→越可能分裂），
    且 α 的中心化把驱动钉在灵敏段（否则整体饱和、区分力归零）。"""
    g = torch.Generator().manual_seed(1)
    grn = torch.randn(9, 8, generator=g)
    w_div = torch.randn(8, generator=g)
    b_div = torch.zeros(())
    lo = division_probability(grn, w_div, b_div, drive_gain=2.0, locus_gain=3.0,
                              locus_channel=0.1)
    hi = division_probability(grn, w_div, b_div, drive_gain=2.0, locus_gain=3.0,
                              locus_channel=0.9)
    assert torch.all(hi >= lo)
    assert float(hi.mean()) > float(lo.mean())
    centred = division_probability(grn, w_div, b_div, drive_gain=2.0)
    assert abs(float(centred.mean()) - 0.5) < 0.25, "中心化后均值应回到灵敏段附近"


def test_division_gains_and_locus_index_wire_from_config():
    """``configs → RGCDConfig`` 必须把 §5 两个增益与通道索引带上（含 CLI 覆盖层）；
    索引以 ``genome.motif_subset_A`` 为**单一来源**。"""
    from evogenesis.core.config import ModelConfig, load_config
    from evogenesis.development.config import RGCDConfig, _resolve_default_model_config

    cfg = load_config(
        _resolve_default_model_config(),
        model=ModelConfig,
        overrides={
            "development.division_drive_gain": 14.5,
            "development.division_locus_gain": 12.0,
        },
    )
    rgcd = RGCDConfig.from_config(cfg)
    assert (rgcd.division_drive_gain, rgcd.division_locus_gain) == (14.5, 12.0)
    assert rgcd.division_locus_indices == (cfg.genome.motif_subset_A,)

