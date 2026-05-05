# ==============================================================
# ComputeHub Makefile
# ==============================================================

BINARY_NAME = computehub-gateway
TUI_NAME = computehub-tui
WORKER_NAME = compute-worker
VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
BUILD_TIME = $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
LDFLAGS = -s -w -X main.version=$(VERSION) -X main.buildTime=$(BUILD_TIME)

# Go
GO = go
GOFLAGS = -v
CGO_ENABLED = 0

# Docker
DOCKER = docker
COMPOSE = docker compose

.PHONY: all build build-tui build-worker clean test test-all help \
        docker-up docker-down docker-logs docker-build docker-push \
        prod-up prod-down load-test lint vet

# ==============================================================
# 编译
# ==============================================================

all: build build-tui build-worker

build:
	CGO_ENABLED=$(CGO_ENABLED) $(GO) build $(GOFLAGS) \
		-ldflags "$(LDFLAGS)" \
		-o code/bin/$(BINARY_NAME) ./cmd/gateway/

build-tui:
	CGO_ENABLED=$(CGO_ENABLED) $(GO) build $(GOFLAGS) \
		-ldflags "$(LDFLAGS)" \
		-o code/bin/$(TUI_NAME) ./cmd/tui/

build-worker:
	CGO_ENABLED=$(CGO_ENABLED) $(GO) build $(GOFLAGS) \
		-ldflags "$(LDFLAGS)" \
		-o code/bin/$(WORKER_NAME) ./cmd/worker/

# ==============================================================
# 测试
# ==============================================================

test:
	$(GO) test ./... -v -short

test-all:
	$(GO) test ./... -v -count=1

test-scheduler:
	$(GO) test ./src/scheduler/... -v -count=1

test-kernel:
	$(GO) test ./src/kernel/... -v -count=1

test-gateway:
	$(GO) test ./src/gateway/... -v -count=1

# ==============================================================
# Docker
# ==============================================================

docker-build:
	$(DOCKER) build -t computehub/gateway:$(VERSION) .

docker-up:
	$(COMPOSE) up -d

docker-down:
	$(COMPOSE) down

docker-logs:
	$(COMPOSE) logs -f gateway

docker-push: docker-build
	$(DOCKER) push computehub/gateway:$(VERSION)

prod-up:
	$(COMPOSE) -f docker-compose.prod.yml up -d

prod-down:
	$(COMPOSE) -f docker-compose.prod.yml down

# ==============================================================
# 生产压测
# ==============================================================

load-test:
	python3 scripts/load_test.py --target localhost:8282 --report load-test-report-$(shell date +%Y%m%d-%H%M).json

load-test-all:
	python3 scripts/load_test.py --target localhost:8282 \
		--concurrency 50 100 200 400 500 \
		--report load-test-report-$(shell date +%Y%m%d-%H%M).json

# ==============================================================
# 代码质量
# ==============================================================

vet:
	$(GO) vet ./...

lint:
	@golangci-lint run ./... 2>/dev/null || echo "golangci-lint not installed, skipping"

format:
	$(GO) fmt ./...

# ==============================================================
# 清理
# ==============================================================

clean:
	rm -rf code/bin/
	rm -f $(BINARY_NAME) $(TUI_NAME) $(WORKER_NAME)
	$(DOCKER) system prune -f 2>/dev/null || true

# ==============================================================
# 帮助
# ==============================================================

help:
	@echo "ComputeHub Build System"
	@echo ""
	@echo "Commands:"
	@echo "  build         编译 Gateway"
	@echo "  build-tui     编译 TUI"
	@echo "  build-worker  编译 Worker Agent"
	@echo "  test          运行短测试"
	@echo "  test-all      运行全部测试"
	@echo "  docker-build  构建 Docker 镜像"
	@echo "  docker-up     启动 Docker 服务"
	@echo "  prod-up       启动生产环境"
	@echo "  load-test     运行压测"
	@echo "  clean         清理构建产物"
	@echo "  help          显示帮助"
