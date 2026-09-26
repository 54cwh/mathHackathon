import argparse
import json
import subprocess
from pathlib import Path

from evogenesis.core.config import read_yaml
from evogenesis.core.io import now_iso

ROOT = Path(__file__).resolve().parents[1]


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an EvoGenesis experiment run.")
    parser.add_argument("--config", required=True, help="configs/ 下的 yaml 路径")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument(
        "--experiment-id",
        required=True,
        help="稳定实验 ID，即 results/runs/<experiment_id>/ 的目录名（核心契约，调用方给定）",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    if not config_path.is_file():
        parser.error(f"配置不存在: {config_path}")

    # 各 configs/*.yaml 的节 schema 不同，这里只做 YAML 解析校验，不套用单一模型。
    read_yaml(config_path)

    run_dir = ROOT / "results" / "runs" / args.experiment_id
    if run_dir.exists():
        parser.error(f"run 目录已存在（experiment_id 需唯一）: {run_dir.relative_to(ROOT)}")
    (run_dir / "config_snapshot").mkdir(parents=True)
    (run_dir / "config_snapshot" / config_path.name).write_text(
        config_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (run_dir / "seed.txt").write_text(f"{args.seed}\n", encoding="utf-8")
    (run_dir / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    metadata = {
        "experiment_id": args.experiment_id,
        "config": str(config_path.relative_to(ROOT)),
        "seed": args.seed,
        "status": "created",
        "created_at": now_iso(),
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"已创建 run 目录: {run_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
