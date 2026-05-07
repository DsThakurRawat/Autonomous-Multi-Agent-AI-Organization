#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

echo "🧹 Cleaning up old SARANG processes..."
fuser -k 8000/tcp 3000/tcp 2>/dev/null
pkill -f "python3 agents_service/api/main.py" 2>/dev/null
sleep 1

echo "🚀 Starting SARANG Research Swarm..."

# Check for existing services
for port in 8000 3000; do
    if lsof -i :$port -t &>/dev/null; then
        echo "⚠️  Port $port still in use. Kill it: fuser -k ${port}/tcp"
    fi
done

# Install Python dependencies
echo "📦 Checking Python dependencies..."
if [ -d "venv" ]; then
    source venv/bin/activate
fi
pip install -q -r requirements.txt 2>/dev/null

# Start Python Intelligence Engine (Port 8000)
echo "🧠 Starting Python Intelligence Engine (Port 8000)..."
export PYTHONPATH=$PYTHONPATH:.
nohup python3 agents_service/api/main.py > agents.log 2>&1 &
echo "  Python Brain Active (PID: $!)"

# Wait for Python to come up
sleep 2

# Start Next.js Dashboard (Port 3000)
echo "🖥️  Starting Next.js Dashboard (Port 3000)..."
if [ -d "dashboard" ]; then
    cd dashboard && npm run dev
else
    echo "❌ Error: Could not find dashboard directory."
    exit 1
fi
