# 🚀 Oracle Cloud Free Tier Deployment Guide

Deploy the **entire Autonomous Multi-Agent AI Organization** stack for free on Oracle Cloud using their **Ampere A1** VM (4 OCPUs, 24GB RAM — permanently free).

## Architecture

```
You → Cloudflare (WAF + SSL) → Oracle VM → Docker Compose Stack
                                                ├── dashboard:3000
                                                ├── api-gateway:8080
                                                ├── ws-hub:8081
                                                ├── orchestrator:9091
                                                ├── agents (7x)
                                                ├── postgres
                                                ├── redis
                                                ├── kafka
                                                └── qdrant
```

---

## Part 1: Provision Oracle VM

1. Sign up at [cloud.oracle.com](https://cloud.oracle.com) (free, no credit card required after initial verification)
2. Go to **Compute → Instances → Create Instance**
3. Configure:
   - **Shape**: `VM.Standard.A1.Flex` → 4 OCPUs, 24 GB RAM
   - **OS**: Ubuntu 22.04 (aarch64)
   - **Boot volume**: 100 GB
   - **Networking**: Create a VCN, assign a Public IP
4. Download the SSH key `.pem` file when prompted
5. Note your VM's **Public IP address**

### Open Firewall Ports (just for Cloudflare Tunnel — no public ports needed)
```bash
# In Oracle Console → Networking → VCN → Security Lists
# Add Ingress rule: TCP port 22 (SSH) from 0.0.0.0/0
# That's all! Cloudflare Tunnel handles all other traffic.
```

---

## Part 2: Set Up the VM

```bash
# SSH into the VM
ssh -i your-key.pem ubuntu@YOUR_VM_IP

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
newgrp docker

# Install Docker Compose
sudo apt-get install -y docker-compose-plugin

# Install git
sudo apt-get install -y git

# Clone the repo
sudo mkdir -p /opt/ai-org
sudo chown ubuntu:ubuntu /opt/ai-org
git clone https://github.com/DsThakurRawat/Autonomous-Multi-Agent-AI-Organization.git /opt/ai-org
cd /opt/ai-org

# Set up environment
cp .env.prod.example .env
nano .env   # Fill in all your real values
```

---

## Part 3: Generate Required Keys

```bash
cd /opt/ai-org

# JWT RSA keys (for auth)
mkdir -p keys
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem

# Strong passwords
echo "POSTGRES_PASSWORD=$(openssl rand -base64 24)" >> .env
echo "GRAFANA_PASSWORD=$(openssl rand -base64 16)" >> .env
echo "KEY_ENCRYPTION_KEY=$(openssl rand -hex 32)" >> .env
echo "NEXTAUTH_SECRET=$(openssl rand -base64 32)" >> .env
```

---

## Part 4: Set Up Cloudflare Tunnel

1. Log into [Cloudflare Zero Trust](https://one.dash.cloudflare.com)
2. Go to **Networks → Tunnels → Create Tunnel**
3. Name it `ai-org-production`
4. Copy the **Tunnel Token**
5. Add to your `.env`: `TUNNEL_TOKEN=your_token_here`
6. In the tunnel, create these **Public Hostname** routes:

| Subdomain | Service |
|---|---|
| `ai-org.yourdomain.com` | `http://dashboard:3000` |
| `api.yourdomain.com` | `http://api-gateway:8080` |
| `ws.yourdomain.com` | `http://ws-hub:8081` |
| `grafana.yourdomain.com` | `http://grafana:3000` |
| `kafka.yourdomain.com` | `http://kafka-ui:8080` |

> For sensitive tools (grafana, kafka-ui), go to **Access → Applications** and add an email policy to require login.

---

## Part 5: Start the Stack

```bash
cd /opt/ai-org

# Start everything (production mode with Cloudflare Tunnel)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check all services are up
docker compose ps

# Watch logs
docker compose logs -f api-gateway orchestrator
```

---

## Part 6: CI/CD Auto-Deploy (GitHub Actions)

Add these secrets to your GitHub repository (**Settings → Secrets → Actions**):

| Secret | Value |
|---|---|
| `ORACLE_HOST` | Your VM's public IP |
| `ORACLE_USER` | `ubuntu` |
| `ORACLE_SSH_KEY` | Contents of your `.pem` key file |
| `ORACLE_DOMAIN` | `ai-org.yourdomain.com` |

Every push to `main` will now automatically SSH into your Oracle VM and redeploy!

---

## Useful Commands

```bash
# View all service status
docker compose ps

# Restart a single service
docker compose restart api-gateway

# View real-time logs
docker compose logs -f

# Pull latest code and redeploy manually
cd /opt/ai-org && git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Check system resources
docker stats
htop
```

---

## Cost Summary

| Service | Cost |
|---|---|
| Oracle Cloud A1 VM (4 OCPU, 24GB) | **$0/month forever** |
| Cloudflare Tunnel | **$0/month forever** |
| Cloudflare WAF + CDN | **$0/month (free plan)** |
| **Total** | **$0/month** |
