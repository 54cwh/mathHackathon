import numpy as np

from evogenesis.core.io import (
    load_array,
    now_iso,
    read_csv,
    read_jsonl,
    read_parquet,
    save_array,
    write_csv,
    write_jsonl,
    write_parquet,
)


def test_jsonl_roundtrip_unicode(tmp_path):
    path = tmp_path / "events.jsonl"
    records = [{"event": "spawn", "n": 1}, {"event": "捕获", "n": 2}]
    write_jsonl(path, records)
    assert read_jsonl(path) == records
    assert "捕获" in path.read_text(encoding="utf-8")


def test_csv_roundtrip(tmp_path):
    path = tmp_path / "metrics.csv"
    rows = [{"step": "0", "loss": "0.5"}, {"step": "1", "loss": "0.25"}]
    write_csv(path, rows, fieldnames=["step", "loss"])
    assert read_csv(path) == rows


def test_csv_infers_fieldnames(tmp_path):
    path = tmp_path / "metrics.csv"
    write_csv(path, [{"a": 1, "b": 2}])
    assert list(read_csv(path)[0].keys()) == ["a", "b"]


def test_parquet_roundtrip(tmp_path):
    path = tmp_path / "table.parquet"
    rows = [{"step": 0, "loss": 0.5}, {"step": 1, "loss": 0.25}]
    write_parquet(path, rows)
    assert read_parquet(path) == rows


def test_array_stored_as_float32(tmp_path):
    path = save_array(tmp_path / "arr", np.arange(4, dtype=np.float64))
    assert path.name == "arr.npz"
    loaded = load_array(path)
    assert loaded.dtype == np.float32
    assert np.allclose(loaded, np.arange(4, dtype=np.float32))


def test_now_iso_is_utc_z():
    stamp = now_iso()
    assert stamp.endswith("Z")
    assert "T" in stamp
