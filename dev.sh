#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# ── 1. Install & Build ──────────────────────────────────────────────
echo "📦 checking dependencies..."
if [ -d "venv" ]; then source venv/bin/activate; fi
pip install -q -r requirements.txt

echo "🏗️  building go gateway..."
cd gateway && go build -o sarang-gateway main.go && cd ..

# ── 2. Start Services ───────────────────────────────────────────────
echo "🚀 launching sarang swarm..."

# Go Gateway (Port 8080)
nohup ./gateway/sarang-gateway > gateway.log 2>&1 &
echo "  [✓] Go Gateway Active (8080)"

# Python Intelligence API (Port 8000)
export PYTHONPATH=$PYTHONPATH:.
nohup python3 agents_service/api/main.py > agents.log 2>&1 &
echo "  [✓] Python API Active (8000)"

# LangGraph Swarm Worker (Background)
nohup python3 agents_service/api/swarm_worker.py > worker.log 2>&1 &
echo "  [✓] Swarm Worker Active (LangGraph)"

# ── 3. Start Dashboard ──────────────────────────────────────────────
echo "🖥️  Starting Next.js Dashboard (3000)..."
cd dashboard && npm run dev

