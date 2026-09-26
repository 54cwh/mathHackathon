import json

from evogenesis.core.logging import configure_logging, get_logger


def _read_lines(path):
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def test_jsonl_otel_fields(tmp_path):
    log_path = tmp_path / "logs.jsonl"
    configure_logging(log_path, level="info", resource={"experiment_id": "exp1"})
    get_logger("t").info("hello", step=3)

    records = _read_lines(log_path)
    assert len(records) == 1
    record = records[0]
    assert record["event"] == "hello"
    assert record["severity_text"] == "INFO"
    assert record["severity_number"] == 9
    assert record["step"] == 3
    assert record["experiment_id"] == "exp1"
    assert record["timestamp"].endswith("Z")


def test_level_filtering(tmp_path):
    log_path = tmp_path / "logs.jsonl"
    configure_logging(log_path, level="warning")
    logger = get_logger("t")
    logger.info("skip-me")
    logger.error("keep-me")

    events = [r["event"] for r in _read_lines(log_path)]
    assert events == ["keep-me"]


def test_unknown_level_rejected(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        configure_logging(tmp_path / "logs.jsonl", level="nope")
