import os
from google import genai
import time

keys = os.getenv("GEMINI_API_KEY", "").split(",")
print(f"Testing {len(keys)} keys...")

models = ["gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-pro-latest"]

for i, key in enumerate(keys):
    client = genai.Client(api_key=key.strip())
    print(f"Key {i+1} ({key.strip()[-4:]}): ")
    for model in models:
        try:
            print(f"  - {model}: ", end="", flush=True)
            resp = client.models.generate_content(
                model=model,
                contents="Say 'OK'"
            )
            print(f"✅ {resp.text.strip()}")
            break # Move to next key if one model works
        except Exception as e:
            print(f"❌ {str(e)[:50]}...")
