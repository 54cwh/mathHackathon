"""契约示例的稳定 ID 与 schema 守护（`schemas/examples/`）。

示例被 `schemas/examples/README.md` 声明「可被代码依赖」，故：ID 必须是 `core §3.1`
合规格式；实体示例必须过各自 schema。
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from evogenesis.core.ids import parse_id

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "schemas"


def _example(name: str) -> dict:
    return json.loads((S / "examples" / name).read_text(encoding="utf-8"))


def _schema(name: str) -> dict:
    return json.loads((S / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("example", "schema"),
    [
        ("genome_example.json", "genome.schema.json"),
        ("fish_example.json", "fish.schema.json"),
        ("experiment_example.json", "experiment.schema.json"),
    ],
)
def test_example_passes_schema(example, schema):
    jsonschema.validate(_example(example), _schema(schema))


def test_genome_and_fish_example_use_stable_ids():
    genome = _example("genome_example.json")
    fish = _example("fish_example.json")
    assert parse_id(genome["genome_id"])[2] == "genome"
    assert parse_id(fish["fish_id"])[2] == "fish"
    assert parse_id(fish["genome_id"])[2] == "genome"


def test_fish_example_uses_authoritative_cell_type_token():
    counts = _example("fish_example.json")["cell_counts"]
    assert "integrator_memory" in counts and "memory" not in counts
