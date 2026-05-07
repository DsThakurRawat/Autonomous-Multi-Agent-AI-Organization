import os
import json
import asyncio
import time
from typing import Dict, Any
from datetime import datetime, UTC
import redis.asyncio as aioredis
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import structlog

# -- Logging --
logger = structlog.get_logger(__name__)

# -- Config --
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
# Support multiple keys separated by commas
GEMINI_KEYS = os.getenv("GEMINI_API_KEY", "").split(",")
current_key_index = 0

def get_next_client():
    global current_key_index
    key = GEMINI_KEYS[current_key_index].strip()
    current_key_index = (current_key_index + 1) % len(GEMINI_KEYS)
    return genai.Client(api_key=key)

rdb = aioredis.from_url(REDIS_URL, decode_responses=True)
llm_client = get_next_client() if GEMINI_KEYS[0] else None

MODEL_CHAIN = ["gemini-2.0-flash", "gemini-pro-latest"]

async def call_ll_with_fallback(system_msg: str, user_message: str, session_id: str = None):
    """Reliable LLM call with patient, gentle key rotation."""
    global llm_client, current_key_index
    max_total_attempts = 10
    
    for attempt in range(max_total_attempts):
        for model_name in MODEL_CHAIN:
            try:
                # Log current state
                logger.info("Attempting LLM call", model=model_name, key_index=current_key_index)
                
                @retry(
                    stop=stop_after_attempt(2),
                    wait=wait_exponential(multiplier=1, min=2, max=5),
                    retry=retry_if_exception_type(Exception),
                    reraise=True
                )
                async def _attempt():
                    return await asyncio.to_thread(
                        llm_client.models.generate_content,
                        model=model_name,
                        contents=[{"role": "user", "parts": [{"text": f"System: {system_msg}\n\nUser: {user_message}"}]}]
                    )
                resp = await _attempt()
                return resp.text
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str:
                    logger.warning("Quota reached, rotating key and waiting...", model=model_name, key_index=current_key_index)
                    
                    # Rotate key
                    llm_client = get_next_client()
                    
                    if session_id:
                        await rdb.publish("sarang:events", json.dumps({
                            "type": "status",
                            "message": f"Rate limit reached. Rotating to Key {current_key_index + 1}... (Waiting 15s for cooldown)",
                            "session_id": session_id,
                            "agent": "system"
                        }))
                    
                    # MANDATORY: Wait for quota cooldown
                    await asyncio.sleep(15)
                    continue
                
                logger.warning("Model failed, trying fallback", model=model_name, error=str(e))
                continue
        
        # If a full model cycle fails, take a longer break
        logger.warning("Full cycle failed, cooling down...")
        await asyncio.sleep(20)
        
    raise Exception("All models and all API keys completely exhausted after multiple cycles")

async def process_task(task: Dict[str, Any]):
    """Processes a single research task from the queue."""
    session_id = task.get("session_id")
    message = task.get("message")
    role = task.get("role", "Research_Intelligence")
    
    try:
        # 1. Notify UI that processing has started
        await rdb.publish("sarang:events", json.dumps({
            "type": "status",
            "message": f"{role} is deconstructing your request...",
            "session_id": session_id,
            "agent": role
        }))

        # 2. Call LLM
        system_msg = f"You are the {role} of SARANG Research Swarm."
        content = await call_ll_with_fallback(system_msg, message, session_id)

        # 3. Save to Session History
        msg_payload = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(UTC).isoformat()
        }
        await rdb.rpush(f"sarang:session:{session_id}:messages", json.dumps(msg_payload))

        # 4. Broadcast final message
        await rdb.publish("sarang:events", json.dumps({
            "type": "message",
            "agent": role,
            "message": content,
            "session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat()
        }))

    except Exception as e:
        logger.error("Task processing failed", error=str(e))
        await rdb.publish("sarang:events", json.dumps({
            "type": "error",
            "message": f"Intelligence Failure: {str(e)}",
            "session_id": session_id,
            "agent": "system"
        }))

async def worker_loop():
    """Main loop to pull tasks from the Redis queue."""
    logger.info("SARANG Python Worker Started", status="listening")
    while True:
        try:
            # BLPOP waits for a task to appear in 'sarang:tasks'
            task_data = await rdb.blpop("sarang:tasks", timeout=5)
            if task_data:
                _, payload = task_data
                task = json.loads(payload)
                await process_task(task)
        except Exception as e:
            logger.error("Worker loop error", error=str(e))
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(worker_loop())
