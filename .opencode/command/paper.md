---
description: 论文写作/改稿——指定任务，由主对话按规范撰写并守去AI味底线
---

写作任务：$ARGUMENTS

这项工作要求与用户多轮确认，在主对话中执行，不委派子代理。

写作前先读 `AGENTS.md` 与 `ai-tone-boundaries.md`；涉及写作手法时加载 `academic-writing-distillation` skill。只依据 `research/notes/`、`src/`、`results/`、`artifacts/` 的既有材料，不新增事实/数字/结论。每处"提升/显著"必须接具体数值或引用。产出 LaTeX 到 `paper/`，本地编译（`latexmk`/`xelatex`），改稿附对照 ai-tone-boundaries 的自检清单。角色定义与固定要求见 `docs/design/prompts/report_agent.md`。
