# DeepTrender - Makefile for common operations

.PHONY: help setup test run web clean lint format check-baseline

# Default target
help:
	@echo "=========================================="
	@echo "🔬 DeepTrender - Available Commands"
	@echo "=========================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup          - One-command setup (venv + deps + test)"
	@echo "  make install        - Install dependencies only"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-verbose   - Run tests with verbose output"
	@echo "  make test-cov       - Run tests with coverage report"
	@echo "  make check-baseline - Verify baseline (tests + pipeline dry-run)"
	@echo ""
	@echo "Running:"
	@echo "  make run            - Run full pipeline"
	@echo "  make run-test       - Run pipeline with small test data"
	@echo "  make run-arxiv      - Run arXiv-only pipeline"
	@echo "  make web            - Start web server"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Clean generated files"
	@echo "  make clean-all      - Clean everything (including venv)"
	@echo ""

# Setup
setup:
	@bash setup.sh

install:
	@echo "📦 Installing dependencies..."
	@pip install -r requirements.txt

# Testing
test:
	@echo "🧪 Running tests..."
	@pytest -q --tb=short

test-verbose:
	@echo "🧪 Running tests (verbose)..."
	@pytest -v

test-cov:
	@echo "🧪 Running tests with coverage..."
	@pytest --cov=src --cov-report=html --cov-report=term

check-baseline: test
	@echo ""
	@echo "✅ Baseline Check: Tests Passed"
	@echo ""
	@echo "📊 Running pipeline dry-run..."
	@python src/main.py --source arxiv --arxiv-days 1 --limit 5 --skip-structuring
	@echo ""
	@echo "✅ Baseline Check Complete"

# Running
run:
	@echo "🚀 Running full pipeline..."
	@python src/main.py

run-test:
	@echo "🚀 Running pipeline (test mode)..."
	@python src/main.py --source arxiv --arxiv-days 1 --limit 10

run-arxiv:
	@echo "🚀 Running arXiv pipeline..."
	@python src/main.py --source arxiv --arxiv-days 7 --extractor yake

web:
	@echo "🌐 Starting web server..."
	@echo "   Visit: http://localhost:5000"
	@python src/web/app.py

# Maintenance
clean:
	@echo "🧹 Cleaning generated files..."
	@rm -rf output/figures/*.png output/reports/*.md
	@rm -rf .pytest_cache __pycache__ src/__pycache__ tests/__pycache__
	@rm -rf htmlcov .coverage
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "✅ Clean complete"

clean-all: clean
	@echo "🧹 Cleaning everything (including venv)..."
	@rm -rf venv
	@echo "✅ Deep clean complete"

# Database operations
db-backup:
	@echo "💾 Backing up database..."
	@cp data/keywords.db data/keywords.backup_$(shell date +%Y%m%d_%H%M%S).db
	@echo "✅ Database backed up"

db-info:
	@echo "📊 Database Info:"
	@if [ -f data/keywords.db ]; then \
		echo "   Size: $$(du -h data/keywords.db | cut -f1)"; \
		echo "   Tables:"; \
		sqlite3 data/keywords.db "SELECT name FROM sqlite_master WHERE type='table';" | sed 's/^/     - /'; \
	else \
		echo "   Database not found"; \
	fi
