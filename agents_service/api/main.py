import os
import asyncio
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog
from dotenv import load_dotenv
from google import genai
import redis.asyncio as aioredis

from agents.research_intelligence import ResearchIntelligence
from agents.events import AgentEvent

load_dotenv()

# -- Logging --------------------------------------------------------
logger = structlog.get_logger(__name__)

app = FastAPI(title="SARANG Intelligence Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- State & Infrastructure -----------------------------------------
api_key = os.getenv("GEMINI_API_KEY")
llm_client = None
if api_key:
    try:
        llm_client = genai.Client(api_key=api_key)
        logger.info("Gemini-3.1 AI Ready", status="online")
    except Exception as e:
        logger.error("Failed to initialize Gemini", error=str(e))

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
rdb = aioredis.from_url(redis_url, decode_responses=True)

# Global store for active missions
active_missions: Dict[str, ResearchIntelligence] = {}

class ChatRequest(BaseModel):
    message: str
    role: str = "Research_Intelligence"
    project_id: Optional[str] = "default"

class AgentResponse(BaseModel):
    agent_role: str
    content: str

# -- WebSocket Management -------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

async def redis_listener():
    """Listens to sarang:events and broadcasts to all connected WebSockets."""
    pubsub = rdb.pubsub()
    await pubsub.subscribe("sarang:events")
    logger.info("Redis listener active", channel="sarang:events")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await manager.broadcast(data)
                except Exception as e:
                    logger.error("Failed to broadcast message", error=str(e))
    finally:
        await pubsub.unsubscribe("sarang:events")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_listener())

# -- Endpoints ------------------------------------------------------

@app.get("/health")
async def health_check():
    return {"status": "online", "llm_ready": llm_client is not None}

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Welcome message
    await websocket.send_json({
        "type": "system",
        "message": "SARANG Research Swarm Connected (Python Core).",
        "agent": "system",
        "timestamp": datetime.now(UTC).isoformat()
    })

    try:
        while True:
            data = await websocket.receive_text()
            req_data = json.loads(data)
            
            if req_data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            message = req_data.get("message")
            role = req_data.get("role", "Research_Intelligence")
            
            # Start research mission in background
            asyncio.create_task(process_chat_request(message, role))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        manager.disconnect(websocket)

async def process_chat_request(message: str, role: str):
    """Processes a chat request using the appropriate agent logic."""
    if not llm_client:
        await rdb.publish("sarang:events", json.dumps({
            "type": "error",
            "message": "Gemini API not configured",
            "agent": "system"
        }))
        return

    try:
        # If it's a Research Intelligence request, use the full run() method
        if role == "Research_Intelligence":
            agent = ResearchIntelligence(llm_client=llm_client)
            # Setup telemetry
            agent._current_task_id = f"chat-{int(datetime.now().timestamp())}"
            
            # Custom context to emit events directly to Redis
            class RedisContext:
                async def emit_event(self, event: AgentEvent):
                    payload = {
                        "type": event.event_type,
                        "agent": event.agent_role,
                        "message": event.message,
                        "level": event.level,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "data": event.data
                    }
                    await rdb.publish("sarang:events", json.dumps(payload))

            plan = await agent.run(research_goal=message, context=RedisContext())
            
            # Send final response
            await rdb.publish("sarang:events", json.dumps({
                "type": "message",
                "agent": role,
                "message": plan.get("summary", "Mission deconstructed."),
                "timestamp": datetime.now(UTC).isoformat()
            }))
        else:
            # Fallback to simple chat for other roles
            system_msg = f"You are the {role} of SARANG Research Swarm."
            response = await asyncio.to_thread(
                llm_client.models.generate_content,
                model="gemini-2.0-flash-lite",
                contents=[{"role": "user", "parts": [{"text": f"System: {system_msg}\n\nUser: {message}"}]}]
            )
            await rdb.publish("sarang:events", json.dumps({
                "type": "message",
                "agent": role,
                "message": response.text,
                "timestamp": datetime.now(UTC).isoformat()
            }))
            
    except Exception as e:
        logger.error("Processing failure", error=str(e))
        await rdb.publish("sarang:events", json.dumps({
            "type": "error",
            "message": f"Intelligence failure: {str(e)}",
            "agent": "system"
        }))

@app.post("/agents/chat", response_model=AgentResponse)
async def chat_with_agent(request: ChatRequest):
    """Legacy REST bridge for one-off requests."""
    if not llm_client:
        raise HTTPException(status_code=503, detail="Gemini API not configured")

    try:
        system_msg = f"You are the {request.role} of SARANG Research Swarm."
        response = await asyncio.to_thread(
            llm_client.models.generate_content,
            model="gemini-2.0-flash-lite",
            contents=[{"role": "user", "parts": [{"text": f"System: {system_msg}\n\nUser: {request.message}"}]}]
        )
        return AgentResponse(agent_role=request.role, content=response.text)
    except Exception as e:
        logger.error("REST intelligence failure", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
