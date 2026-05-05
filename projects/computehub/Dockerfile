# ==============================================================
# ComputeHub Gateway — Docker 生产构建
# 多阶段构建: golang 编译 → alpine 运行
# ==============================================================

# ---- Stage 1: Build ----
FROM golang:1.24-alpine AS builder

# 系统依赖
RUN apk add --no-cache gcc musl-dev ca-certificates tzdata

# 工作目录
WORKDIR /build

# 依赖层缓存优化：先拷 go.mod/go.sum
COPY go.mod go.sum ./
RUN go mod download && go mod verify

# 拷贝源码
COPY . .

# 编译（静态链接 + 剥离符号表）
ARG LDFLAGS="-s -w -X main.version=dev -X main.buildTime=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN CGO_ENABLED=0 go build \
    -ldflags="$LDFLAGS" \
    -o /build/computehub-gateway \
    ./cmd/gateway/

# 验证二进制
RUN chmod +x /build/computehub-gateway && \
    /build/computehub-gateway --version 2>/dev/null || true

# ---- Stage 2: Runtime ----
FROM alpine:3.20 AS runtime

LABEL org.opencontainers.image.title="ComputeHub Gateway"
LABEL org.opencontainers.image.description="Deterministic Computing Power Scheduling Platform"
LABEL org.opencontainers.image.vendor="ComputeHub"

# 非 root 用户
RUN addgroup -S computehub && adduser -S computehub -G computehub

WORKDIR /app

# 从 builder 拷贝
COPY --from=builder --chown=computehub:computehub /build/computehub-gateway .
COPY --from=builder --chown=computehub:computehub /build/config.json ./config.json
COPY --from=builder --chown=computehub:computehub /build/genes.json ./genes.json
COPY --from=builder --chown=computehub:computehub /build/code/dashboard ./code/dashboard

# 创建必要目录
RUN mkdir -p /tmp/computehub-logs /tmp/computehub-sandbox /app/data && \
    chown -R computehub:computehub /app /tmp/computehub-logs /tmp/computehub-sandbox /app/data

# 端口
EXPOSE 8282

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:8282/api/health || exit 1

USER computehub

# 默认时区
ENV TZ=Asia/Shanghai

ENTRYPOINT ["./computehub-gateway"]
CMD ["--config", "/app/config.json"]
