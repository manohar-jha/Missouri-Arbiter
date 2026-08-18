import os
import boto3
import json
from botocore.exceptions import ClientError

def test_detailed():
    profile = os.getenv("AWS_PROFILE", "manohar_kumar_jha")
    region = os.getenv("AWS_REGION", "ap-south-1")
    
    session = boto3.Session(profile_name=profile, region_name=region)
    runtime = session.client("bedrock-runtime")
    
    print(f"Testing AWS Profile: {profile}, Region: {region}")
    
    # 1. Nova Lite via apac inference profile
    targets = [
        "amazon.nova-lite-v1:0",
        "apac.amazon.nova-lite-v1:0",
        "us.amazon.nova-lite-v1:0",
        "arn:aws:bedrock:ap-south-1:599729677443:inference-profile/apac.amazon.nova-lite-v1:0"
    ]
    
    for t in targets:
        print(f"\n--- Testing Converse on '{t}' ---")
        try:
            res = runtime.converse(
                modelId=t,
                messages=[{"role": "user", "content": [{"text": "Hello"}]}],
                inferenceConfig={"maxTokens": 10}
            )
            print("SUCCESS Converse:", res["output"]["message"]["content"][0]["text"])
        except ClientError as ce:
            print("ClientError Response:", json.dumps(ce.response, default=str))
        except Exception as e:
            print("Error:", e)

    # 2. Titan Embeddings V2
    print("\n--- Testing Titan Embeddings V2 ---")
    try:
        res = runtime.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({"inputText": "test", "dimensions": 1024, "normalize": True})
        )
        body = json.loads(res["body"].read())
        print("SUCCESS Titan, dim:", len(body.get("embedding", [])))
    except ClientError as ce:
        print("ClientError Response:", json.dumps(ce.response, default=str))
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_detailed()
