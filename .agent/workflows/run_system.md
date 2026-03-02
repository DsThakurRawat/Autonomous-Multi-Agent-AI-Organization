---
description: How to run the Autonomous Multi-Agent AI Organization system
---

# Workflow: Running the AI Company in a Box

## Prerequisites

- Python 3.11+
- Docker + Docker Compose
- Git
- (Optional) AWS CLI configured for real deployment

## Step 1: Set up Python environment

// turbo

```bash
cd "/home/divyansh-rawat/Autonomous Multi-Agent AI Organization" && python3 -m venv venv && source venv/bin/activate && pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy asyncpg networkx structlog rich tenacity python-jose passlib python-dotenv httpx
```

## Step 2: Copy environment file

// turbo

```bash
cp "/home/divyansh-rawat/Autonomous Multi-Agent AI Organization/.env.example" "/home/divyansh-rawat/Autonomous Multi-Agent AI Organization/.env"
```

## Step 3: Run the demo (no AWS/API keys needed)

// turbo

```bash
cd "/home/divyansh-rawat/Autonomous Multi-Agent AI Organization" && source venv/bin/activate && python run_demo.py "Build a SaaS platform for student internship tracking"
```

## Step 4: Open the dashboard

Open the file in your browser:

```
/home/divyansh-rawat/Autonomous Multi-Agent AI Organization/dashboard/index.html
```

Then click any idea chip and click Launch.

## Step 5: Start orchestrator API server

```bash
cd "/home/divyansh-rawat/Autonomous Multi-Agent AI Organization" && source venv/bin/activate && uvicorn api.main:app --port 8080 --reload
```

## Step 6: (Optional) Full Docker stack

```bash
cd "/home/divyansh-rawat/Autonomous Multi-Agent AI Organization" && docker-compose up --build
```

## Step 7: (Production) Deploy to AWS

1. Configure .env with AWS credentials
2. Run `./infrastructure/scripts/deploy.sh`
3. Monitor at CloudWatch dashboard
