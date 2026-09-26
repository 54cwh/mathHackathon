"""`configs/*.yaml` 与各自 schema owner 的一致性守护（A5）。

每个 YAML 的字段名/类型有**唯一 owner**：`default_model.yaml` → `core.ModelConfig`；
`default_arena.yaml` → `arena.config.ARENA_SECTIONS` 的 dataclass。本测试确保 YAML 不出现
未登记的节/键、也不缺登记过的键——防止"另写一版 schema"造成的静默漂移。
"""

from dataclasses import fields
from pathlib import Path

import yaml

from evogenesis.arena.config import ARENA_SECTIONS, DERIVED_READONLY_KEYS
from evogenesis.core.config import ModelConfig

CONFIGS = Path(__file__).resolve().parents[1] / "configs"


def _data(filename: str) -> dict:
    return yaml.safe_load((CONFIGS / filename).read_text(encoding="utf-8"))


def test_default_model_sections_match_core():
    assert set(_data("default_model.yaml")) == set(ModelConfig.model_fields)


def test_default_model_section_keys_match_core():
    data = _data("default_model.yaml")
    for name, field in ModelConfig.model_fields.items():
        section = field.annotation
        assert section is not None
        assert set(data[name]) == set(section.model_fields), name


def test_default_arena_sections_match_module_schema():
    assert set(_data("default_arena.yaml")) == set(ARENA_SECTIONS)


def test_default_arena_section_keys_match_module_schema():
    data = _data("default_arena.yaml")
    for name, section_type in ARENA_SECTIONS.items():
        allowed = {f.name for f in fields(section_type)}
        derived = {key for section, key in DERIVED_READONLY_KEYS if section == name}
        assert set(data[name]) == allowed | derived, name
