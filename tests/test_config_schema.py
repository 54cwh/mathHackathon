"""`configs/default_model.yaml` 与 core 模型 schema 的一致性守护。

字段名/类型的唯一 owner 是 `core/config.py`。本测试确保该 YAML 不出现未登记的节/键、
也不缺登记过的键——防止"各模块另写一版 schema"造成的静默漂移（A5）。
"""

from pathlib import Path

import yaml

from evogenesis.core.config import ModelConfig

CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "default_model.yaml"


def _data() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def test_default_model_sections_match_core():
    assert set(_data()) == set(ModelConfig.model_fields)


def test_default_model_section_keys_match_core():
    data = _data()
    for name, field in ModelConfig.model_fields.items():
        section = field.annotation
        assert section is not None
        assert set(data[name]) == set(section.model_fields), name
