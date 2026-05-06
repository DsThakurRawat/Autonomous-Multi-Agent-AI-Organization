import os
import asyncio
from typing import List, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
import structlog
from dotenv import load_dotenv
from google import genai

# Import the real agents from the agents/ directory
from agents.lead_researcher_agent import LeadResearcherAgent
from agents.roles import AgentRole

load_dotenv()

# -- Professional Logging Configuration -----------------------------
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer() if os.getenv("PROD") else structlog.dev.ConsoleRenderer()
    ]
)
logger = structlog.get_logger(__name__)

app = FastAPI(title="SARANG Intelligence Engine")

# -- Gemini Initialization ------------------------------------------
api_key = os.getenv("GEMINI_API_KEY")
llm_client = None
if api_key:
    try:
        llm_client = genai.Client(api_key=api_key)
        logger.info("Gemini-1.5 AI ready", status="online")
    except Exception as e:
        logger.error("Failed to initialize Gemini", error=str(e))
else:
    logger.warning("GEMINI_API_KEY missing - running in legacy mock mode")

# -- Pydantic Models (Modern Dev Standards) ------------------------
class ResearchMission(BaseModel):
    mission_id: str = Field(..., example="mission-123")
    goal: str = Field(..., example="Deconstruct a paper on Quantum Neural Networks")

class ChatRequest(BaseModel):
    message: str = Field(..., example="What are the mathematical requirements for this paper?")
    role: str = Field(default="Lead_Researcher")
    history: Optional[List[dict]] = []

class AgentResponse(BaseModel):
    agent_role: str
    content: str
    status: str = "success"

# -- API Endpoints --------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "SARANG Intelligence Online",
        "llm_provider": "google",
        "llm_ready": llm_client is not None
    }

async def run_mission_logic(mission_id: str, goal: str):
    """Executes a full research mission using the real agent swarm logic."""
    log = logger.bind(mission_id=mission_id)
    log.info("Research swarm launching", goal=goal)

    try:
        # Instantiate the real Lead Researcher with Redis support
        agent = LeadResearcherAgent(llm_client=llm_client)
        agent.model_name = "gemini-1.5-flash"
        agent.provider = "google"
        agent._current_task_id = mission_id  # This enables the Redis event bridge

        # Execute the mission - results will be streamed via agent.emit()
        result = await agent.run(research_goal=goal)
        
        log.info("Mission intelligence synthesis complete", 
                 complexity=result.get("estimated_complexity"),
                 hypotheses=len(result.get("hypotheses", [])))
        
    except Exception as e:
        log.error("Mission failed", error=str(e))

@app.post("/agents/research")
async def conduct_research(request: ResearchMission, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_mission_logic, request.mission_id, request.goal)
    return {
        "status": "mission_launched",
        "mission_id": request.mission_id,
        "primary_agent": AgentRole.LEAD_RESEARCHER,
        "message": "Scientific deconstruction swarm is now active."
    }

@app.post("/agents/chat", response_model=AgentResponse)
async def chat_with_agent(request: ChatRequest):
    """Direct conversational interface - behave like Claude/Gemini."""
    if not llm_client:
        raise HTTPException(status_code=503, detail="LLM provider not available")

    log = logger.bind(agent=request.role)
    log.info("Conversational request received", message=request.message[:50])

    try:
        # Detect if this is a greeting or a research request
        # In a real LangGraph setup, this would be a node transition
        is_greeting = any(word in request.message.lower() for word in ["hi", "hello", "hey", "who are you"])
        
        if is_greeting:
            system_msg = (
                "You are the Lead Researcher of SARANG. "
                "Respond warmly and professionally. Explain that you are an autonomous research coordinator "
                "capable of deconstructing papers, extracting math, and running simulations. "
                "Ask how you can assist with their scientific inquiry today."
            )
        else:
            system_msg = (
                f"You are the {request.role} of SARANG. "
                "Provide a high-level, intelligent response to the user's inquiry. "
                "If they are asking for a research mission, confirm you can launch the swarm for them."
            )

        response = llm_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[
                {"role": "user", "parts": [{"text": f"System: {system_msg}\n\nUser: {request.message}"}]}
            ]
        )
        
        return AgentResponse(
            agent_role=request.role,
            content=response.text
        )
    except Exception as e:
        log.error("Chat failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
