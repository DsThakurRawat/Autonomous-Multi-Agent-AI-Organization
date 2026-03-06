# Option B (SaaS) Ultra-Budget Deployment Roadmap

Deploying a multi-agent system with Kafka, Postgres, Redis, and a Go+Next.js microservice architecture is notoriously resource-heavy. Doing this on managed AWS (like EKS for Kubernetes, MSK for Kafka, and RDS for Postgres) or standard Terraform setups will easily cost **₹20,000 to ₹40,000+ per month**, far exceeding a ₹5,000/year budget.

However, **there is a way to deploy Option B (SaaS) for effectively ₹0 to ₹1,000 per year.**

To do this, we must completely abandon managed AWS services and Kubernetes. Instead, we will use a **Single-Node Docker Compose** approach on a high-tier "Always Free" Virtual Private Server (VPS).

### 🌟 The "Always Free" Secret: Oracle Cloud

Most free tiers (like AWS EC2 Micro) only give you 1GB of RAM, which will instantly crash when you try to start Apache Kafka.

**Oracle Cloud** has a hidden gem called the **"Always Free Ampere A1 Compute"**. They give you:

* **4 ARM CPU Cores**
* **24 GB of RAM**
* **200 GB Storage**
* *Cost: 100% Free Forever.*

24GB of RAM is more than enough to run the entire Option B stack (all Go services, Kafka, Postgres, Redis, the Dashboard, and the 7 Python Agents).

---

### 🗺️ The Ultra-Budget Roadmap for Option B (SaaS)

#### Phase 1: Infrastructure & Domain (Cost: ~₹500 - ₹800 / year)

1. **Get the Server:** Sign up for **Oracle Cloud** and create the Always Free ARM instance (24GB RAM). Install Ubuntu 22.04 LTS on it.
2. **Buy a Cheap Domain:** Go to Hostinger or Namecheap and buy a `.in`, `.xyz`, or `.tech` domain. This will cost you around ₹500/year. Let's assume it's `my-ai-org.in`.
3. **Free SSL & DNS:** Sign up for a **Cloudflare (Free Tier)** account. Point your domain there. Point the DNS A-Record to your new Oracle Cloud Server IP.

#### Phase 2: Server Prep (Cost: ₹0)

1. SSH into your Oracle server.
2. Install **Docker** and **Docker Compose**.
3. *Optional but recommended:* Set up a 4GB Swapfile to prevent out-of-memory errors just in case Docker goes rogue.
4. Clone your repository onto the server.

#### Phase 3: Setup Google Auth & HTTPS (Cost: ₹0)

1. Go to the **Google Cloud Console**.
2. Create an OAuth Application.
3. Set the authorized redirect URI to: `https://my-ai-org.in/v1/auth/google/callback`.
4. Grab your `Client ID` and `Client Secret`.
5. Note: Since Cloudflare is handling your SSL, it will automatically upgrade your traffic to `https://`, meaning Google Auth will accept it.

#### Phase 4: Configure and Launch (Cost: ₹0)

On your server, configure your `.env` file (the Option B SaaS configuration):

```bash
cd "Autonomous Multi-Agent AI Organization"
cp .env.example .env

# Generate your JWT RSA Keys
mkdir -p keys
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem

# Generate encryption key
openssl rand -hex 32
```

Edit your `.env` and fill it out:

* `AUTH_DISABLED=false`
* `GOOGLE_CLIENT_ID=<your-google-client-id>`
* `GOOGLE_CLIENT_SECRET=<your-google-secret>`
* `GOOGLE_REDIRECT_URL=https://my-ai-org.in/v1/auth/google/callback`

Finally, run the SaaS compose file to boot the entire system:

```bash
docker-compose -f go-backend/deploy/docker-compose.yml up -d --build
```

### Summary of Costs

* **AWS/Kubernetes Route:** ₹3,00,000+ / year ❌
* **Oracle Cloud + Cloudflare + Docker Compose Route:** ₹500 / year (just the domain name!) ✅
