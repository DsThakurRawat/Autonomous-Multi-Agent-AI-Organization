import asyncio
import os
import sys
from typing import Any

import structlog
from dotenv import load_dotenv

# Import Orchestration Components
from orchestrator.planner import OrchestratorEngine, ExecutionEvent
from agents.model_registry import get_default

# Import Specialist Agents
from agents.ceo_agent import CEOAgent
from agents.cto_agent import CTOAgent
from agents.backend_agent import BackendAgent
from agents.frontend_agent import FrontendAgent
from agents.qa_agent import QAAgent
from agents.devops_agent import DevOpsAgent
from agents.finance_agent import FinanceAgent

# Setup logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
)
logger = structlog.get_logger(__name__)

def create_llm_client(provider: str):
    """Factory to create LLM clients based on provider."""
    if provider == "openai":
        from openai import OpenAI
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    elif provider == "anthropic":
        from anthropic import Anthropic
        return Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    elif provider == "google":
        from google import genai
        return genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    elif provider == "bedrock":
        import boto3
        return boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
    return None

async def event_logger(event: ExecutionEvent):
    """Callback to print execution events to the console."""
    color = "\033[94m" # Info
    if event.level == "success": color = "\033[92m"
    elif event.level == "warning": color = "\033[93m"
    elif event.level == "error": color = "\033[91m"
    
    # Surgical log formatting
    print(f"{color}[{event.agent_role}] {event.message}\033[0m")
    if event.data and "diff" in event.data:
        print(f"\033[90m{event.data['diff']}\033[0m")

async def run_desktop_nova(goal: str):
    """Bootstraps and runs the Proximus specialist swarm locally."""
    load_dotenv()
    
    # Set Local Mode as default
    os.environ["AI_ORG_LOCAL_MODE"] = "true"
    
    # 1. Initialize the Standalone Orchestrator
    engine = OrchestratorEngine(output_dir="./output")
    engine.subscribe_events(event_logger)
    
    # 2. Initialize and Register Specialist Swarm
    agent_classes = [
        CEOAgent, CTOAgent, BackendAgent, FrontendAgent, 
        QAAgent, DevOpsAgent, FinanceAgent
    ]
    
    for AgentClass in agent_classes:
        config = get_default(AgentClass.ROLE)
        
        # Build client
        client = create_llm_client(config["provider"])
        
        # Instantiate agent
        agent = AgentClass(
            llm_client=client,
            model_name=config["model"],
            provider=config["provider"]
        )
        
        engine.register_agent(agent.ROLE, agent)
        
    logger.info("Proximus Desktop Nova: Specialist Swarm Ready")
    
    # 3. Start the Mission
    try:
        project_id = await engine.start_project(business_idea=goal)
        print(f"\n🚀 Mission Started! Project ID: {project_id}")
        
        # Poll for completion
        while True:
            project_ctx = engine._active_projects.get(project_id)
            if not project_ctx:
                break
                
            status = project_ctx.get("status")
            if status == "completed":
                print(f"\n\033[92m✅ Mission Accomplished! Output saved to: {engine.output_dir}/{project_id}\033[0m")
                break
            elif status == "failed":
                print(f"\n\033[91m❌ Mission Failed. Check logs in {engine.output_dir}/{project_id}/decision_log.json\033[0m")
                break
                
            await asyncio.sleep(2)
            
    except Exception as e:
        logger.error("Mission failed", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python desktop_nova.py \"Your business idea or coding goal\"")
        sys.exit(1)
        
    goal = sys.argv[1]
    asyncio.run(run_desktop_nova(goal))
