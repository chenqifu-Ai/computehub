# ComputeHub v3.0 - Makefile
# 基于 OpenPC 工程规范

CGO_ENABLED ?= 0
GO          ?= go
GOFLAGS     ?= -trimpath -mod=readonly

TARGET_DIR  = bin
GATEWAY_BIN = $(TARGET_DIR)/computehub-gateway
TUI_BIN     = $(TARGET_DIR)/computehub-tui

.PHONY: all build-gateway build-tui test test-full clean help \
        run-gateway run-tui \
        install uninstall

all: build-gateway build-tui

# ─── 构建 ───

build-gateway:
	@echo "🔨 Building ComputeHub Gateway..."
	@mkdir -p $(TARGET_DIR)
	CGO_ENABLED=$(CGO_ENABLED) $(GO) build $(GOFLAGS) -o $(GATEWAY_BIN) main.go
	@echo "✅ Gateway built: $(GATEWAY_BIN)"

build-tui:
	@echo "🔨 Building ComputeHub TUI..."
	@mkdir -p $(TARGET_DIR)
	CGO_ENABLED=$(CGO_ENABLED) $(GO) build $(GOFLAGS) -o $(TUI_BIN) tui.go
	@echo "✅ TUI built: $(TUI_BIN)"

build: build-gateway build-tui

# ─── 运行 ───

run-gateway:
	@./$(GATEWAY_BIN) serve

run-tui:
	@./$(TUI_BIN)

# ─── 测试 ───

test:
	@echo "🧪 Running unit tests..."
	CGO_ENABLED=$(CGO_ENABLED) $(GO) test -v -count=1 ./src/kernel/... ./src/pure/... ./src/executor/... ./src/gene/... ./src/gateway/...

test-full: build test
	@echo "🔗 Running full integration tests..."
	@./scripts/test-full-loop.sh

test-coverage:
	@echo "📊 Generating test coverage..."
	CGO_ENABLED=$(CGO_ENABLED) $(GO) test -coverprofile=coverage.out -count=1 ./src/...
	@echo "Coverage report:"
	CGO_ENABLED=$(CGO_ENABLED) $(GO) tool cover -func=coverage.out

# ─── 清理 ───

clean:
	@echo "🧹 Cleaning..."
	rm -rf $(TARGET_DIR)
	rm -f coverage.out
	find . -name "*.test" -delete
	@echo "✅ Cleaned."

# ─── 帮助 ───

help:
	@echo "ComputeHub v3.0 - Makefile Targets"
	@echo ""
	@echo "  build           Build gateway + TUI binaries"
	@echo "  build-gateway   Build gateway only"
	@echo "  build-tui       Build TUI only"
	@echo "  run-gateway     Run gateway (./bin/computehub-gateway serve)"
	@echo "  run-tui         Run TUI (./bin/computehub-tui)"
	@echo "  test            Run unit tests"
	@echo "  test-full       Build + test + integration tests"
	@echo "  test-coverage   Generate coverage report"
	@echo "  clean           Remove build artifacts"
	@echo "  help            Show this help"
	@echo ""
	@echo "  Flags:"
	@echo "    CGO_ENABLED=1  Enable CGO (default: 0 for ARM64 compatibility)"
