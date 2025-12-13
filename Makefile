# Bookmarks Project Makefile
# Automation shortcuts for common development tasks

.PHONY: help test test-verbose test-coverage lint format format-check clean install run docker-build docker-up docker-down

# Default target: show help
help:
	@echo "Available targets:"
	@echo "  make install         - Install dependencies with uv"
	@echo "  make test           - Run all tests"
	@echo "  make test-verbose   - Run tests with verbose output"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make lint           - Run ruff linter (check only)"
	@echo "  make format         - Run ruff formatter and fix imports"
	@echo "  make format-check   - Check formatting without modifying files"
	@echo "  make clean          - Remove cache and build artifacts"
	@echo "  make run            - Run the Flask development server"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-up      - Start services with docker-compose"
	@echo "  make docker-down    - Stop docker-compose services"

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

# Format code (fix)
format:
	uv run ruff format .
	uv run ruff check --select I --fix .

# Check formatting without modifying
format-check:
	uv run ruff format --check .
	uv run ruff check .

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
