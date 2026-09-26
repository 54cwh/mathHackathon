.PHONY: help env test lint fmt tree experiment frontend demo

help:
	@echo "make env        - 同步依赖并安装 evogenesis（editable）"
	@echo "make test       - 运行测试"
	@echo "make lint       - ruff 静态检查"
	@echo "make fmt        - ruff 格式化"
	@echo "make tree       - 查看项目目录结构"
	@echo "make experiment - 创建实验 run，例: make experiment ARGS='--config configs/default_arena.yaml --seed 1 --experiment-id exp-0001'"
	@echo "make frontend   - 构建前端产物到 frontend/dist"
	@echo "make demo       - 一键起服（构建前端 + 启动 API），浏览器开 http://127.0.0.1:8000"

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
		-not -path './frontend/node_modules*' -not -path './frontend/dist*' \
		| sort

experiment:
	uv run python scripts/run_experiment.py $(ARGS)

frontend:
	cd frontend && npm run build

demo:
	./scripts/start_demo.sh
