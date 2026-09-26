# 论文（LaTeX）

> **owner**：李辰钊（report lane）。中文草稿先行，后续按投稿会议改英文。

## 1. 编译

```bash
cd paper/latex && ./build.sh          # = latexmk -xelatex main.tex -> main.pdf
```

- **必须用 xelatex**（`ctex` 的中文排版依赖它）；`pdflatex` 会因 CJK 报错。
- TeX Live 2026 已验证可编译；本机 `xelatex` / `biber` / `latexmk` 均可用。
- 编译产物（`*.aux`、`*.pdf` 等）已被根 `.gitignore` 忽略。

## 2. 结构

```
main.tex                 总装：docclass + 顺序 input
preamble.tex             导言区（**换会议时主要改这里**）
refs.bib                 自动生成，请勿手改
sections/00..07-*.tex    正文，与 paper/报告-骨架.md 章节一一对应
figs/                    论文用图（自包含）
```

## 3. 文献（重要约束）

`refs.bib` **由脚本从唯一来源生成**，不要手写：

```bash
.venv/Scripts/python.exe scripts/make_bib.py          # 重新生成
.venv/Scripts/python.exe scripts/make_bib.py --check  # 校验同步（门禁）
```

- 唯一来源 = `research/notes/bibliography.md`（仓库硬约束：**未登记即引用＝缺陷**）。
- 生成器支持该文件实际混用的**三种条目格式**，要求每条有 DOI **或**稳定链接；
  当前 **220 条全部解析、0 丢弃**。
- key 规则：`bibN_<首作者姓><年份>`，与 bibliography.md 第 N 条一一对应，
  故正文引用能直接对上 md 里的 `[bib#N]`。

## 4. 换投稿目标（中文 → 英文/会议模板）

只改两处，`sections/*.tex` **不动**：

1. `main.tex` 的 `\documentclass{ctexart}` → 会议官方 class/sty
   （如 `\documentclass{article}` + 对应的 style 文件）。
2. `preamble.tex` 的「版式」段 → 会议官方版式；若模板自带参考文献宏包，
   删掉我们引入的那一行避免冲突。

建议顺序：**中文先把内容写实** → 定稿后一次性转英文，避免反复改写。

## 5. 图（自包含）

- 论文用图统一放 `paper/latex/figs/`，用 `\graphicspath{{figs/}}` 引用**文件名**。
- **不要把论文图指向 `results/`**：该目录被 `.gitignore` 忽略，他机会编译失败。
  故需把选定图**复制**进 `figs/`（`figs/*.png` 可提交）。
- 每张图的底层数据在 `results/**/data/<同名>.xlsx`，映射见 `paper/图表-数据对照表.md`。

## 6. 写作纪律

- **禁止 AI 填空**：未跑完的实验一律用 `\todo{...}` 标注并留在正文（红色可见），
  不得用编造的数值或结论顶替。
- 引用只从 `refs.bib` 取（即只引已登记文献）。
- 图注若写数字，必须一并声明 `paper/图表-数据对照表.md` §3 的三条口径警示。
