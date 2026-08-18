import boto3
from botocore.exceptions import ClientError

def test_all_models_in_apsouth1():
    session = boto3.Session(profile_name="manohar_kumar_jha", region_name="ap-south-1")
    bedrock = session.client("bedrock")
    runtime = session.client("bedrock-runtime")
    
    models = bedrock.list_foundation_models().get("modelSummaries", [])
    print(f"Total foundation models in ap-south-1: {len(models)}")
    
    for m in models:
        m_id = m["modelId"]
        provider = m.get("providerName")
        m_name = m.get("modelName")
        
        # Try a dummy call based on provider
        try:
            if "titan-embed" in m_id:
                res = runtime.invoke_model(
                    modelId=m_id,
                    contentType="application/json",
                    accept="application/json",
                    body='{"inputText":"test"}'
                )
                print(f"[SUCCESS] {m_id} ({provider} - {m_name})")
            elif "converse" in str(m.get("outputModalities", [])):
                res = runtime.converse(
                    modelId=m_id,
                    messages=[{"role": "user", "content": [{"text": "hi"}]}]
                )
                print(f"[SUCCESS CONVERSE] {m_id} ({provider} - {m_name})")
        except ClientError as ce:
            err = ce.response.get("Error", {}).get("Message", str(ce))
            print(f"[FAIL] {m_id}: {err}")
        except Exception as e:
            print(f"[ERR] {m_id}: {e}")

if __name__ == "__main__":
    test_all_models_in_apsouth1()
