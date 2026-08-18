import os
import json
import boto3
from botocore.exceptions import ClientError

def test_nova_and_titan():
    profile = os.getenv("AWS_PROFILE", "manohar_kumar_jha")
    region = os.getenv("AWS_REGION", "ap-south-1")
    
    print(f"Testing AWS Profile: {profile}, Region: {region}", flush=True)
    
    session = boto3.Session(profile_name=profile, region_name=region)
    bedrock = session.client("bedrock")
    runtime = session.client("bedrock-runtime")
    
    # 1. Test List Models / Inference Profiles
    try:
        profiles = bedrock.list_inference_profiles()
        p_list = [p.get("inferenceProfileId") for p in profiles.get("inferenceProfileSummaries", [])]
        print(f"Inference profiles found: {p_list}")
    except Exception as e:
        print(f"Error listing inference profiles: {e}")
        
    try:
        models = bedrock.list_foundation_models()
        m_list = [m.get("modelId") for m in models.get("modelSummaries", []) if "nova" in m.get("modelId", "").lower()]
        print(f"Nova models found in foundation models: {m_list}")
    except Exception as e:
        print(f"Error listing foundation models: {e}")
        
    # Candidate model IDs for Nova Lite in ap-south-1 or cross-region inference profiles
    nova_candidates = [
        "amazon.nova-lite-v1:0",
        "apac.amazon.nova-lite-v1:0",
        "us.amazon.nova-lite-v1:0",
        "eu.amazon.nova-lite-v1:0",
        "arn:aws:bedrock:ap-south-1::foundation-model/amazon.nova-lite-v1:0"
    ]
    
    print("\n--- Testing Nova Lite Invocations ---")
    nova_success_id = None
    nova_res = None
    
    for model_id in nova_candidates:
        print(f"\nTrying modelId: '{model_id}'...")
        # 1) Try converse API
        try:
            res = runtime.converse(
                modelId=model_id,
                messages=[{"role": "user", "content": [{"text": "Say hello in one word."}]}],
                inferenceConfig={"maxTokens": 20, "temperature": 0.1}
            )
            output_text = res["output"]["message"]["content"][0]["text"]
            print(f"[CONVERSE SUCCESS] modelId='{model_id}': {output_text.strip()}")
            nova_success_id = model_id
            nova_res = output_text
            break
        except ClientError as ce:
            print(f"[CONVERSE FAIL] modelId='{model_id}': {ce}")
        except Exception as e:
            print(f"[CONVERSE ERROR] modelId='{model_id}': {e}")
            
        # 2) Try invoke_model API
        try:
            body = {
                "inferenceConfig": {"max_new_tokens": 20, "temperature": 0.1},
                "messages": [{"role": "user", "content": [{"text": "Say hello in one word."}]}]
            }
            res = runtime.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body)
            )
            resp_body = json.loads(res["body"].read())
            print(f"[INVOKE SUCCESS] modelId='{model_id}': {resp_body}")
            nova_success_id = model_id
            nova_res = resp_body
            break
        except ClientError as ce:
            print(f"[INVOKE FAIL] modelId='{model_id}': {ce}")
        except Exception as e:
            print(f"[INVOKE ERROR] modelId='{model_id}': {e}")

    # 2. Test Titan Embeddings
    print("\n--- Testing Titan Embeddings V2 ---")
    titan_success = False
    titan_dim = None
    try:
        payload = {
            "inputText": "Missouri Arbiter Real Cloud Verification Payload",
            "dimensions": 1024,
            "normalize": True
        }
        res = runtime.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        body = json.loads(res["body"].read())
        emb = body.get("embedding", [])
        titan_dim = len(emb)
        print(f"[TITAN SUCCESS] Dimension: {titan_dim}")
        titan_success = True
    except Exception as e:
        print(f"[TITAN FAIL] Error: {e}")

    print("\n================ SUMMARY ================")
    print(f"[BEDROCK] MODEL = amazon.nova-lite-v1:0 (Using: {nova_success_id})")
    print(f"[BEDROCK] REGION = {region}")
    print(f"[BEDROCK] REAL API = {'PASS' if nova_success_id else 'FAIL'}")
    print(f"[TITAN] REAL API = {'PASS' if titan_success else 'FAIL'}")
    print(f"[TITAN] DIMENSION = {titan_dim}")

if __name__ == "__main__":
    test_nova_and_titan()
