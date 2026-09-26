"""penetrance 校准 / 报告 CLI（薄壳；业务逻辑 owner：`experiment/penetrance.py`）。

用法::

    uv run python scripts/run_penetrance.py --experiment-id pen-0001 --mode calibrate
    uv run python scripts/run_penetrance.py --experiment-id pen-0001 --mode report

- ``calibrate``：在独立校准集（AaBb×AaBb 自交）上定 ``θ_N^obs/θ_H^obs``，写
  ``results/tables/<id>_penetrance_calibration.json``；**不**改 config，冻结由人签署。
- ``report``：读 ``configs/penetrance.yaml`` 已冻结的 ``θ^obs``，出逐类 ``pen(g)`` + Wilson CI +
  2×2 观测档计数 + 连续分布，写 ``results/tables/<id>_penetrance.json``（schema
  ``schemas/penetrance.schema.json``）。报告样本不得调阈值（`genome §3`）。
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:  # 允许未 editable 安装时 `python scripts/...`
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from evogenesis.experiment import penetrance as P  # noqa: E402
from evogenesis.experiment.console import force_utf8_stdout  # noqa: E402


def _parse_seeds(value: str | None) -> tuple[int, ...] | None:
    if value is None:
        return None
    seeds = tuple(int(token) for token in value.split(",") if token.strip())
    if not seeds:
        raise argparse.ArgumentTypeError("seeds 不能为空")
    return seeds


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdout()
    parser = argparse.ArgumentParser(
        description="penetrance 校准/报告（genome §3 / experiment §3.9）"
    )
    parser.add_argument("--experiment-id", required=True, help="实验 id（产物文件名/种子命名空间）")
    parser.add_argument("--mode", choices=("calibrate", "report"), default="report")
    parser.add_argument("--model-config", default=str(P.DEFAULT_MODEL_CONFIG))
    parser.add_argument("--penetrance-config", default=str(P.DEFAULT_PENETRANCE_CONFIG))
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--seeds", default=None, help="逗号分隔 master seed（覆盖 config，校准/报告同用）"
    )
    parser.add_argument("--calibration-offspring", type=int, default=None)
    parser.add_argument("--report-offspring", type=int, default=None)
    parser.add_argument("--json", default=None, help="产物路径（缺省 results/tables/<id>_*.json）")
    args = parser.parse_args(argv)

    config = P.load_penetrance_config(args.penetrance_config)
    updates: dict[str, object] = {}
    seeds = _parse_seeds(args.seeds)
    if seeds is not None:
        updates["calibration_master_seeds"] = seeds
        updates["report_master_seeds"] = seeds
    if args.calibration_offspring is not None:
        updates["calibration_offspring"] = args.calibration_offspring
    if args.report_offspring is not None:
        updates["report_offspring"] = args.report_offspring
    if updates:
        config = dataclasses.replace(config, **updates)

    if args.mode == "calibrate":
        payload = P.run_calibration(
            args.experiment_id,
            model_config_path=args.model_config,
            penetrance_config=config,
            device=args.device,
        )
        out = Path(args.json) if args.json else P.table_path(args.experiment_id, kind="calibration")
        cal = payload["calibration"]
        print("penetrance 校准（AaBb×AaBb 独立校准集；草案待确认）")
        print(f"  n_rows={cal['n_rows']}  genotype_counts={payload['genotype_counts']}")
        print(
            f"  θ_N^obs: min-misclass={cal['theta_N_obs_min_misclass']:.4g}"
            f"  median-midpoint={cal['theta_N_obs_median_midpoint']:.4g}"
            f"  misclass={cal['misclass_rate_N']:.3f}"
        )
        print(
            f"  θ_H^obs: min-misclass={cal['theta_H_obs_min_misclass']:.4g}"
            f"  median-midpoint={cal['theta_H_obs_median_midpoint']:.4g}"
            f"  misclass={cal['misclass_rate_H']:.3f}"
        )
    else:
        payload = P.run_report(
            args.experiment_id,
            model_config_path=args.model_config,
            penetrance_config=config,
            device=args.device,
        )
        out = Path(args.json) if args.json else P.table_path(args.experiment_id, kind="report")
        print("penetrance 报告（独立报告集；θ^obs 取自 config，未再调）")
        for label, stat in payload["report"]["pooled"]["per_class"].items():
            pen = "None" if stat["penetrance"] is None else f"{stat['penetrance']:.3f}"
            print(f"  {label:5s} n={stat['n']:<4d} pen={pen}")
        print(f"  observed_9331={payload['report']['observed_9331']}")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  写出: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
