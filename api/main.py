"""
Main API Server — Orchestrator Control Plane
FastAPI application that exposes the orchestrator to the world.
Provides REST API + WebSocket for real-time agent event streaming.
"""

import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import UTC, datetime
import os
import time
from typing import Any

import boto3
from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Security,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from google import genai
from pydantic import BaseModel, Field
import structlog

from agents.ceo_agent import CEOAgent
from agents.cto_agent import CTOAgent
from agents.devops_agent import DevOpsAgent
from agents.engineer_agent import EngineerAgent
from agents.finance_agent import FinanceAgent
from agents.model_registry import get_default
from agents.qa_agent import QAAgent
from agents.roles import AgentRole
from orchestrator.planner import ExecutionEvent, OrchestratorEngine

logger = structlog.get_logger(__name__)

# ── Dynamic LLM Setup ──────────────────────────────────────────────

load_dotenv()

# clients
gemini_client = None
bedrock_client = None

# ── Google Gemini Setup ──────────────────────────────────────────
gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if gemini_key and gemini_key != "your-gemini-key" and not gemini_key.startswith("AIza"):
    gemini_client = genai.Client(api_key=gemini_key)
    logger.info("Google Gemini client initialized")

# ── Amazon Bedrock Setup ──────────────────────────────────────────
aws_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_REGION", "us-east-1")

if aws_key and aws_key != "your-access-key-id":
    bedrock_client = boto3.client(
        "bedrock-runtime",
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
        region_name=aws_region,
    )
    logger.info("Amazon Bedrock (Nova) client initialized", region=aws_region)
else:
    logger.warning(
        "No AWS Bedrock credentials found. Agents will fall back to Gemini or Mock."
    )


# ── Global Orchestrator ────────────────────────────────────────────
orchestrator = OrchestratorEngine(budget_usd=200.0, output_dir="./output")


# ── Security Setup ─────────────────────────────────────────────────
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """Dependency to enforce X-API-Key header authentication."""
    expected_key = os.getenv("API_KEY")
    if not expected_key:
        logger.warning("API_KEY environment variable is not set. All secure requests will be rejected.")
        raise HTTPException(status_code=403, detail="Server misconfiguration: No API key defined")

    if api_key != expected_key:
        raise HTTPException(status_code=403, detail="Could not validate API key")
    return api_key


# ── WebSocket Connection Manager ───────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
        logger.info("WebSocket connected", project_id=project_id)

    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            self.active_connections[project_id].remove(websocket)

    async def broadcast(self, project_id: str, data: dict[str, Any]):
        if project_id not in self.active_connections:
            return
        dead = []
        for ws in self.active_connections[project_id]:
            try:
                # Issue #25: Prevent slow clients from freezing the event loop
                await asyncio.wait_for(ws.send_json(data), timeout=0.5)
            except TimeoutError:
                logger.warning("WebSocket broadcast timeout, dropping message", project_id=project_id)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active_connections[project_id].remove(ws)


manager = ConnectionManager()


# ── App Lifecycle ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Register all agents on startup using model_registry defaults."""

    def get_agent_config(role: str):
        config = get_default(role)
        provider = config["provider"]
        model = config["model"]

        client = None
        if provider == "google":
            client = gemini_client
        elif provider == "bedrock":
            client = bedrock_client

        return client, model, provider

    # CEO
<<<<<<< Updated upstream
    client, model, provider = get_agent_config(AgentRole.CEO)
    orchestrator.register_agent(AgentRole.CEO, CEOAgent(llm_client=client, model_name=model, provider=provider))

    # CTO
    client, model, provider = get_agent_config(AgentRole.CTO)
    orchestrator.register_agent(AgentRole.CTO, CTOAgent(llm_client=client, model_name=model, provider=provider))

    # Backend Engineer
    client, model, provider = get_agent_config(AgentRole.ENGINEER_BACKEND)
    orchestrator.register_agent(AgentRole.ENGINEER_BACKEND, EngineerAgent(mode="backend", llm_client=client, model_name=model, provider=provider))

    # Frontend Engineer
    client, model, provider = get_agent_config(AgentRole.ENGINEER_FRONTEND)
    orchestrator.register_agent(AgentRole.ENGINEER_FRONTEND, EngineerAgent(mode="frontend", llm_client=client, model_name=model, provider=provider))

    # QA
    client, model, provider = get_agent_config(AgentRole.QA)
    orchestrator.register_agent(AgentRole.QA, QAAgent(llm_client=client, model_name=model, provider=provider))

    # DevOps
    client, model, provider = get_agent_config(AgentRole.DEVOPS)
    orchestrator.register_agent(AgentRole.DEVOPS, DevOpsAgent(llm_client=client, model_name=model, provider=provider))

    # Finance
    client, model, provider = get_agent_config(AgentRole.FINANCE)
    orchestrator.register_agent(AgentRole.FINANCE, FinanceAgent(llm_client=client, model_name=model, provider=provider))
=======
    client, model, provider = get_agent_config("CEO")
    orchestrator.register_agent(
        "CEO", CEOAgent(llm_client=client, model_name=model, provider=provider)
    )

    # CTO
    client, model, provider = get_agent_config("CTO")
    orchestrator.register_agent(
        "CTO", CTOAgent(llm_client=client, model_name=model, provider=provider)
    )

    # Backend Engineer
    client, model, provider = get_agent_config("Engineer_Backend")
    orchestrator.register_agent(
        "Engineer_Backend",
        EngineerAgent(
            mode="backend", llm_client=client, model_name=model, provider=provider
        ),
    )

    # Frontend Engineer
    client, model, provider = get_agent_config("Engineer_Frontend")
    orchestrator.register_agent(
        "Engineer_Frontend",
        EngineerAgent(
            mode="frontend", llm_client=client, model_name=model, provider=provider
        ),
    )

    # QA
    client, model, provider = get_agent_config("QA")
    orchestrator.register_agent(
        "QA", QAAgent(llm_client=client, model_name=model, provider=provider)
    )

    # DevOps
    client, model, provider = get_agent_config("DevOps")
    orchestrator.register_agent(
        "DevOps", DevOpsAgent(llm_client=client, model_name=model, provider=provider)
    )

    # Finance
    client, model, provider = get_agent_config("Finance")
    orchestrator.register_agent(
        "Finance", FinanceAgent(llm_client=client, model_name=model, provider=provider)
    )
>>>>>>> Stashed changes

    logger.info("All agents registered and ready")
    yield


# ── FastAPI App ────────────────────────────────────────────────────
app = FastAPI(
    title="🏢 Autonomous Multi-Agent AI Organization",
    description="AI Company in a Box — Control Plane API",
    version="1.0.0",
    docs_url="/api/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Simple In-Memory Rate Limiter ──────────────────────────────────
RATE_LIMIT_DURATION = 60
RATE_LIMIT_REQUESTS = 60
request_counts = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()

    # Fast prune old requests
    request_counts[client_ip] = [t for t in request_counts[client_ip] if now - t < RATE_LIMIT_DURATION]

    if len(request_counts[client_ip]) >= RATE_LIMIT_REQUESTS:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Please try again later."})

    request_counts[client_ip].append(now)
    return await call_next(request)


# ── Request/Response Models ────────────────────────────────────────
class StartProjectRequest(BaseModel):
    idea: str = Field(..., min_length=5, max_length=1000, description="The core business idea")
    budget: dict[str, Any] = Field(default_factory=lambda: {"max_cost_usd": 200.0})
    name: str | None = Field(default="", max_length=100)
    constraints: dict[str, Any] | None = None


# ── REST Endpoints ─────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "name": "🏢 Autonomous Multi-Agent AI Organization",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/api/docs",
        "dashboard": "/dashboard",
    }


@app.get("/health")
@app.get("/healthz")
async def health():
    return {
        "status": "healthy",
<<<<<<< Updated upstream
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime_seconds": 3600, # Mock uptime
=======
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": 3600,  # Mock uptime
>>>>>>> Stashed changes
        "agents": list(orchestrator._agent_registry.keys()),
        "active_projects": len(orchestrator._active_projects),
    }


@app.post("/v1/projects", status_code=202)
async def start_project(request: StartProjectRequest, api_key: str = Depends(verify_api_key)):
    """
    MAIN ENDPOINT: Submit a business idea and launch the AI company.
    Returns a project_id for WebSocket streaming and status polling.
    """
    if len(request.idea.strip()) < 5:
        raise HTTPException(status_code=400, detail="Idea too short")

    # Wire up WebSocket event broadcasting
    async def broadcast_event(event: ExecutionEvent):
        await manager.broadcast(project_id, event.to_dict())

    project_id = await orchestrator.start_project(
<<<<<<< Updated upstream
        business_idea=request.idea,
        user_constraints=request.constraints or {}
=======
        business_idea=request.idea, user_constraints=request.constraints or {}
>>>>>>> Stashed changes
    )

    # Subscribe the event broadcaster for this project
    orchestrator.subscribe_events(broadcast_event)

    logger.info("Project started via API", project_id=project_id)
    # Match Dashboard Project interface
    return {
        "id": project_id,
        "name": request.name or "New Project",
        "description": request.idea,
        "status": "running",
        "budget_usd": request.budget.get("max_cost_usd", 200.0),
        "spent_usd": 0.0,
        "progress_pct": 0,
        "tasks_total": 0,
        "tasks_done": 0,
<<<<<<< Updated upstream
        "created_at": datetime.now(UTC).isoformat()
=======
        "created_at": datetime.utcnow().isoformat(),
>>>>>>> Stashed changes
    }


@app.get("/v1/projects/{project_id}")
async def get_project_status(project_id: str, api_key: str = Depends(verify_api_key)):
    """Get full project status including task graph, cost, and artifacts."""
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="Project not found")
    return status


@app.get("/api/projects")
async def list_projects():
    """List all active projects."""
    return {
        "projects": [
            {
                "project_id": pid,
                "status": ctx["status"],
                "started_at": ctx["started_at"].isoformat(),
            }
            for pid, ctx in orchestrator._active_projects.items()
        ],
        "total": len(orchestrator._active_projects),
    }


@app.get("/v1/projects/{project_id}/tasks")
async def get_project_tasks(project_id: str):
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="Project not found")
    # Wrap tasks in list as expected by Dashboard
    return status.get("tasks", [])


@app.get("/v1/projects/{project_id}/cost")
async def get_cost_report(project_id: str):
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="Project not found")

    cost_report = status.get("cost_report", {})
    return {
        "total_usd": cost_report.get("total_usd", 0.0),
        "by_agent": cost_report.get("by_agent", {}),
    }


@app.get("/api/projects/{project_id}/decisions")
async def get_decisions(project_id: str):
    ctx = orchestrator._active_projects.get(project_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "decisions": ctx["decision_log"].get_timeline(),
        "summary": ctx["decision_log"].summary(),
    }


@app.get("/api/agents")
async def list_agents():
    """List all registered agents and their capabilities."""
    agent_info = {
        AgentRole.CEO: "Strategy, vision, milestone planning, risk assessment",
        AgentRole.CTO: "Architecture design, tech stack selection, cost estimation",
        AgentRole.ENGINEER_BACKEND: "FastAPI code generation, DB models, CRUD APIs",
        AgentRole.ENGINEER_FRONTEND: "Next.js UI, React components, API integration",
        AgentRole.QA: "Test generation, security scanning, coverage analysis",
        AgentRole.DEVOPS: "Terraform IaC, Docker, ECS deployment, CI/CD pipelines",
        AgentRole.FINANCE: "Cost tracking, budget governance, optimization recommendations",
    }
    return {
        "agents": [
            {
                "role": role,
                "description": desc,
                "registered": role in orchestrator._agent_registry,
            }
            for role, desc in agent_info.items()
        ]
    }


# ── Omni-Channel Webhook (Slack, Discord, Telegram) ────────────────
class WebhookPayload(BaseModel):
    user_id: str
    text: str
    metadata: dict[str, Any] | None = None


@app.post("/api/webhooks/{channel}")
async def omni_channel_webhook(channel: str, payload: WebhookPayload, api_key: str = Depends(verify_api_key)):
    """
    Omni-channel control plane integration.
    Allows passing messages from Slack, Discord, or Telegram to the CEO/Orchestrator.
    """
    logger.info(
        "Received omni-channel message", channel=channel, user_id=payload.user_id
    )

    if "rewind" in payload.text.lower():
        # Example of instantly handling a rewind command from chat!
        return {
            "status": "success",
            "reply": "Rewind sequence initiated from " + channel,
        }

    return {
        "status": "success",
        "reply": f"Message received by CEO agent via {channel}",
    }


# ── BI-DIRECTIONAL WebSocket Stream ───────────────────────────────────────────────
@app.websocket("/ws/{project_id}")
async def websocket_events(websocket: WebSocket, project_id: str):
    """
    Bi-directional WebSocket endpoint.
    Receives live updates as agents execute execution graphs.
    Allows client to stream commands (HITL, rewind, chat) directly to the Orchestrator.

    Note: WebSockets don't natively support headers in browsers easily.
    We enforce authentication here by demanding the first message be an init payload
    with the API key.
    """
    await manager.connect(websocket, project_id)
    try:
        # Require immediate authentication upon connection
        try:
            auth_msg = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
            if auth_msg.get("type") != "authenticate" or auth_msg.get("api_key") != os.getenv("API_KEY"):
                await websocket.send_json({"type": "error", "message": "Authentication failed"})
                raise WebSocketDisconnect("Authentication failed")
        except TimeoutError:
            await websocket.send_json({"type": "error", "message": "Authentication timeout"})
            raise WebSocketDisconnect("Authentication timeout") from None

        await websocket.send_json(
            {
                "type": "connected",
                "message": f"Connected to project {project_id}",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        while True:
            # Handle incoming client commands (HITL approval, chat, rewind)
            try:
                # wait_for throws TimeoutError, preventing infinite blocking
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)

                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data.get("type") == "hitl_approval":
                    logger.info(
                        "Human-in-the-loop approval received via WebSocket",
                        project_id=project_id,
                    )
                    await manager.broadcast(
                        project_id,
                        {
                            "type": "system",
                            "agent": "Orchestrator",
                            "message": "HITL constraint cleared by user.",
                        },
                    )
                elif data.get("type") == "chat":
                    logger.info("User chat received", text=data.get("message"))
                    await manager.broadcast(
                        project_id, {"type": "chat_ack", "message": "Acknowledged."}
                    )
                elif data.get("type") == "rewind":
                    # Instant rewind functionality wired through the WS Gateway!
                    hash_val = data.get("hash")
                    logger.info("Rewind command requested via WebSocket", hash=hash_val)
                    ctx = orchestrator._active_projects.get(project_id)
                    if ctx and ctx.get("checkpoint_manager"):
                        await ctx["checkpoint_manager"].rewind(hash_val, force=True)
                        await manager.broadcast(
                            project_id,
                            {
                                "type": "system",
                                "message": f"Rewound project state to {hash_val}",
                            },
                        )

            except TimeoutError:
                await websocket.send_json(
                    {"type": "heartbeat", "timestamp": datetime.now(UTC).isoformat()}
                )
            except Exception as e:
                # Handle non-JSON messages or disconnects
                if "disconnect" in str(e).lower() or "close" in str(e).lower():
                    break
                logger.warning("WebSocket parsing error from client", error=str(e))

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, project_id)
        logger.info("WebSocket disconnected", project_id=project_id)
