# ═══════════════════════════════════════════════════════════════════════
# MoE Scoring Service — Rust Multi-Stage Dockerfile
# Stage 1: Build with Cargo (full toolchain)
# Stage 2: Minimal distroless runtime (~8MB final image)
# ═══════════════════════════════════════════════════════════════════════

# ── Stage 1: Build ────────────────────────────────────────────────────
FROM rust:1.77-slim AS builder

WORKDIR /app

# Install musl for fully static binary (no glibc dependency)
RUN apt-get update && apt-get install -y musl-tools && rm -rf /var/lib/apt/lists/*
RUN rustup target add x86_64-unknown-linux-musl

# Cache dependencies — copy manifests first
COPY Cargo.toml ./
RUN mkdir src && echo 'fn main(){}' > src/main.rs
RUN cargo build --release --target x86_64-unknown-linux-musl 2>/dev/null || true
RUN rm -rf src

# Build actual source
COPY src/ ./src/
RUN touch src/main.rs && \
    cargo build --release --target x86_64-unknown-linux-musl

# ── Stage 2: Minimal Runtime ──────────────────────────────────────────
FROM scratch AS runtime

# OCI labels
LABEL org.opencontainers.image.title="AI Org — MoE Scoring Service"
LABEL org.opencontainers.image.description="Rust MoE expert routing and scoring HTTP API"
LABEL org.opencontainers.image.version="1.0.0"

# Copy static binary
COPY --from=builder /app/target/x86_64-unknown-linux-musl/release/moe-scoring /moe-scoring

# CA certificates for HTTPS if needed
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

EXPOSE 8090

ENV MOE_PORT=8090
ENV RUST_LOG=moe_scoring=info,tower_http=warn

ENTRYPOINT ["/moe-scoring"]
