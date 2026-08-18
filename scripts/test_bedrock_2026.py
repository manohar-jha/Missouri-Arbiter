"""
Bedrock 2026 Access Model Diagnostic & Test Script
Probes Titan V2 and Claude models in ap-south-1 and us-east-1 under profile 'manohar_kumar_jha'.
Analyzes exact AWS exception types (Marketplace, IAM, Quota, Use Case Submission, ResourceNotFound).
"""

import json
import logging
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("bedrock_2026")

PROFILE_NAME = "manohar_kumar_jha"

MODELS_TO_PROBE = [
    # 1. Titan V2 Embeddings
    {"id": "amazon.titan-embed-text-v2:0", "region": "ap-south-1", "type": "titan"},
    {"id": "amazon.titan-embed-text-v2:0", "region": "us-east-1", "type": "titan"},
    {"id": "us.amazon.titan-embed-text-v2:0", "region": "us-east-1", "type": "titan"},
    
    # 2. Anthropic / Claude Models
    {"id": "anthropic.claude-3-5-sonnet-20241022-v2:0", "region": "ap-south-1", "type": "claude"},
    {"id": "anthropic.claude-3-5-sonnet-20240620-v1:0", "region": "ap-south-1", "type": "claude"},
    {"id": "anthropic.claude-3-haiku-20240307-v1:0", "region": "ap-south-1", "type": "claude"},
    {"id": "us.anthropic.claude-3-5-sonnet-20241022-v2:0", "region": "us-east-1", "type": "claude"},
    {"id": "us.anthropic.claude-3-haiku-20240307-v1:0", "region": "us-east-1", "type": "claude"}
]


def test_titan_invocation(runtime_client, model_id: str):
    payload = {
        "inputText": "Missouri Arbiter Hydrodynamic Vector Embedding Probe",
        "dimensions": 1024,
        "normalize": True
    }
    response = runtime_client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload)
    )
    body = json.loads(response["body"].read())
    embedding = body.get("embedding", [])
    return embedding


def test_claude_invocation(runtime_client, model_id: str):
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 50,
        "messages": [{"role": "user", "content": "Missouri Arbiter Test"}]
    }
    response = runtime_client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload)
    )
    body = json.loads(response["body"].read())
    return body


def run_diagnostics():
    logger.info("=== Running Bedrock 2026 Access Diagnostics ===")
    
    results = {}
    
    for item in MODELS_TO_PROBE:
        m_id = item["id"]
        region = item["region"]
        m_type = item["type"]
        key = f"{m_id} ({region})"
        
        logger.info(f"\nProbing {m_type.upper()} Model: {m_id} in {region}...")
        
        try:
            session = boto3.Session(profile_name=PROFILE_NAME, region_name=region)
            runtime = session.client("bedrock-runtime")
            
            if m_type == "titan":
                emb = test_titan_invocation(runtime, m_id)
                logger.info(f"[SUCCESS] Real Titan V2 Invocation PASSED! Vector length: {len(emb)}")
                results[key] = {"status": "PASS", "vector_length": len(emb), "error": None}
            else:
                resp = test_claude_invocation(runtime, m_id)
                text = resp.get("content", [{}])[0].get("text", "")
                logger.info(f"[SUCCESS] Real Claude Invocation PASSED! Output snippet: {text[:50]}")
                results[key] = {"status": "PASS", "output_snippet": text[:50], "error": None}
                
        except ClientError as ce:
            err_code = ce.response.get("Error", {}).get("Code", "Unknown")
            err_msg = ce.response.get("Error", {}).get("Message", str(ce))
            logger.warning(f"[FAILED] Code: {err_code} | Message: {err_msg}")
            
            # Analyze root cause
            cause = "UNKNOWN"
            if "Operation not allowed" in err_msg or "ValidationException" in err_code:
                cause = "AWS Marketplace Subscription / Anthropic First-Time Use Case Agreement Required in AWS Console"
            elif "AccessDenied" in err_code:
                cause = "IAM Permission Missing for bedrock:InvokeModel"
            elif "ResourceNotFoundException" in err_code:
                cause = "Model ID or Region Deprecated / Unsupported"
            elif "ThrottlingException" in err_code:
                cause = "AWS Service Quota / Rate Limit Exceeded"
                
            results[key] = {"status": "FAIL", "code": err_code, "message": err_msg, "probable_cause": cause}
            
        except Exception as e:
            logger.error(f"[ERROR] {e}")
            results[key] = {"status": "ERROR", "error": str(e)}

    print("\n" + "="*70)
    print("=== BEDROCK 2026 DIAGNOSTIC SUMMARY ===")
    print(json.dumps(results, indent=2))
    print("="*70)
    return results

if __name__ == "__main__":
    run_diagnostics()
