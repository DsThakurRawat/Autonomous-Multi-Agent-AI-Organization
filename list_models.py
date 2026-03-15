import os
import boto3
from dotenv import load_dotenv

load_dotenv()


def list_bedrock_models():
    print(
        f"Checking available foundation models in {os.getenv('AWS_REGION', 'us-east-1')}..."
    )
    try:
        client = boto3.client(
            "bedrock", region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        response = client.list_foundation_models()

        nova_models = [
            m for m in response["modelSummaries"] if "nova" in m["modelId"].lower()
        ]

        if not nova_models:
            print(
                "❌ No Amazon Nova models found. Make sure you have requested access in the AWS Console for this region."
            )
            return

        print("\nAvailable Amazon Nova Models:")
        for model in nova_models:
            print(f"- {model['modelId']} (Name: {model['modelName']})")

    except Exception as e:
        print(f"❌ Error listing models: {e}")


if __name__ == "__main__":
    list_bedrock_models()
