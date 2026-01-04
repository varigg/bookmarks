# Bookmarks Project Makefile
# Automation shortcuts for common development tasks

.PHONY: help test test-verbose test-coverage lint typecheck format format-check clean-code clean install run docker-build docker-up docker-down configure service-install
CONFIG_ENV_FILE := $(HOME)/.config/bookmarks/.env
DEFAULT_DATA_DIR := /srv/bookmarks-data

# Default target: show help
help:
	@echo "Available targets:"
	@echo "  make install         - Install dependencies with uv"
	@echo "  make test           - Run all tests"
	@echo "  make test-verbose   - Run tests with verbose output"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make lint           - Run ruff linter (check only)"
	@echo "  make typecheck      - Run ty type checker"
	@echo "  make format         - Run ruff formatter and fix imports"
	@echo "  make format-check   - Check formatting without modifying files"
	@echo "  make clean-code     - Format, lint, and test (run before commit)"
	@echo "  make clean          - Remove cache and build artifacts"
	@echo "  make run            - Run the Flask development server"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-up      - Start services with docker-compose"
	@echo "  make docker-down    - Stop docker-compose services"
	@echo "  make configure      - Run interactive configuration wizard"
	@echo "  make service-install - Configure and start services with named volumes"

# Install dependencies
install:
	uv sync

# Run tests
test:
	uv run pytest

# Run tests with verbose output
test-verbose:
	uv run pytest -v

# Run tests with coverage
test-coverage:
	uv run pytest --cov=bookmarks --cov-report=html --cov-report=term

# Lint code
lint:
	uv run ruff check .

# Type check with ty (excludes routes due to Pydantic dynamic typing)
typecheck:
	uv run ty check --exclude "bookmarks/web/routes.py" --exclude "tools/**" .

# Format code (fix)
format:
	uv run ruff format .
	uv run ruff check --select I --fix .

# Check formatting without modifying
format-check:
	uv run ruff format --check .
	uv run ruff check .

# Run format, lint, and test (pre-commit quality check)
clean-code:
	@echo "🔧 Formatting code..."
	@$(MAKE) format
	@echo "\n🔍 Linting code..."
	@$(MAKE) lint
	@echo "\n✅ Running tests..."
	@$(MAKE) test
	@echo "\n✨ All checks passed! Ready to commit."

# Clean cache and build artifacts
clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache .coverage htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Run Flask development server
run:
	uv run flask run --debug

# Docker commands
docker-build:
	docker compose build

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

# Infrastructure commands (alias)
infrastructure-build: docker-build
infrastructure-up: docker-up
infrastructure-stop: docker-down

# Configuration and Installation
configure:
	uv run python tools/configure.py

service-install: configure
	@env_file=$(CONFIG_ENV_FILE); \
	if [ -f "$$env_file" ]; then \
		set -a; \
		. "$$env_file"; \
		set +a; \
	fi; \
	data_dir="$${BOOKMARKS_DATA_DIR:-$(DEFAULT_DATA_DIR)}"; \
	sudo mkdir -p "$$data_dir" "$$data_dir/backup"; \
	sudo chmod -R u+rwX "$$data_dir"; \
	echo "📁 Data directory ready: $$data_dir"; \
	echo "🔨 Building Docker image..."; \
	if ! sudo docker compose build; then \
		echo ""; \
		echo "❌ Docker build failed. Docker daemon may not be running:"; \
		echo "   sudo systemctl start docker"; \
		echo ""; \
		exit 1; \
	fi; \
	echo "🚀 Starting services..."; \
	sudo docker compose up -d
