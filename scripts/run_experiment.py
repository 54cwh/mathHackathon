import argparse
import json
import subprocess
import time
from pathlib import Path

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
    parser.add_argument("--tag", default="run", help="run 目录后缀标签")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    if not config_path.is_file():
        parser.error(f"配置不存在: {config_path}")

    run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{args.tag}"
    run_dir = ROOT / "results" / "runs" / run_id
    (run_dir / "config_snapshot").mkdir(parents=True, exist_ok=True)
    (run_dir / "config_snapshot" / config_path.name).write_text(
        config_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (run_dir / "seed.txt").write_text(f"{args.seed}\n", encoding="utf-8")
    (run_dir / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    metadata = {
        "run_id": run_id,
        "config": str(config_path.relative_to(ROOT)),
        "seed": args.seed,
        "status": "created",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"已创建 run 目录: {run_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
