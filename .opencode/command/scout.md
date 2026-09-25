---
description: 调研侦察——检索 GitHub 项目、论文与数据，落盘 research/reference/ JSON
agent: scout
---

调研任务：$ARGUMENTS

先读 `docs/search-spec.md`，再按 scout 的工作方法执行：
1. 用 `gh search repos` 找开源实现，用 `openalex_*` / `arxiv` MCP 找理论锚点，二者对应。
2. 结果写入 `research/reference/` 下的 JSON（遵循 `docs/search-spec.md`）；同名文件优先更新并记录搜索时间。
3. 每个候选给出：名称 | 链接 | star/引用 | 最近更新 | 许可 | 作用 | 适配度(1-5)。
4. 给出「推荐直接用 / 仅作参考 / 不建议」三级结论，并标注需进一步验证的风险点。
5. 不确定的字段标"待验证"，不得杜撰。
