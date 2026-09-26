---
description: 实验实现——搭最小可复现管线，出结果图与指标表
agent: experimenter
---

实验目标：$ARGUMENTS

先用 `uv`（`uv sync` / `uv add` / `uv run`）确认环境，实现最小可跑实验验证管线，再按需放大。固定种子、记录配置：图存 `results/figs/`、指标存 `results/tables/`、运行细节存 `results/runs/<id>/`，冻结演示资产存 `artifacts/`。报告参数量/FLOPs/延迟/能耗中至少两项。收尾按 AGENTS.md「代码审查」一节自检。先给方案再动代码。
