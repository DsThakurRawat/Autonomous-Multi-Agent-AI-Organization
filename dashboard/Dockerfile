# ═══════════════════════════════════════════════════════════════════════
# Dashboard — Next.js 14 Production Dockerfile
# Multi-stage: deps → builder → runner (standalone, minimal)
# Works on: linux/amd64 · linux/arm64 (Apple M1/M2)
# ═══════════════════════════════════════════════════════════════════════

FROM node:20-alpine AS base

# ── Stage 1: Install dependencies ───────────────────────────────────
FROM base AS deps
WORKDIR /app
RUN apk add --no-cache libc6-compat

COPY package*.json ./
RUN npm ci --only=production && \
    cp -R node_modules /prod_node_modules

RUN npm ci

# ── Stage 2: Build ───────────────────────────────────────────────────
FROM base AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG NEXT_PUBLIC_API_URL=http://localhost:8080
ARG NEXT_PUBLIC_WS_URL=ws://localhost:8080
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ── Stage 3: Runtime (minimal) ────────────────────────────────────────
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser  --system --uid 1001 nextjs

# Copy standalone output
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public 2>/dev/null || true

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
    CMD wget -q --spider http://localhost:3000 || exit 1

CMD ["node", "server.js"]
