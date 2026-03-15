import os
import json
import boto3
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


def test_bedrock_nova():
    print("Testing Live AWS Bedrock Integration for Amazon Nova Models...")
    try:
        client = boto3.client(
            "bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1")
        )

        # Test Text Embeddings (Nova Multimodal Embeddings)
        print("\n1. Testing amazon.nova-embed-text-v1:0...")
        embed_payload = {
            "inputText": "Testing Nova Multimodal Embeddings for AI Agent Routing"
        }

        response = client.invoke_model(
            modelId="amazon.nova-embed-text-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(embed_payload),
        )

        response_body = json.loads(response["body"].read().decode("utf-8"))
        embedding = response_body.get("embedding", [])
        print(f"✅ Success! Fetched {len(embedding)}-dimensional Nova embedding.")

        client = boto3.client(
            "bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1")
        )

        # Test Text Generation (Nova Lite/Pro)
        print("\nTesting amazon.nova-lite-v1:0...")
        prompt_payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": "Hello Nova, are you ready to act as a core platform agent?"
                        }
                    ],
                }
            ],
            "schemaVersion": "messages-v1",
        }

        response = client.invoke_model(
            modelId="amazon.nova-lite-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(prompt_payload),
        )

        response_body = json.loads(response["body"].read().decode("utf-8"))
        answer = (
            response_body.get("output", {})
            .get("message", {})
            .get("content", [{}])[0]
            .get("text", "")
        )

        response_body = json.loads(response["body"].read().decode("utf-8"))

        # Bedrock response parsing for Nova
        output = response_body.get("output", {})
        message = output.get("message", {})
        content = message.get("content", [{}])
        answer = content[0].get("text", "No response text found")

        print(f"✅ Success! Nova Lite says: {answer}")

    except Exception as e:
        print(
            f"⚠️ Live AWS Bedrock test failed (Do you have AWS credentials set up locally?): {e}"
        )


if __name__ == "__main__":
    test_bedrock_nova()
