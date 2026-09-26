#!/usr/bin/env bash
# 编译论文。中文草稿用 xelatex（ctex 需要）；换英文/会议模板后命令不变。
set -euo pipefail
cd "$(dirname "$0")"
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
echo "==> main.pdf"
