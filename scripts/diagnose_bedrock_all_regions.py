import os
import json
import boto3
from botocore.exceptions import ClientError

def test_all():
    profile = "manohar_kumar_jha"
    session = boto3.Session(profile_name=profile)
    
    regions = ["ap-south-1", "us-east-1", "us-west-2", "eu-central-1", "ap-northeast-1", "eu-west-1"]
    
    print(f"=== Testing Bedrock for profile: {profile} across regions ===")
    
    for r in regions:
        print(f"\n--- REGION: {r} ---")
        bedrock = session.client("bedrock", region_name=r)
        runtime = session.client("bedrock-runtime", region_name=r)
        
        # Check model access / foundation models
        try:
            f_models = bedrock.list_foundation_models()
            nova_f = [m["modelId"] for m in f_models.get("modelSummaries", []) if "nova" in m["modelId"]]
            titan_f = [m["modelId"] for m in f_models.get("modelSummaries", []) if "titan" in m["modelId"]]
            print(f"Foundation Nova models: {nova_f}")
            print(f"Foundation Titan models: {titan_f}")
        except Exception as e:
            print(f"Failed to list foundation models: {e}")

        # Check inference profiles
        try:
            inf_p = bedrock.list_inference_profiles()
            nova_ip = [p["inferenceProfileId"] for p in inf_p.get("inferenceProfileSummaries", []) if "nova" in p["inferenceProfileId"]]
            print(f"Inference profiles (Nova): {nova_ip}")
        except Exception as e:
            print(f"Failed to list inference profiles: {e}")

        # Test Titan
        try:
            res = runtime.invoke_model(
                modelId="amazon.titan-embed-text-v2:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps({"inputText": "test", "dimensions": 1024, "normalize": True})
            )
            body = json.loads(res["body"].read())
            dim = len(body.get("embedding", []))
            print(f"TITAN V2: PASS (dim={dim})")
        except ClientError as ce:
            print(f"TITAN V2: FAIL - {ce.response['Error']['Code']}: {ce.response['Error']['Message']}")

        # Test Nova Lite candidate IDs
        nova_ids = [
            "amazon.nova-lite-v1:0",
            "apac.amazon.nova-lite-v1:0",
            "us.amazon.nova-lite-v1:0",
            "eu.amazon.nova-lite-v1:0",
            "global.amazon.nova-2-lite-v1:0"
        ]
        
        for nid in nova_ids:
            try:
                res = runtime.converse(
                    modelId=nid,
                    messages=[{"role": "user", "content": [{"text": "Reply OK"}]}],
                    inferenceConfig={"maxTokens": 10}
                )
                txt = res["output"]["message"]["content"][0]["text"]
                print(f"NOVA LITE ({nid}): PASS -> '{txt.strip()}'")
            except ClientError as ce:
                code = ce.response['Error']['Code']
                msg = ce.response['Error']['Message']
                if "invalid" not in msg.lower():
                    print(f"NOVA LITE ({nid}): FAIL - {code}: {msg}")

if __name__ == "__main__":
    test_all()
