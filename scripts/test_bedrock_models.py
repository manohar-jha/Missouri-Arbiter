"""
Bedrock Model Access Tester
Tests direct model IDs and cross-region inference profiles in ap-south-1 and us-east-1.
"""

import json
import logging
import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_bedrock")

PROFILE_NAME = "manohar_kumar_jha"

MODELS_TO_TEST = [
    ("amazon.titan-embed-text-v2:0", "ap-south-1"),
    ("apac.amazon.titan-embed-text-v2:0", "ap-south-1"),
    ("us.amazon.titan-embed-text-v2:0", "us-east-1"),
    ("amazon.titan-embed-text-v1", "ap-south-1"),
    ("anthropic.claude-3-5-sonnet-20240620-v1:0", "ap-south-1"),
    ("apac.anthropic.claude-3-5-sonnet-20240620-v1:0", "ap-south-1"),
    ("us.anthropic.claude-3-5-sonnet-20241022-v2:0", "us-east-1"),
    ("anthropic.claude-3-haiku-20240307-v1:0", "ap-south-1"),
]


def test_models():
    for model_id, region in MODELS_TO_TEST:
        session = boto3.Session(profile_name=PROFILE_NAME, region_name=region)
        runtime = session.client("bedrock-runtime")
        
        is_titan = "titan" in model_id.lower()
        if is_titan:
            payload = {"inputText": "Missouri Arbiter Test", "dimensions": 1024, "normalize": True}
        else:
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 50,
                "messages": [{"role": "user", "content": "Hello Bedrock"}]
            }
            
        try:
            res = runtime.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload)
            )
            body = json.loads(res["body"].read())
            logger.info(f"[SUCCESS] Model '{model_id}' in region '{region}' INVOKED SUCCESSFULLY!")
            if is_titan:
                emb = body.get("embedding", [])
                logger.info(f" -> Titan Vector length: {len(emb)}")
        except Exception as e:
            logger.warning(f"[FAILED] Model '{model_id}' in '{region}': {e}")


if __name__ == "__main__":
    test_models()
