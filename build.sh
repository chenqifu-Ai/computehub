#!/bin/bash
# ComputeHub v3.0 - 统一构建脚本
# 基于 OpenPC 工程规范

set -e

CGO_ENABLED=${CGO_ENABLED:-0}
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="${PROJECT_DIR}/bin"

log() {
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[${timestamp}] $*"
}

case "${1:-build}" in
    build)
        log "🔨 Building ComputeHub v3.0..."
        mkdir -p "${TARGET_DIR}"
        
        log "  → Gateway..."
        CGO_ENABLED=${CGO_ENABLED} go build -trimpath -mod=readonly -o "${TARGET_DIR}/computehub-gateway" main.go
        log "  ✅ Gateway: ${TARGET_DIR}/computehub-gateway"
        
        log "  → TUI..."
        CGO_ENABLED=${CGO_ENABLED} go build -trimpath -mod=readonly -o "${TARGET_DIR}/computehub-tui" tui.go
        log "  ✅ TUI: ${TARGET_DIR}/computehub-tui"
        
        log "✅ Build complete."
        ;;
    
    clean)
        log "🧹 Cleaning..."
        rm -rf "${TARGET_DIR}"
        rm -f coverage.out
        log "✅ Cleaned."
        ;;
    
    help)
        echo "Usage: ./build.sh [build|clean|help]"
        echo ""
        echo "  build   Build gateway + TUI (default)"
        echo "  clean   Remove build artifacts"
        echo "  help    Show this help"
        echo ""
        echo "  Environment:"
        echo "    CGO_ENABLED=0  Disable CGO (recommended for ARM64)"
        ;;
    
    *)
        echo "Unknown command: $1"
        echo "Usage: ./build.sh [build|clean|help]"
        exit 1
        ;;
esac
