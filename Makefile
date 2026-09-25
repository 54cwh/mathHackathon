.PHONY: help env test lint fmt tree

help:
	@echo "make env    - 同步依赖并安装 mh（editable）"
	@echo "make test   - 运行测试"
	@echo "make lint   - ruff 静态检查"
	@echo "make fmt    - ruff 格式化"
	@echo "make tree   - 查看项目目录结构"

env:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check .

fmt:
	uv run ruff format .

tree:
	@find . -type d \
		-not -path './.git*' -not -path './.venv*' -not -path './refs*' \
		-not -path './.opencode/node_modules*' -not -path '*/__pycache__*' \
		| sort
