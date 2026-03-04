SHELL := /bin/bash
GO     := /snap/bin/go
MODULE := github.com/DsThakurRawat/autonomous-org/go-backend

# ── Colours ──────────────────────────────────────────────────────────────
CYAN  := \033[36m
RESET := \033[0m
BOLD  := \033[1m

.PHONY: help build test lint proto migrate-up migrate-down dev clean docker-build

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS=":.*?## "}; {printf "$(CYAN)%-20s$(RESET) %s\n", $$1, $$2}'

## ── Build ────────────────────────────────────────────────────────────────

build: ## Build all 6 binaries into ./bin/
	@echo -e "$(BOLD)Building all services...$(RESET)"
	$(GO) build -ldflags="-s -w" -o bin/gateway         ./cmd/gateway
	$(GO) build -ldflags="-s -w" -o bin/orchestrator    ./cmd/orchestrator
	$(GO) build -ldflags="-s -w" -o bin/ws-hub          ./cmd/ws-hub
	$(GO) build -ldflags="-s -w" -o bin/tenant-svc      ./cmd/tenant-svc
	$(GO) build -ldflags="-s -w" -o bin/metrics-svc     ./cmd/metrics-svc
	$(GO) build -ldflags="-s -w" -o bin/health-monitor  ./cmd/health-monitor
	@echo -e "$(CYAN)Done. Binaries in ./bin/$(RESET)"

build-gateway: ## Build only the gateway
	$(GO) build -ldflags="-s -w" -o bin/gateway ./cmd/gateway

## ── Test ─────────────────────────────────────────────────────────────────

test: ## Run all tests with race detector
	$(GO) test -race -count=1 ./...

test-cover: ## Run tests with coverage report
	$(GO) test -race -coverprofile=coverage.out ./...
	$(GO) tool cover -html=coverage.out -o coverage.html
	@echo "Coverage report: coverage.html"

test-integration: ## Run integration tests (requires Docker)
	$(GO) test -tags=integration -race -timeout=120s ./...

bench: ## Run benchmarks
	$(GO) test -bench=. -benchmem ./...

## ── Quality ──────────────────────────────────────────────────────────────

lint: ## Run golangci-lint
	golangci-lint run ./...

vet: ## Run go vet
	$(GO) vet ./...

fmt: ## Format all Go files
	gofmt -s -w .
	goimports -w .

tidy: ## Tidy go.mod
	$(GO) mod tidy

## ── Protobuf ─────────────────────────────────────────────────────────────

proto: ## Generate gRPC stubs from .proto files
	@echo -e "$(BOLD)Generating protobuf stubs...$(RESET)"
	protoc \
		--go_out=./proto/gen \
		--go_opt=paths=source_relative \
		--go-grpc_out=./proto/gen \
		--go-grpc_opt=paths=source_relative \
		proto/*.proto
	@echo -e "$(CYAN)Stubs written to proto/gen/$(RESET)"

proto-install: ## Install protoc Go plugins
	$(GO) install google.golang.org/protobuf/cmd/protoc-gen-go@latest
	$(GO) install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

## ── Database ─────────────────────────────────────────────────────────────

migrate-up: ## Run all pending migrations
	migrate -path migrations -database "$(DATABASE_URL)" up

migrate-down: ## Rollback last migration
	migrate -path migrations -database "$(DATABASE_URL)" down 1

migrate-create: ## Create new migration (use: make migrate-create NAME=add_users)
	migrate create -ext sql -dir migrations -seq $(NAME)

## ── Dev ──────────────────────────────────────────────────────────────────

dev-gateway: ## Run gateway with hot reload (requires air)
	air -c .air.gateway.toml

dev-orchestrator: ## Run orchestrator with hot reload
	air -c .air.orchestrator.toml

infra-up: ## Start local infra (Postgres, Redis, Kafka) via Docker
	docker compose -f ../docker-compose.yml up -d postgres redis kafka zookeeper

infra-down: ## Stop local infra
	docker compose -f ../docker-compose.yml down

## ── Docker ───────────────────────────────────────────────────────────────

docker-build: ## Build all Docker images
	docker build -f deploy/dockerfiles/Dockerfile.gateway    -t ai-org/gateway:latest    .
	docker build -f deploy/dockerfiles/Dockerfile.orchestrator -t ai-org/orchestrator:latest .
	docker build -f deploy/dockerfiles/Dockerfile.ws-hub    -t ai-org/ws-hub:latest     .
	docker build -f deploy/dockerfiles/Dockerfile.tenant    -t ai-org/tenant-svc:latest  .

docker-push: ## Push images to registry (set REGISTRY env var)
	docker push $(REGISTRY)/ai-org/gateway:latest
	docker push $(REGISTRY)/ai-org/orchestrator:latest
	docker push $(REGISTRY)/ai-org/ws-hub:latest
	docker push $(REGISTRY)/ai-org/tenant-svc:latest

## ── Clean ────────────────────────────────────────────────────────────────

clean: ## Remove build artifacts
	rm -rf bin/ coverage.out coverage.html
	$(GO) clean -cache
