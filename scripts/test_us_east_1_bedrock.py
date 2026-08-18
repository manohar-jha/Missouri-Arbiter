import os
import json
import boto3
from botocore.exceptions import ClientError

def test_us_east_1_bedrock():
    profile = os.getenv("AWS_PROFILE", "manohar_kumar_jha")
    region = "us-east-1"
    
    session = boto3.Session(profile_name=profile, region_name=region)
    bedrock = session.client("bedrock")
    runtime = session.client("bedrock-runtime")
    
    print(f"--- 1. List Foundation Models in {region} ---")
    try:
        res = bedrock.list_foundation_models()
        models = [m["modelId"] for m in res.get("modelSummaries", []) if "nova" in m["modelId"] or "titan" in m["modelId"]]
        print(f"Foundation models found in {region}: {models[:10]}")
    except Exception as e:
        print("List foundation models error:", e)

    print(f"\n--- 2. Try Nova Lite Converse in {region} ---")
    for m_id in ["amazon.nova-lite-v1:0", "us.amazon.nova-lite-v1:0"]:
        try:
            res = runtime.converse(
                modelId=m_id,
                messages=[{"role": "user", "content": [{"text": "Hello"}]}],
                inferenceConfig={"maxTokens": 10}
            )
            print(f"[SUCCESS] {m_id}: {res['output']['message']['content'][0]['text']}")
        except ClientError as ce:
            print(f"[FAIL] {m_id}: Code={ce.response.get('Error',{}).get('Code')} | Msg={ce.response.get('Error',{}).get('Message')}")
        except Exception as e:
            print(f"[ERR] {m_id}: {e}")

    print(f"\n--- 3. Try Titan Embeddings V2 in {region} ---")
    try:
        payload = {"inputText": "Test", "dimensions": 1024, "normalize": True}
        res = runtime.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        body = json.loads(res["body"].read())
        print(f"[SUCCESS Titan]: Vector dim = {len(body.get('embedding', []))}")
    except ClientError as ce:
        print(f"[FAIL Titan]: Code={ce.response.get('Error',{}).get('Code')} | Msg={ce.response.get('Error',{}).get('Message')}")
    except Exception as e:
        print(f"[ERR Titan]: {e}")

if __name__ == "__main__":
    test_us_east_1_bedrock()
