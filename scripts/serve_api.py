"""薄 CLI：启动 EvoGenesis API 服务（单 worker；`API与系统工程.md` §9）。

会话为纯内存（`API接口.md` §7.1），故**必须单 worker**——多 worker 会让同一
`session_id` 落到不同进程而随机 404。
"""

from __future__ import annotations

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the EvoGenesis API server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run(
        "evogenesis.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
