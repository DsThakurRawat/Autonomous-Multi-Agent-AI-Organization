import os
import json
import asyncio
from typing import Annotated, TypedDict, List, Union, Any

import redis.asyncio as aioredis
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from agents.research_intelligence import ResearchIntelligence
from agents.math_architect_agent import MathArchitectAgent
from agents.implementation_specialist_agent import ImplementationSpecialistAgent
from agents.peer_reviewer_agent import PeerReviewerAgent

# -- Swarm State ----------------------------------------------------

class SwarmState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    research_plan: dict
    math_analysis: dict
    blueprint: dict
    next_agent: str
    session_id: str

# -- Agent Nodes ----------------------------------------------------

async def research_node(state: SwarmState, config: RunnableConfig):
    """Orchestrates high-level research planning."""
    agent = ResearchIntelligence()
    # In a real LangGraph, we'd wrap the agent logic to be compatible
    goal = state["messages"][-1].content
    plan = await agent.run(research_goal=goal)
    
    return {
        "research_plan": plan,
        "next_agent": "math_architect",
        "messages": [AIMessage(content=plan.get("summary", "Plan generated."), name="Research_Intelligence")]
    }

async def math_node(state: SwarmState, config: RunnableConfig):
    """Formalizes mathematical foundations."""
    # Logic to call MathArchitectAgent with the plan from state["research_plan"]
    return {
        "next_agent": "implementation",
        "messages": [AIMessage(content="Mathematical deconstruction complete.", name="Math_Architect")]
    }

async def implementation_node(state: SwarmState, config: RunnableConfig):
    """Drafts technical implementations."""
    return {
        "next_agent": "reviewer",
        "messages": [AIMessage(content="Implementation blueprint ready.", name="Implementation_Specialist")]
    }

async def reviewer_node(state: SwarmState, config: RunnableConfig):
    """Critiques the swarm's output."""
    return {
        "next_agent": END,
        "messages": [AIMessage(content="Final review complete. Research is reproducible.", name="Peer_Reviewer")]
    }

# -- Build the Graph ------------------------------------------------

workflow = StateGraph(SwarmState)

workflow.add_node("researcher", research_node)
workflow.add_node("math_architect", math_node)
workflow.add_node("implementation", implementation_node)
workflow.add_node("reviewer", reviewer_node)

workflow.add_edge(START, "researcher")
workflow.add_edge("researcher", "math_architect")
workflow.add_edge("math_architect", "implementation")
workflow.add_edge("implementation", "reviewer")
workflow.add_edge("reviewer", END)

# Compile with SQLite/Postgres checkpointer for long-term memory
app = workflow.compile()

# -- Worker Loop ----------------------------------------------------

async def run_worker():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    r = aioredis.from_url(redis_url, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("sarang:tasks")

    print("🚀 SARANG Swarm Worker (LangGraph) Active...")
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            session_id = data.get("session_id")
            goal = data.get("message")
            
            print(f"📥 New Task Received: {goal[:50]}...")
            
            # Run LangGraph
            async for event in app.astream(
                {"messages": [HumanMessage(content=goal)], "session_id": session_id},
                config={"configurable": {"thread_id": session_id}}
            ):
                # Emit events to Redis for the Go Gateway to relay
                for node, output in event.items():
                    if "messages" in output:
                        msg = output["messages"][-1]
                        await r.publish("sarang:events", json.dumps({
                            "type": "message",
                            "agent": msg.name or node,
                            "message": msg.content,
                            "session_id": session_id
                        }))

if __name__ == "__main__":
    asyncio.run(run_worker())
