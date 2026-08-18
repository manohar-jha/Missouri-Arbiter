import os
import json
import boto3
from botocore.exceptions import ClientError

def check_iam():
    profile = os.getenv("AWS_PROFILE", "manohar_kumar_jha")
    region = os.getenv("AWS_REGION", "ap-south-1")
    session = boto3.Session(profile_name=profile, region_name=region)
    sts = session.client("sts")
    iam = session.client("iam")
    
    ident = sts.get_caller_identity()
    print("STS Identity:", json.dumps(ident, indent=2))
    
    arn = ident["Arn"]
    account = ident["Account"]
    
    print("\n--- Simulating Policy for Bedrock InvokeModel ---")
    try:
        res = iam.simulate_principal_policy(
            PolicySourceArn=arn,
            ActionNames=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:Converse"
            ],
            ResourceArns=[
                "arn:aws:bedrock:ap-south-1::foundation-model/amazon.nova-lite-v1:0",
                "arn:aws:bedrock:ap-south-1::foundation-model/amazon.titan-embed-text-v2:0"
            ]
        )
        print("IAM Policy Simulation Results:")
        for eval_res in res.get("EvaluationResults", []):
            print(f"Action: {eval_res['EvalActionName']} -> Decision: {eval_res['EvalDecision']}")
    except ClientError as ce:
        print("IAM Policy Simulation ClientError:", ce)
    except Exception as e:
        print("IAM Policy Simulation Exception:", e)

if __name__ == "__main__":
    check_iam()
