---
description: 代码审查——按 docs/code-review.md 跑自动检查与人工清单，输出阻断/重要/建议
agent: reviewer
---

审查范围：$ARGUMENTS

严格按 `docs/code-review.md` 执行：先跑 `uv run ruff format .`、`uv run ruff check .`、`uv run pytest -q`（必须全绿），再逐条核对人工清单。按 阻断/重要/建议 输出，每条含问题、位置（`file:line`）、修改建议，并给出一行留痕。只审查、不修改文件。
