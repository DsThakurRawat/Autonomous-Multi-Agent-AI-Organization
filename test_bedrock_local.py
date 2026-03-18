import os

import boto3
from dotenv import load_dotenv

load_dotenv()

def test_bedrock():
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    print(f"Testing Bedrock in {aws_region}...")

    try:
        client = boto3.client(
            "bedrock-runtime",
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
            region_name=aws_region,
        )

        # Test a simple converse call
        model_id = "amazon.nova-lite-v1:0"
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]

        response = client.converse(
            modelId=model_id,
            messages=messages,
            inferenceConfig={"maxTokens": 10}
        )
        print("Success! Bedrock response received.")
        print(f"Response: {response['output']['message']['content'][0]['text']}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_bedrock()
