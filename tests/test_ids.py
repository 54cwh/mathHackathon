"""稳定 ID 铸造（``core §3.1``）。"""

import pytest

from evogenesis.core.ids import mint_id


def test_mint_id_format_and_determinism():
    assert mint_id("exp-0001", "genome", 3, 7) == "exp-0001:g3:genome0007"
    assert mint_id("exp-0001", "genome", 3, 7) == mint_id("exp-0001", "genome", 3, 7)
    assert mint_id("exp-0001", "fish", 0, 0) == "exp-0001:g0:fish0000"


def test_mint_id_unique_within_generation():
    ids = {mint_id("exp-0001", "fish", 2, index) for index in range(100)}
    assert len(ids) == 100


def test_mint_id_rejects_bad_inputs():
    with pytest.raises(ValueError):
        mint_id("", "genome", 0, 0)
    with pytest.raises(ValueError):
        mint_id("a:b", "genome", 0, 0)
    with pytest.raises(ValueError):
        mint_id("exp", "unknown", 0, 0)
    with pytest.raises(ValueError):
        mint_id("exp", "genome", -1, 0)
    with pytest.raises(ValueError):
        mint_id("exp", "genome", 0, -1)
