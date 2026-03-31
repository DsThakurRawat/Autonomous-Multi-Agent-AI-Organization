#!/bin/bash
# Proximus-Nova AWS EC2 Deployment Script
# Automatically syncs code and runs Docker Compose on a target EC2 instance.

set -e

if [[ -z "$EC2_HOST" || -z "$SSH_KEY_PATH" ]]; then
    echo "[!] Error: Missing required environment variables."
    echo "Usage: EC2_HOST=ec2-user@<ip> SSH_KEY_PATH=~/.ssh/my-key.pem ./deploy.sh"
    exit 1
fi

echo "==============================================="
echo " Deploying Proximus-Nova Backend to EC2        "
echo "==============================================="

echo "[*] Setting up remote directory on $EC2_HOST..."
ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no "$EC2_HOST" "mkdir -p ~/proximus-nova"

echo "[*] Syncing files via RSYNC..."
# Exclude heavy/local folders
rsync -avz --exclude 'venv' --exclude 'node_modules' --exclude '.git' --exclude '.next' \
    -e "ssh -i $SSH_KEY_PATH -o StrictHostKeyChecking=no" \
    "../../" "$EC2_HOST":~/proximus-nova/

echo "[*] Starting Docker Compose on remote EC2 host..."
ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no "$EC2_HOST" << 'EOF'
    cd ~/proximus-nova
    # Ensure Docker is running
    sudo systemctl start docker || true
    
    # We use docker-compose.yml which has the backend + python agents + infra dependencies
    sudo docker compose up -d --build
EOF

echo "[*] Deployment Complete! Services are now booting on $EC2_HOST."
