# ==============================================================
# ComputeHub Gateway — Docker 部署
# 多阶段构建: 先编译再打包
# ==============================================================

# ---- Stage 1: Build ----
FROM golang:1.24-alpine AS builder

RUN apk add --no-cache gcc musl-dev

WORKDIR /build

# 先拷 go.mod/go.sum 缓存依赖
COPY go.mod go.sum ./
RUN go mod download

# 拷贝源码
COPY cmd/ ./cmd/
COPY src/ ./src/
COPY config.json ./config.json
COPY genes.json ./genes.json

# 编译（CGO_ENABLED=0 保证静态链接，alpine 下可执行）
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /build/computehub-gateway ./cmd/gateway/

# ---- Stage 2: Runtime ----
FROM alpine:3.20

RUN apk add --no-cache ca-certificates tzdata

# 应用目录
WORKDIR /app

# 拷贝二进制 + 配置文件
COPY --from=builder /build/computehub-gateway .
COPY --from=builder /build/config.json .
COPY --from=builder /build/genes.json .

# 创建 sandbox 目录
RUN mkdir -p /tmp/opc-sandbox

# 端口
EXPOSE 8282

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:8282/api/health || exit 1

ENTRYPOINT ["./computehub-gateway"]
