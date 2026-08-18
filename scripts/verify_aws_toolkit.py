"""
AWS Agent Toolkit & Bedrock Verification Script
Performs AWS CLI v2 verification, Agent Toolkit configuration, Bedrock model discovery, Titan V2 testing,
and Antigravity MCP integration audit.
"""

import os
import sys
import json
import logging
import subprocess
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("aws_toolkit_verify")

PROFILE_NAME = "manohar_kumar_jha"
WORKING_REGION = "ap-south-1"
TOOLKIT_REGION = "us-east-1"


def get_aws_cli_cmd(args: List[str]) -> List[str]:
    """Returns executable command array for AWS CLI."""
    pf_v2 = r"C:\Program Files\Amazon\AWSCLIV2\aws.exe"
    if os.path.exists(pf_v2):
        return [pf_v2] + args
    
    return [sys.executable, "-m", "awscli"] + args


def run_aws_command(args: List[str]) -> subprocess.CompletedProcess:
    cmd = get_aws_cli_cmd(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def check_aws_cli_version() -> Dict[str, Any]:
    logger.info("\n--- 1. Checking AWS CLI Version ---")
    res = run_aws_command(["--version"])
    ver_output = (res.stdout or res.stderr or "").strip()
    if res.returncode == 0 or "aws-cli" in ver_output.lower():
        logger.info(f"[DETECTED] AWS CLI: {ver_output}")
        is_v2 = "aws-cli/2" in ver_output.lower()
        return {"installed": True, "version": ver_output, "is_v2": is_v2}
    else:
        logger.error(f"[FAILED] AWS CLI check failed: {ver_output}")
        return {"installed": False, "version": ver_output, "is_v2": False}


def configure_aws_profile_region() -> bool:
    logger.info(f"\n--- 2. Setting AWS Profile '{PROFILE_NAME}' Region to '{WORKING_REGION}' ---")
    res = run_aws_command(["configure", "set", "region", WORKING_REGION, "--profile", PROFILE_NAME])
    if res.returncode == 0:
        logger.info(f"[SUCCESS] Region for profile '{PROFILE_NAME}' configured to '{WORKING_REGION}'")
        return True
    else:
        logger.error(f"[FAILED] Configure set region failed: {(res.stderr or res.stdout).strip()}")
        return False


def verify_aws_caller_identity() -> Dict[str, Any]:
    logger.info(f"\n--- 3. Verifying AWS Identity (aws sts get-caller-identity --profile {PROFILE_NAME}) ---")
    res = run_aws_command(["sts", "get-caller-identity", "--profile", PROFILE_NAME])
    if res.returncode == 0:
        try:
            data = json.loads(res.stdout)
            account = data.get("Account", "")
            arn = data.get("Arn", "")
            masked_acc = f"***{account[-4:]}" if len(account) >= 4 else "MASKED"
            logger.info(f"[SUCCESS] Authenticated! Account: {masked_acc}, ARN: {arn}")
            return {"authenticated": True, "account": masked_acc, "arn": arn, "error": None}
        except Exception as e:
            return {"authenticated": False, "account": None, "arn": None, "error": str(e)}
    else:
        err = (res.stderr or res.stdout).strip()
        logger.warning(f"[UNAUTHENTICATED] {err}")
        return {"authenticated": False, "account": None, "arn": None, "error": err}


def run_agent_toolkit_setup() -> Dict[str, Any]:
    logger.info(f"\n--- 4. Installing / Configuring AWS Agent Toolkit (Region: {TOOLKIT_REGION}) ---")
    res = run_aws_command(["configure", "agent-toolkit", "--yes", "--region", TOOLKIT_REGION, "--profile", PROFILE_NAME])
    if res.returncode == 0:
        output = res.stdout.strip()
        logger.info(f"[SUCCESS] AWS Agent Toolkit Configured!\n{output}")
        return {"configured": True, "output": output, "error": None}
    else:
        err = (res.stderr or res.stdout).strip()
        logger.warning(f"[AGENT TOOLKIT SETUP RESULT] {err}")
        return {"configured": False, "output": None, "error": err}


def inspect_antigravity_mcp_compatibility() -> Dict[str, Any]:
    logger.info("\n--- 5. Checking Antigravity MCP Compatibility ---")
    gemini_mcp_path = r"C:\Users\manoh\.gemini\config\mcp_config.json"
    workspace_mcp_path = os.path.join(os.getcwd(), ".agents", "mcp_config.json")
    
    found_paths = []
    if os.path.exists(gemini_mcp_path):
        found_paths.append(gemini_mcp_path)
    if os.path.exists(workspace_mcp_path):
        found_paths.append(workspace_mcp_path)
        
    logger.info(f"Discovered Antigravity MCP Configuration Locations: {found_paths}")
    
    home_dir = os.path.expanduser("~")
    aws_mcp_path = os.path.join(home_dir, ".aws", "mcp.json")
    has_aws_mcp = os.path.exists(aws_mcp_path)
    
    return {
        "gemini_mcp_path": gemini_mcp_path if os.path.exists(gemini_mcp_path) else None,
        "workspace_mcp_path": workspace_mcp_path if os.path.exists(workspace_mcp_path) else None,
        "aws_mcp_path": aws_mcp_path if has_aws_mcp else None,
        "has_aws_mcp": has_aws_mcp,
        "direct_compatibility": True if (found_paths and has_aws_mcp) else False
    }


def discover_bedrock_models() -> Dict[str, Any]:
    logger.info(f"\n--- 6. Discovering Bedrock Models in {WORKING_REGION} ---")
    try:
        import boto3
        session = boto3.Session(profile_name=PROFILE_NAME, region_name=WORKING_REGION)
        bedrock = session.client("bedrock")
        res = bedrock.list_foundation_models()
        summaries = res.get("modelSummaries", [])
        discovered = [m["modelId"] for m in summaries]
        
        logger.info(f"[SUCCESS] Connected to Bedrock API in {WORKING_REGION}. Found {len(discovered)} models.")
        
        claude_models = [m for m in discovered if "claude" in m.lower()]
        selected_claude = None
        for pref in [
            "us.anthropic.claude-3-5-sonnet-20240620-v1:0",
            "anthropic.claude-3-5-sonnet-20240620-v1:0",
            "anthropic.claude-3-haiku-20240307-v1:0",
            "anthropic.claude-v2:1"
        ]:
            if pref in discovered:
                selected_claude = pref
                break
        if not selected_claude and claude_models:
            selected_claude = claude_models[0]
            
        return {
            "connected": True,
            "total_models": len(discovered),
            "claude_models": claude_models,
            "selected_model": selected_claude or "anthropic.claude-3-5-sonnet-20240620-v1:0"
        }
    except Exception as e:
        logger.warning(f"[BEDROCK DISCOVERY UNSECURED] {e}")
        return {
            "connected": False,
            "total_models": 0,
            "claude_models": [],
            "selected_model": "anthropic.claude-3-5-sonnet-20240620-v1:0 (Pending Auth)"
        }


def test_real_bedrock_invocation(model_id: str) -> Dict[str, Any]:
    logger.info(f"\n--- 7. Real Bedrock Invocation Test (Model: {model_id}) ---")
    try:
        import boto3
        session = boto3.Session(profile_name=PROFILE_NAME, region_name=WORKING_REGION)
        runtime = session.client("bedrock-runtime")
        
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "Missouri Arbiter Test"}]
        }
        res = runtime.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        body = json.loads(res["body"].read())
        logger.info(f"[SUCCESS] Bedrock Invocation PASSED!")
        return {"passed": True, "response": body}
    except Exception as e:
        logger.warning(f"[BEDROCK INVOCATION FAILED] {e}")
        return {"passed": False, "error": str(e)}


def test_real_titan_embeddings() -> Dict[str, Any]:
    logger.info(f"\n--- 8. Real Amazon Titan Embeddings V2 Test ---")
    try:
        import boto3
        session = boto3.Session(profile_name=PROFILE_NAME, region_name=WORKING_REGION)
        runtime = session.client("bedrock-runtime")
        
        payload = {
            "inputText": "Missouri Arbiter Maritime Embedding Test",
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
        if emb and len(emb) == 1024:
            logger.info(f"[SUCCESS] Real Titan Embeddings V2 PASSED! Dimension: {len(emb)}")
            return {"passed": True, "dimension": len(emb), "model_id": "amazon.titan-embed-text-v2:0"}
        else:
            return {"passed": False, "dimension": len(emb) if emb else 0, "error": "Invalid dimension"}
    except Exception as e:
        logger.warning(f"[TITAN EMBEDDINGS FAILED] {e}")
        return {"passed": False, "dimension": 1024, "error": str(e)}


def run_full_toolkit_verification():
    cli_info = check_aws_cli_version()
    cfg_ok = configure_aws_profile_region()
    ident_info = verify_aws_caller_identity()
    toolkit_info = run_agent_toolkit_setup() if ident_info["authenticated"] else {"configured": False, "error": "Unauthenticated profile"}
    mcp_compat = inspect_antigravity_mcp_compatibility()
    bedrock_disc = discover_bedrock_models() if ident_info["authenticated"] else {"connected": False, "selected_model": "anthropic.claude-3-5-sonnet-20240620-v1:0 (Pending Auth)"}
    
    model_id = bedrock_disc.get("selected_model", "anthropic.claude-3-5-sonnet-20240620-v1:0")
    bedrock_test = test_real_bedrock_invocation(model_id) if ident_info["authenticated"] else {"passed": False, "error": "Unauthenticated"}
    titan_test = test_real_titan_embeddings() if ident_info["authenticated"] else {"passed": False, "error": "Unauthenticated"}
    
    report = {
        "aws_cli": cli_info,
        "region_configured": cfg_ok,
        "aws_identity": ident_info,
        "agent_toolkit": toolkit_info,
        "antigravity_mcp": mcp_compat,
        "bedrock_discovery": bedrock_disc,
        "bedrock_test": bedrock_test,
        "titan_test": titan_test
    }
    
    print("\n" + "="*60)
    print("=== AWS AGENT TOOLKIT VERIFICATION SUMMARY ===")
    print(json.dumps(report, indent=2))
    print("="*60)
    return report

if __name__ == "__main__":
    run_full_toolkit_verification()
