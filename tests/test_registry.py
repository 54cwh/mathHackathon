import pytest

from evogenesis.core.registry import Registry


def test_register_and_resolve_alias(tmp_path):
    registry = Registry(tmp_path / "registry.json")
    registry.register("danionet", "1", path="models/a.pt", run_id="run-1", tags={"seed": "7"})
    registry.set_alias("danionet", "champion", "1")

    entry = registry.resolve("danionet", "champion")
    assert entry["version"] == "1"
    assert entry["source_run_id"] == "run-1"
    assert entry["tags"] == {"seed": "7"}


def test_versions_are_immutable(tmp_path):
    registry = Registry(tmp_path / "registry.json")
    registry.register("danionet", "1")
    with pytest.raises(FileExistsError):
        registry.register("danionet", "1")


def test_unknown_model_raises(tmp_path):
    registry = Registry(tmp_path / "registry.json")
    with pytest.raises(KeyError):
        registry.resolve("nope", "champion")


def test_alias_to_missing_version_raises(tmp_path):
    registry = Registry(tmp_path / "registry.json")
    registry.register("danionet", "1")
    with pytest.raises(KeyError):
        registry.set_alias("danionet", "champion", "2")


def test_resolve_requires_alias(tmp_path):
    registry = Registry(tmp_path / "registry.json")
    registry.register("danionet", "1")
    with pytest.raises(ValueError):
        registry.resolve("danionet")


def test_get_by_version(tmp_path):
    registry = Registry(tmp_path / "registry.json")
    registry.register("danionet", "1", run_id="run-1")
    registry.register("danionet", "2", run_id="run-2")
    assert registry.get("danionet", "2")["source_run_id"] == "run-2"


def test_get_missing_version_raises(tmp_path):
    registry = Registry(tmp_path / "registry.json")
    registry.register("danionet", "1")
    with pytest.raises(KeyError):
        registry.get("danionet", "9")


def test_persistence_across_instances(tmp_path):
    path = tmp_path / "registry.json"
    first = Registry(path)
    first.register("danionet", "1")
    second = Registry(path)
    assert second.list_models() == ["danionet"]
    assert second.versions("danionet") == ["1"]


def test_returned_entries_are_isolated_from_store(tmp_path):
    registry = Registry(tmp_path / "registry.json")
    handle = registry.register("danionet", "1", run_id="run-1")
    handle["tags"]["mutated"] = "yes"
    handle["source_run_id"] = "tampered"
    assert registry.get("danionet", "1")["source_run_id"] == "run-1"
    assert registry.get("danionet", "1")["tags"] == {}

    registry.set_alias("danionet", "champion", "1")
    resolved = registry.resolve("danionet", alias="champion")
    resolved["path"] = "/tampered"
    assert registry.get("danionet", "1")["path"] is None
