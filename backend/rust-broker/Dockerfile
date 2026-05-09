FROM rust:1.78-slim AS builder

WORKDIR /build

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Cache Cargo registry
COPY Cargo.toml Cargo.lock* ./
RUN mkdir src && echo "fn main() {}" > src/main.rs && cargo build --release
RUN rm -rf src

# Build
COPY src/ ./src/
RUN touch src/main.rs && cargo build --release

# ─── Runtime ──────────────────────────────────────────────────────────────────
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/target/release/jarvis-broker /jarvis-broker

EXPOSE 8200

ENTRYPOINT ["/jarvis-broker"]
