# =============================================================================
# ComputeHub — 多阶段构建 Dockerfile
# =============================================================================
# 构建:
#   docker build -t computehub:latest .
#   docker build --build-arg TARGETARCH=arm64 -t computehub:arm64 .
#
# 运行 Gateway:
#   docker run -p 8282:8282 -v /path/to/config.json:/app/config.json computehub:latest gateway
#
# 运行 Worker:
#   docker run computehub:latest worker --gw http://gateway:8282 --node-id docker-worker
# =============================================================================

# ── Stage 1: Build ──
FROM golang:1.24-alpine AS builder

ARG TARGETARCH=amd64
ARG VERSION=1.4.0

RUN apk add --no-cache git ca-certificates

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN GOARCH=${TARGETARCH} CGO_ENABLED=0 \
    go build -ldflags="-X github.com/computehub/opc/src/version.VERSION=${VERSION} -s -w" \
    -o /build/computehub ./cmd/computehub/

# ── Stage 2: Runtime ──
FROM alpine:3.20

RUN apk add --no-cache ca-certificates tzdata

WORKDIR /app
COPY --from=builder /build/computehub /app/computehub
COPY --from=builder /src/config.json /app/config.json
COPY --from=builder /src/web /app/web
COPY --from=builder /src/deploy /app/deploy

EXPOSE 8282

ENTRYPOINT ["/app/computehub"]
CMD ["gateway"]
