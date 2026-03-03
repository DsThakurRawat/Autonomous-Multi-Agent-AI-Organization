# 🚀 Setup Guide — Cross-Platform

> Works on: Ubuntu · Debian · Arch · macOS · Windows 11 · Windows 10 (WSL2) · Raspberry Pi (ARM64)

---

## ⚡ Quickstart (All Platforms) — Docker Method

This is the **recommended method**. One command. Zero dependencies except Docker.

```bash
# 1. Clone
git clone https://github.com/DsThakurRawat/Autonomous-Multi-Agent-AI-Organization.git
cd "Autonomous Multi-Agent AI Organization"

# 2. Copy environment config
cp .env.example .env
# Then edit .env with your API keys (see section below)

# 3. Start everything
docker compose up -d

# 4. Open dashboard
open http://localhost:3000   # Mac
xdg-open http://localhost:3000  # Linux
# Windows: just open browser → http://localhost:3000
```

**That's it.** The full stack starts automatically:

- Dashboard at `http://localhost:3000`
- API at `http://localhost:8080`
- Kafka UI at `http://localhost:8888`
- Grafana at `http://localhost:3002`
- Prometheus at `http://localhost:9090`
- Jaeger at `http://localhost:16686`

---

## 🔑 Environment Variables (`.env`)

```bash
# LLM API Keys (at least one required for agents to work)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional: AWS (for cloud deployment)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1

# Optional: Pinecone (vector DB — uses local ChromaDB if not set)
PINECONE_API_KEY=
PINECONE_ENV=

# System (pre-filled defaults — don't change unless you know what you're doing)
POSTGRES_PASSWORD=aiorg_secret_2026
REDIS_PASSWORD=
KAFKA_MOCK=false
ENVIRONMENT=development
```

---

## 🐧 Linux (Ubuntu / Debian)

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose v2
sudo apt-get install -y docker-compose-plugin

# Verify
docker --version        # Docker 24+
docker compose version  # v2.x

# Start the project
docker compose up -d
```

**Other distros:**

- **Arch:** `sudo pacman -S docker docker-compose && sudo systemctl enable --now docker`
- **Fedora/RHEL:** `sudo dnf install docker-ce docker-compose-plugin`
- **Alpine:** `apk add docker docker-compose`

---

## 🍎 macOS (Intel + Apple Silicon M1/M2/M3)

```bash
# Install Docker Desktop — handles everything including ARM64
# Download from: https://www.docker.com/products/docker-desktop/

# Or via Homebrew
brew install --cask docker

# Start Docker Desktop from Applications, then:
docker compose up -d
```

> ✅ **Apple Silicon (M1/M2/M3):** All Docker images include `linux/arm64` support. No changes needed.

---

## 🪟 Windows

### Option A: Docker Desktop (Recommended)

```powershell
# 1. Install Docker Desktop from: https://www.docker.com/products/docker-desktop/
# 2. Enable WSL2 integration in Docker Desktop settings
# 3. Open PowerShell or Windows Terminal:
docker compose up -d
# 4. Open browser: http://localhost:3000
```

### Option B: WSL2 (Ubuntu inside Windows)

```powershell
# Install WSL2 with Ubuntu
wsl --install -d Ubuntu

# Inside WSL2 terminal:
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Then follow the Linux instructions above
```

---

## 🔧 Native Python Setup (No Docker — Advanced)

Use this if you want to develop without Docker, or run individual services.

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- (Optional) Kafka

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and configure env
cp .env.example .env

# Start dependencies (if not using Docker)
# Option: run Postgres + Redis via Docker only
docker compose up -d postgres redis

# Run the API server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8080

# In a second terminal, run the demo
python run_demo.py
```

---

## 🔁 Common Commands

```bash
# Start everything
docker compose up -d

# View logs (all services)
docker compose logs -f

# View logs (specific service)
docker compose logs -f orchestrator

# Stop everything (keeps data)
docker compose down

# Stop + delete all data (fresh start)
docker compose down -v

# Rebuild after code changes
docker compose up -d --build

# Run tests
docker compose exec orchestrator python -m pytest tests/ -v

# Open an agent shell
docker compose exec orchestrator bash
```

---

## 🌐 Cloud Deployment (AWS)

```bash
# Prerequisites: AWS CLI, kubectl, Helm, Terraform

# 1. Provision infrastructure
cd infrastructure/terraform
terraform init
terraform apply

# 2. Configure kubectl
aws eks update-kubeconfig --name ai-org-eks --region us-east-1

# 3. Deploy with Helm
helm upgrade --install ai-org ./helm/ai-org \
  --namespace ai-org --create-namespace \
  --set global.environment=production

# 4. Get the public URL
kubectl get service api-gateway -n ai-org
```

---

## ❓ Troubleshooting

| Problem | Fix |
|---------|-----|
| `Port already in use` | `docker compose down` then retry |
| `Permission denied /var/run/docker.sock` | `sudo usermod -aG docker $USER && newgrp docker` |
| Slow on Mac M1/M2 | Normal on first pull (downloading ARM64 images). Subsequent starts are fast. |
| Kafka not starting | Give it 30s — Zookeeper starts first. Check: `docker compose logs kafka` |
| Agents not thinking | Check `OPENAI_API_KEY` in `.env` — without it, agents use fallback stubs |
| Out of disk space | `docker system prune -a` (removes unused images) |
