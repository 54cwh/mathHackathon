"""稳定 ID 铸造（``core §3.1``）。"""

from typing import cast

import pytest

from evogenesis.core.ids import mint_id, parse_id, parse_index


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
    with pytest.raises(ValueError):
        mint_id("exp", "genome", cast(int, 1.5), 0)
    with pytest.raises(ValueError):
        mint_id("exp", "genome", 0, True)


def test_parse_id_roundtrip():
    for role in ("genome", "fish"):
        for generation, index in ((0, 0), (3, 7), (19, 12345)):
            stable_id = mint_id("exp-0001", role, generation, index)
            assert parse_id(stable_id) == ("exp-0001", generation, role, index)
            assert parse_index(stable_id) == index


def test_parse_id_rejects_bad_inputs():
    for bad in ("", "exp:g0:fish", "exp:g0:fish00", "exp:g-1:fish0000", "exp:g0:bird0000"):
        with pytest.raises(ValueError):
            parse_id(bad)
