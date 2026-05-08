import os
import asyncio
import json
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog
from dotenv import load_dotenv
from google import genai
from groq import Groq as GroqClient
from agents_service.mock_llm import MockLLMClient
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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

# -- Key Rotation ---------------------------------------------------
GEMINI_KEYS = [k.strip() for k in os.getenv("GEMINI_API_KEY", "").split(",") if k.strip()]
GROQ_KEYS   = [k.strip() for k in os.getenv("GROQ_API_KEY",   "").split(",") if k.strip()]
current_gemini_index = 0
current_groq_index   = 0

def get_next_gemini_client():
    global current_gemini_index
    key = GEMINI_KEYS[current_gemini_index]
    current_gemini_index = (current_gemini_index + 1) % len(GEMINI_KEYS)
    return genai.Client(api_key=key)

def get_next_groq_client():
    global current_groq_index
    key = GROQ_KEYS[current_groq_index]
    current_groq_index = (current_groq_index + 1) % len(GROQ_KEYS)
    return GroqClient(api_key=key)

# Legacy alias kept for startup log
def get_next_client():
    if GEMINI_KEYS:
        return get_next_gemini_client()
    return MockLLMClient()

llm_client = get_next_client() if GEMINI_KEYS else None
logger.info("SARANG LLM Ready", gemini_keys=len(GEMINI_KEYS), groq_keys=len(GROQ_KEYS))

MODEL_CHAIN = ["gemini-2.0-flash", "gemini-pro-latest"]

# -- In-Memory Session Store ----------------------------------------
# No Redis. No external deps. Just Python dicts.
sessions_store: Dict[str, dict] = {}          # session_id -> metadata
messages_store: Dict[str, List[dict]] = {}    # session_id -> [messages]
user_sessions: Dict[str, List[str]] = {}      # user_email -> [session_ids]

# -- Models ---------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    role: str = "Research_Intelligence"
    session_id: Optional[str] = None
    user_email: Optional[str] = "local@sarang.ai"

class SessionCreate(BaseModel):
    user_email: str
    title: Optional[str] = "New Research"

class AgentResponse(BaseModel):
    agent_role: str
    content: str

# -- Session Helpers (In-Memory) ------------------------------------

def create_session(user_email: str, title: str) -> dict:
    session_id = f"sess_{int(time.time())}_{os.urandom(4).hex()}"
    meta = {
        "id": session_id,
        "title": title,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "user_email": user_email
    }
    sessions_store[session_id] = meta
    messages_store[session_id] = []
    if user_email not in user_sessions:
        user_sessions[user_email] = []
    user_sessions[user_email].insert(0, session_id)
    return meta

def add_message(session_id: str, role: str, content: str):
    msg = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(UTC).isoformat()
    }
    if session_id not in messages_store:
        messages_store[session_id] = []
    messages_store[session_id].append(msg)

    # Auto-title from first user message
    if role == "User" and session_id in sessions_store:
        meta = sessions_store[session_id]
        if meta.get("title") == "New Research":
            meta["title"] = (content[:30] + '...') if len(content) > 30 else content
        meta["updated_at"] = datetime.now(UTC).isoformat()

# -- WebSocket Manager ----------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket client connected", total=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_to_session(self, session_id: str, message: dict):
        """Broadcast to all connected clients (they filter by session_id)."""
        dead = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                dead.append(conn)
        for d in dead:
            self.disconnect(d)

manager = ConnectionManager()

# -- LLM Call with Key Rotation -------------------------------------

GROQ_MODEL = "llama-3.3-70b-versatile"

async def call_groq(system_msg: str, user_message: str, session_id: str = None) -> str:
    """Try all 10 Groq keys in rotation. Returns text or raises."""
    global current_groq_index
    exhausted: set = set()

    for _ in range(len(GROQ_KEYS)):
        key_idx = current_groq_index
        client = get_next_groq_client()
        try:
            logger.info("Groq LLM call", key=key_idx, model=GROQ_MODEL)
            resp = await asyncio.to_thread(
                client.chat.completions.create,
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user",   "content": user_message}
                ],
                max_tokens=2048,
            )
            return resp.choices[0].message.content
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "quota" in err or "rate" in err:
                logger.warning("Groq quota hit, rotating", key=key_idx)
                exhausted.add(key_idx)
                if len(exhausted) >= len(GROQ_KEYS):
                    raise RuntimeError("All Groq keys exhausted")
                await asyncio.sleep(1)
            else:
                logger.warning("Groq model error", error=str(e))
                raise
    raise RuntimeError("All Groq keys exhausted")


async def call_llm(system_msg: str, user_message: str, session_id: str = None) -> str:
    """LLM call with tiered fallback: Gemini → Groq → Mock."""
    global llm_client, current_gemini_index

    # ── Tier 1: Gemini ──────────────────────────────────────────────
    if GEMINI_KEYS:
        gemini_exhausted: set = set()
        gemini_client = get_next_gemini_client()

        for attempt in range(len(GEMINI_KEYS) * len(MODEL_CHAIN)):
            for model_name in MODEL_CHAIN:
                try:
                    logger.info("Gemini call", model=model_name, key=current_gemini_index, attempt=attempt)
                    resp = await asyncio.to_thread(
                        gemini_client.models.generate_content,
                        model=model_name,
                        contents=[{"role": "user", "parts": [{"text": f"System: {system_msg}\n\nUser: {user_message}"}]}]
                    )
                    return resp.text
                except Exception as e:
                    err = str(e).lower()
                    if "429" in err or "quota" in err or "resource" in err:
                        logger.warning("Gemini quota hit", model=model_name, key=current_gemini_index)
                        gemini_exhausted.add(current_gemini_index)
                        gemini_client = get_next_gemini_client()
                        if len(gemini_exhausted) >= len(GEMINI_KEYS):
                            logger.warning("All Gemini keys exhausted, switching to Groq")
                            if session_id:
                                await manager.send_to_session(session_id, {
                                    "type": "status",
                                    "message": "Gemini keys rate-limited. Switching to Groq...",
                                    "session_id": session_id,
                                    "agent": "system"
                                })
                            break
                        if session_id:
                            await manager.send_to_session(session_id, {
                                "type": "status",
                                "message": f"Rate limit hit. Trying next key... ({len(gemini_exhausted)}/{len(GEMINI_KEYS)} exhausted)",
                                "session_id": session_id,
                                "agent": "system"
                            })
                        await asyncio.sleep(1)
                    else:
                        logger.warning("Gemini model error", model=model_name, error=str(e))
                    continue
            else:
                continue
            break  # inner for broke — all Gemini exhausted

    # ── Tier 2: Groq ────────────────────────────────────────────────
    if GROQ_KEYS:
        try:
            text = await call_groq(system_msg, user_message, session_id)
            return text
        except Exception as e:
            logger.warning("Groq exhausted too", error=str(e))
            if session_id:
                await manager.send_to_session(session_id, {
                    "type": "status",
                    "message": "All Groq keys rate-limited. Switching to Demo Mode...",
                    "session_id": session_id,
                    "agent": "system"
                })

    # ── Tier 3: Mock (Demo Mode) ─────────────────────────────────────
    logger.warning("All LLM providers exhausted — falling back to MockLLMClient")
    if session_id:
        await manager.send_to_session(session_id, {
            "type": "status",
            "message": "All API keys rate-limited. Switching to Demo Mode...",
            "session_id": session_id,
            "agent": "system"
        })
    mock = MockLLMClient()
    resp = await asyncio.to_thread(
        mock.models.generate_content,
        model="mock-demo",
        contents=[{"role": "user", "parts": [{"text": f"System: {system_msg}\n\nUser: {user_message}"}]}]
    )
    return resp.text

# -- Direct Chat Processing -----------------------------------------

async def process_chat(message: str, role: str, session_id: str):
    """Process chat DIRECTLY. No queue. No Redis. No worker."""
    try:
        # 1. Tell user we're thinking
        await manager.send_to_session(session_id, {
            "type": "status",
            "message": f"{role} is analyzing your request...",
            "session_id": session_id,
            "agent": role
        })

        # 2. Call LLM directly
        system_msg = f"""You are the {role} of the SARANG Research Swarm — an elite AI research collective.
You provide deep, thoughtful, well-structured research responses.
Use markdown formatting for clarity. Be comprehensive but concise."""

        content = await call_llm(system_msg, message, session_id)

        # 3. Save to memory
        add_message(session_id, role, content)

        # 4. Send result directly to WebSocket
        await manager.send_to_session(session_id, {
            "type": "message",
            "agent": role,
            "message": content,
            "session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat()
        })

    except Exception as e:
        logger.error("Chat processing failed", error=str(e))
        await manager.send_to_session(session_id, {
            "type": "message",
            "agent": "system",
            "message": f"⚠️ Intelligence error: {str(e)}. Please try again in a minute.",
            "session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat()
        })

# -- REST Endpoints -------------------------------------------------

@app.get("/sessions")
async def list_sessions(user_email: str):
    sids = user_sessions.get(user_email, [])
    return [sessions_store[sid] for sid in sids if sid in sessions_store]

@app.post("/sessions")
async def start_session(req: SessionCreate):
    return create_session(req.user_email, req.title or "New Research")

@app.get("/sessions/{session_id}/messages")
async def list_messages(session_id: str):
    return messages_store.get(session_id, [])

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user_email: str):
    sessions_store.pop(session_id, None)
    messages_store.pop(session_id, None)
    if user_email in user_sessions:
        user_sessions[user_email] = [s for s in user_sessions[user_email] if s != session_id]
    return {"status": "deleted"}

@app.post("/agents/chat", response_model=AgentResponse)
async def chat_with_agent(request: ChatRequest):
    """REST fallback — processes inline."""
    if not llm_client:
        raise HTTPException(status_code=503, detail="Gemini API not configured")

    if request.session_id:
        add_message(request.session_id, "User", request.message)

    # Process in background so we return immediately
    asyncio.create_task(process_chat(request.message, request.role, request.session_id))
    return AgentResponse(agent_role=request.role, content="Agent is thinking...")

# -- WebSocket Endpoint ---------------------------------------------

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Greeting
        await websocket.send_json({
            "type": "system",
            "message": "SARANG Intelligence Swarm Connected.",
            "agent": "system"
        })

        while True:
            data = await websocket.receive_text()
            req_data = json.loads(data)

            if req_data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            message = req_data.get("message")
            role = req_data.get("role", "Research_Intelligence")
            session_id = req_data.get("session_id")

            if not message or not session_id:
                continue

            # Save user message
            add_message(session_id, "User", message)

            # Process in background — response comes via WebSocket
            asyncio.create_task(process_chat(message, role, session_id))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        manager.disconnect(websocket)

@app.get("/health")
async def health():
    return {
        "status": "online",
        "llm_ready": llm_client is not None,
        "keys_loaded": len(GEMINI_KEYS),
        "architecture": "Pure Python (No Redis)"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
