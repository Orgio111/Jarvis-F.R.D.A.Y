FROM golang:1.25-alpine AS builder

WORKDIR /build

# Install build dependencies
RUN apk add --no-cache git ca-certificates

# Cache dependencies
COPY go.mod go.sum* ./
RUN go mod download

# Build
COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -ldflags="-s -w -extldflags '-static'" \
    -o /bin/gateway ./cmd/gateway

# ─── Runtime ──────────────────────────────────────────────────────────────────
FROM alpine:3.20

RUN apk add --no-cache ca-certificates wget

COPY --from=builder /bin/gateway /gateway

EXPOSE 8000

ENTRYPOINT ["/gateway"]
