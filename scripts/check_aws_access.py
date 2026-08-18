import os
import boto3
from botocore.exceptions import ClientError

def check_aws():
    print("ENV AWS_PROFILE:", os.getenv("AWS_PROFILE"))
    print("ENV AWS_REGION:", os.getenv("AWS_REGION"))
    print("ENV AWS_ACCESS_KEY_ID:", os.getenv("AWS_ACCESS_KEY_ID")[:5] if os.getenv("AWS_ACCESS_KEY_ID") else None)
    
    for profile in ["manohar_kumar_jha", None]:
        print(f"\n--- Checking Profile: {profile} ---")
        try:
            session = boto3.Session(profile_name=profile)
            sts = session.client("sts")
            ident = sts.get_caller_identity()
            print(f"STS Identity: Account={ident['Account']}, Arn={ident['Arn']}")
        except Exception as e:
            print(f"STS Identity failed: {e}")
            continue

        for region in ["ap-south-1", "us-east-1", "us-west-2"]:
            print(f"\nChecking Bedrock in region '{region}' with profile '{profile}':")
            runtime = session.client("bedrock-runtime", region_name=region)
            
            # Test Titan
            try:
                res = runtime.invoke_model(
                    modelId="amazon.titan-embed-text-v2:0",
                    contentType="application/json",
                    accept="application/json",
                    body='{"inputText":"test","dimensions":1024,"normalize":true}'
                )
                print(f"  [TITAN ap-south-1/us-east-1] SUCCESS in {region}")
            except ClientError as ce:
                print(f"  [TITAN FAIL {region}]: {ce}")

            # Test Nova Lite
            for model_id in ["amazon.nova-lite-v1:0", "us.amazon.nova-lite-v1:0", "apac.amazon.nova-lite-v1:0"]:
                try:
                    res = runtime.converse(
                        modelId=model_id,
                        messages=[{"role": "user", "content": [{"text": "hi"}]}]
                    )
                    print(f"  [NOVA SUCCESS {region}] modelId={model_id}: {res['output']['message']['content'][0]['text']}")
                except ClientError as ce:
                    print(f"  [NOVA FAIL {region}] modelId={model_id}: {ce.response['Error']['Code']} - {ce.response['Error']['Message']}")

if __name__ == "__main__":
    check_aws()
