# ═══════════════════════════════════════════════════════════════════════
# Makefile — Autonomous Multi-Agent AI Organization
# Cross-platform shortcuts for common operations
# Usage: make <target>
# ═══════════════════════════════════════════════════════════════════════

.PHONY: help start stop restart logs test build clean status shell demo

# Default target
help:
	@echo ""
	@echo "  🏢 Autonomous Multi-Agent AI Organization"
	@echo "  ══════════════════════════════════════════"
	@echo ""
	@echo "  make start        Start all services (detached)"
	@echo "  make stop         Stop all services"
	@echo "  make restart      Restart all services"
	@echo "  make logs         Tail logs (all services)"
	@echo "  make status       Show running containers + health"
	@echo ""
	@echo "  make test         Run unit tests"
	@echo "  make lint         Run ruff + black check"
	@echo "  make security     Run bandit security scan"
	@echo ""
	@echo "  make build        Rebuild all Docker images"
	@echo "  make clean        Remove containers + volumes (fresh start)"
	@echo "  make shell        Open shell in orchestrator container"
	@echo "  make demo         Run the AI demo pipeline"
	@echo ""
	@echo "  make setup        First-time setup (copy .env, build images)"
	@echo "  make grafana      Open Grafana dashboard in browser"
	@echo "  make kafka-ui     Open Kafka UI in browser"
	@echo "  make jaeger       Open Jaeger tracing UI in browser"
	@echo ""

# ── Setup ────────────────────────────────────────────────────────────
setup:
	@echo "📋 Setting up AI Organization..."
	@test -f .env || (cp .env.example .env && echo "✅ .env created from .env.example — please fill in your API keys")
	@mkdir -p output monitoring/grafana/provisioning/datasources monitoring/grafana/dashboards
	@docker compose build
	@echo "✅ Setup complete. Run: make start"

# ── Core Operations ──────────────────────────────────────────────────
start:
	@echo "🚀 Starting AI Organization..."
	@docker compose up -d
	@echo ""
	@echo "  ✅ Dashboard:    http://localhost:3000"
	@echo "  ✅ API:          http://localhost:8080"
	@echo "  ✅ Kafka UI:     http://localhost:8888"
	@echo "  ✅ Grafana:      http://localhost:3002  (admin / ai-org-admin)"
	@echo "  ✅ Prometheus:   http://localhost:9090"
	@echo "  ✅ Jaeger:       http://localhost:16686"
	@echo ""

stop:
	@echo "🛑 Stopping AI Organization..."
	@docker compose down
	@echo "✅ Stopped."

restart:
	@docker compose down
	@docker compose up -d

logs:
	@docker compose logs -f --tail=100

logs-orchestrator:
	@docker compose logs -f orchestrator --tail=100

logs-agents:
	@docker compose logs -f ceo-agent cto-agent engineer-backend engineer-frontend qa-agent devops-agent finance-agent

status:
	@echo "📊 Service Status:"
	@docker compose ps

# ── Development ──────────────────────────────────────────────────────
build:
	@echo "🐳 Building Docker images..."
	@docker compose build --parallel
	@echo "✅ Build complete."

build-no-cache:
	@docker compose build --no-cache --parallel

shell:
	@docker compose exec orchestrator bash

shell-agent:
	@docker compose exec ceo-agent bash

# ── Testing ──────────────────────────────────────────────────────────
test:
	@echo "🧪 Running tests..."
	@docker compose exec orchestrator python -m pytest tests/ -v --tb=short 2>/dev/null || \
		(source venv/bin/activate 2>/dev/null || true; python -m pytest tests/ -v --tb=short)

test-local:
	@source venv/bin/activate && python -m pytest tests/unit/ -v --tb=short

test-coverage:
	@source venv/bin/activate && python -m pytest tests/ --cov=. --cov-report=html
	@echo "📊 Coverage report: htmlcov/index.html"

lint:
	@echo "🔍 Linting..."
	@source venv/bin/activate && ruff check . && black --check .
	@echo "✅ Lint passed."

lint-fix:
	@source venv/bin/activate && ruff check . --fix && black .

security:
	@echo "🔒 Security scan..."
	@source venv/bin/activate && bandit -r agents/ orchestrator/ api/ moe/ messaging/ tools/ -ll
	@echo "✅ Security scan complete."

# ── Demo ─────────────────────────────────────────────────────────────
demo:
	@echo "🎬 Running AI Organization demo pipeline..."
	@source venv/bin/activate && python run_demo.py

demo-docker:
	@docker compose exec orchestrator python run_demo.py

# ── Data Management ───────────────────────────────────────────────────
clean:
	@echo "⚠️  This will delete ALL data (volumes). Press Ctrl+C to cancel..."
	@sleep 3
	@docker compose down -v
	@echo "✅ Cleaned. Fresh start."

clean-output:
	@rm -rf output/*
	@echo "✅ Output directory cleaned."

# ── UI Shortcuts (open browser) ────────────────────────────────────────
grafana:
	@open http://localhost:3002 2>/dev/null || xdg-open http://localhost:3002 2>/dev/null || echo "Open: http://localhost:3002"

kafka-ui:
	@open http://localhost:8888 2>/dev/null || xdg-open http://localhost:8888 2>/dev/null || echo "Open: http://localhost:8888"

jaeger:
	@open http://localhost:16686 2>/dev/null || xdg-open http://localhost:16686 2>/dev/null || echo "Open: http://localhost:16686"

dashboard:
	@open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null || echo "Open: http://localhost:3000"

# ── Git Workflow ─────────────────────────────────────────────────────
branch-feature:
	@read -p "Feature name (e.g. nextjs-dashboard): " name; \
	git checkout master && git checkout -b feature/$$name

branch-bugfix:
	@read -p "Bug name: " name; \
	git checkout master && git checkout -b bugfix/$$name

branch-status:
	@echo "Current branch: $$(git branch --show-current)"
	@echo "All branches:"
	@git branch -a
