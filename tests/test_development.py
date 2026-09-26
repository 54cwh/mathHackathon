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
