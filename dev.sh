#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "🚀 Starting SARANG Research Swarm..."

# Kill existing processes on ports 8080 and 8000
echo "🧹 Cleaning up old processes..."
fuser -k 8080/tcp 8000/tcp 2>/dev/null

# Start Python Agent Service in the background
echo "🧠 Starting Python Intelligence Swarm (Port 8000)..."
export PYTHONPATH=$PYTHONPATH:.
python3 agents_service/api/main.py > agents.log 2>&1 &

# Wait a moment for Python to warm up
sleep 2

# Start Go Gateway in the foreground
echo "🌐 Starting Go Gateway (Port 8080)..."
if [ -d "gateway" ]; then
    cd gateway && go run cmd/gateway/main.go
else
    echo "❌ Error: Could not find gateway directory in $SCRIPT_DIR"
    exit 1
fi
