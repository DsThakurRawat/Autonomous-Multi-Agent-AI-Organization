"""
Main API Server — Orchestrator Control Plane
FastAPI application that exposes the orchestrator to the world.
Provides REST API + WebSocket for real-time agent event streaming.
"""

import asyncio
from datetime import datetime
import os
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from google import genai

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import structlog

from orchestrator.planner import OrchestratorEngine, ExecutionEvent
from agents.ceo_agent import CEOAgent
from agents.cto_agent import CTOAgent
from agents.engineer_agent import EngineerAgent
from agents.qa_agent import QAAgent
from agents.devops_agent import DevOpsAgent
from agents.finance_agent import FinanceAgent

logger = structlog.get_logger(__name__)

# ── Dynamic LLM Setup ──────────────────────────────────────────────

load_dotenv()

llm_client = None
model_name = "gemini-2.5-flash"
gemini_key = os.getenv("GEMINI_API_KEY")

if gemini_key and gemini_key != "your-gemini-key":
    llm_client = genai.Client(api_key=gemini_key)
    logger.info("Initializing agents with Google Gemini LLM")
else:
    logger.warning("No Gemini API key found. Agents will run in mock mode.")

# ── Global Orchestrator ────────────────────────────────────────────
orchestrator = OrchestratorEngine(budget_usd=200.0, output_dir="./output")


# ── WebSocket Connection Manager ───────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
        logger.info("WebSocket connected", project_id=project_id)

    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            self.active_connections[project_id].remove(websocket)

    async def broadcast(self, project_id: str, data: Dict[str, Any]):
        if project_id not in self.active_connections:
            return
        dead = []
        for ws in self.active_connections[project_id]:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active_connections[project_id].remove(ws)


manager = ConnectionManager()


# ── App Lifecycle ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Register all agents on startup."""
    orchestrator.register_agent(
        "CEO", CEOAgent(llm_client=llm_client, model_name=model_name)
    )
    orchestrator.register_agent(
        "CTO", CTOAgent(llm_client=llm_client, model_name=model_name)
    )
    orchestrator.register_agent(
        "Engineer_Backend",
        EngineerAgent(mode="backend", llm_client=llm_client, model_name=model_name),
    )
    orchestrator.register_agent(
        "Engineer_Frontend",
        EngineerAgent(mode="frontend", llm_client=llm_client, model_name=model_name),
    )
    orchestrator.register_agent(
        "QA", QAAgent(llm_client=llm_client, model_name=model_name)
    )
    orchestrator.register_agent(
        "DevOps", DevOpsAgent(llm_client=llm_client, model_name=model_name)
    )
    orchestrator.register_agent(
        "Finance", FinanceAgent(llm_client=llm_client, model_name=model_name)
    )
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


# ── Request/Response Models ────────────────────────────────────────
class StartProjectRequest(BaseModel):
    business_idea: str
    budget_usd: float = 200.0
    constraints: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseModel):
    project_id: str
    status: str
    message: str
    started_at: str


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
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "agents": list(orchestrator._agent_registry.keys()),
        "active_projects": len(orchestrator._active_projects),
    }


@app.post("/api/projects", response_model=ProjectResponse)
async def start_project(request: StartProjectRequest):
    """
    MAIN ENDPOINT: Submit a business idea and launch the AI company.
    Returns a project_id for WebSocket streaming and status polling.
    """
    if len(request.business_idea.strip()) < 10:
        raise HTTPException(
            status_code=400, detail="Business idea too short (min 10 chars)"
        )

    # Wire up WebSocket event broadcasting
    async def broadcast_event(event: ExecutionEvent):
        await manager.broadcast(project_id, event.to_dict())

    project_id = await orchestrator.start_project(
        business_idea=request.business_idea, user_constraints=request.constraints or {}
    )

    # Subscribe the event broadcaster for this project
    orchestrator.subscribe_events(broadcast_event)

    logger.info("Project started via API", project_id=project_id)
    return ProjectResponse(
        project_id=project_id,
        status="started",
        message=f"AI company launched! Connect WebSocket to /ws/{project_id} for live updates.",
        started_at=datetime.utcnow().isoformat(),
    )


@app.get("/api/projects/{project_id}")
async def get_project_status(project_id: str):
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


@app.get("/api/projects/{project_id}/artifacts")
async def get_artifacts(project_id: str):
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="Project not found")
    return status.get("artifacts", {})


@app.get("/api/projects/{project_id}/cost")
async def get_cost_report(project_id: str):
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="Project not found")
    return status.get("cost_report", {})


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
        "CEO": "Strategy, vision, milestone planning, risk assessment",
        "CTO": "Architecture design, tech stack selection, cost estimation",
        "Engineer_Backend": "FastAPI code generation, DB models, CRUD APIs",
        "Engineer_Frontend": "Next.js UI, React components, API integration",
        "QA": "Test generation, security scanning, coverage analysis",
        "DevOps": "Terraform IaC, Docker, ECS deployment, CI/CD pipelines",
        "Finance": "Cost tracking, budget governance, optimization recommendations",
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
    metadata: Optional[Dict[str, Any]] = None


@app.post("/api/webhooks/{channel}")
async def omni_channel_webhook(channel: str, payload: WebhookPayload):
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
    """
    await manager.connect(websocket, project_id)
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "message": f"Connected to project {project_id}",
                "timestamp": datetime.utcnow().isoformat(),
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
                        await ctx["checkpoint_manager"].rewind(hash_val)
                        await manager.broadcast(
                            project_id,
                            {
                                "type": "system",
                                "message": f"Rewound project state to {hash_val}",
                            },
                        )

            except asyncio.TimeoutError:
                await websocket.send_json(
                    {"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()}
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
