import os
import json
import boto3
from botocore.exceptions import ClientError

def test_us_east_1():
    profile = os.getenv("AWS_PROFILE", "manohar_kumar_jha")
    region = "us-east-1"
    
    print(f"Testing AWS Bedrock in region '{region}' with profile '{profile}'...", flush=True)
    session = boto3.Session(profile_name=profile, region_name=region)
    bedrock = session.client("bedrock")
    runtime = session.client("bedrock-runtime")
    
    # 1. Check availability
    try:
        avail_nova = bedrock.get_foundation_model_availability(modelId="amazon.nova-lite-v1:0")
        print(f"Nova Lite Availability in {region}:", json.dumps(avail_nova, indent=2, default=str), flush=True)
    except Exception as e:
        print(f"Nova Lite Availability Error in {region}: {e}", flush=True)
        
    try:
        avail_titan = bedrock.get_foundation_model_availability(modelId="amazon.titan-embed-text-v2:0")
        print(f"Titan V2 Availability in {region}:", json.dumps(avail_titan, indent=2, default=str), flush=True)
    except Exception as e:
        print(f"Titan V2 Availability Error in {region}: {e}", flush=True)

    # 2. Test Invocations for Nova Lite (direct & us inference profile)
    nova_targets = ["amazon.nova-lite-v1:0", "us.amazon.nova-lite-v1:0"]
    for target in nova_targets:
        print(f"\n--- Invocing Nova Lite ({target}) in {region} ---", flush=True)
        try:
            res = runtime.converse(
                modelId=target,
                messages=[{"role": "user", "content": [{"text": "Hello, answer OK"}]}],
                inferenceConfig={"maxTokens": 10}
            )
            txt = res["output"]["message"]["content"][0]["text"]
            print(f"[NOVA SUCCESS] {target}: '{txt.strip()}'", flush=True)
        except ClientError as ce:
            print(f"[NOVA FAIL] {target}: {ce.response['Error']['Code']} - {ce.response['Error']['Message']}", flush=True)

    # 3. Test Invocation for Titan V2
    print(f"\n--- Invoking Titan V2 in {region} ---", flush=True)
    try:
        payload = {"inputText": "Test embedding payload", "dimensions": 1024, "normalize": True}
        res = runtime.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        body = json.loads(res["body"].read())
        emb = body.get("embedding", [])
        print(f"[TITAN SUCCESS] Vector length: {len(emb)}", flush=True)
    except ClientError as ce:
        print(f"[TITAN FAIL]: {ce.response['Error']['Code']} - {ce.response['Error']['Message']}", flush=True)

if __name__ == "__main__":
    test_us_east_1()
