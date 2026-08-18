import os
import json
import boto3
from botocore.exceptions import ClientError

def check_agreements():
    profile = os.getenv("AWS_PROFILE", "manohar_kumar_jha")
    region = os.getenv("AWS_REGION", "ap-south-1")
    session = boto3.Session(profile_name=profile, region_name=region)
    bedrock = session.client("bedrock")
    
    models = ["amazon.nova-lite-v1:0", "amazon.titan-embed-text-v2:0"]
    
    for m in models:
        print(f"\n--- Checking agreement offers for {m} ---")
        try:
            res = bedrock.list_foundation_model_agreement_offers(modelId=m)
            print(json.dumps(res, indent=2, default=str))
        except ClientError as ce:
            print("ClientError:", ce)
        except Exception as e:
            print("Exception:", e)

if __name__ == "__main__":
    check_agreements()
