import os
import json
import boto3
from botocore.exceptions import ClientError

def query_availability():
    profile = os.getenv("AWS_PROFILE", "manohar_kumar_jha")
    region = os.getenv("AWS_REGION", "ap-south-1")
    
    print(f"Connecting to Bedrock control plane (Profile: {profile}, Region: {region})...", flush=True)
    session = boto3.Session(profile_name=profile, region_name=region)
    bedrock = session.client("bedrock")
    
    # List available methods on bedrock client
    methods = [m for m in dir(bedrock) if not m.startswith("_")]
    print(f"Bedrock client methods available: {[m for m in methods if 'model' in m.lower() or 'availability' in m.lower()]}", flush=True)
    
    models = ["amazon.nova-lite-v1:0", "amazon.titan-embed-text-v2:0"]
    
    results = {}
    
    for m_id in models:
        print(f"\n==================================================", flush=True)
        print(f"Querying availability for model: {m_id}", flush=True)
        print(f"==================================================", flush=True)
        
        m_info = {}
        
        # 1. Try get_foundation_model_availability (if exists in API)
        if hasattr(bedrock, "get_foundation_model_availability"):
            try:
                res = bedrock.get_foundation_model_availability(modelId=m_id)
                print(f"[get_foundation_model_availability] Response:", flush=True)
                print(json.dumps(res, indent=2, default=str), flush=True)
                m_info["get_foundation_model_availability"] = res
            except ClientError as ce:
                print(f"[get_foundation_model_availability] ClientError: {ce}", flush=True)
                m_info["get_foundation_model_availability_error"] = str(ce)
            except Exception as e:
                print(f"[get_foundation_model_availability] Exception: {e}", flush=True)
                m_info["get_foundation_model_availability_error"] = str(e)

        # 2. Try get_foundation_model
        if hasattr(bedrock, "get_foundation_model"):
            try:
                res = bedrock.get_foundation_model(modelIdentifier=m_id)
                print(f"[get_foundation_model] Response:", flush=True)
                print(json.dumps(res, indent=2, default=str), flush=True)
                m_info["get_foundation_model"] = res
            except ClientError as ce:
                print(f"[get_foundation_model] ClientError: {ce}", flush=True)
                m_info["get_foundation_model_error"] = str(ce)
            except Exception as e:
                print(f"[get_foundation_model] Exception: {e}", flush=True)

        # 3. Try aws cli command if available
        # We can also check aws cli bedrock get-foundation-model-availability or get-foundation-model
        results[m_id] = m_info

    print("\n" + "="*70, flush=True)
    print("AVAILABILITY QUERY COMPLETE", flush=True)
    print("="*70, flush=True)

if __name__ == "__main__":
    query_availability()
