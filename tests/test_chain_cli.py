"""`scripts/run_chain.py` 冒烟：DanioNet 驱动 Arena 跑一代，落 run 产物。

守护「genome → 发育 → connectome → Arena」上游链路的**生产入口**可用：
viable 个体进 Arena、稳定 ID、`events.jsonl`（header + 逐事件，过 schema）、`metrics.csv`。
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_chain.py"
SCHEMA = json.loads((ROOT / "schemas" / "event_log.schema.json").read_text(encoding="utf-8"))
EXPERIMENT_ID = "cli-chain"
SEED = 1103


def test_chain_cli_writes_run_artifacts(tmp_path: Path):
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--experiment-id",
            EXPERIMENT_ID,
            "--seed",
            str(SEED),
            "--n",
            "12",
            "--steps",
            "20",
            "--out-root",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr

    run_dir = tmp_path / f"{EXPERIMENT_ID}-s{SEED}"
    assert {"metrics.csv", "events.jsonl", "seed_summary.json"} <= {
        p.name for p in run_dir.iterdir()
    }

    records = [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    header, *events = records
    assert header["record_type"] == "header"
    assert header["experiment_id"] == EXPERIMENT_ID
    assert header["n_events"] == len(events)
    for record in records:
        jsonschema.validate(record, SCHEMA)

    with (run_dir / "metrics.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows, "无 viable 个体的指标行"
    for row in rows:
        assert row["fish_id"].startswith(f"{EXPERIMENT_ID}:g0:fish")
        assert 0.0 <= float(row["survival"]) <= 1.0
