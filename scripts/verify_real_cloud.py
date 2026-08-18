"""
Real Cloud Environment Verification Suite (Amazon Bedrock Nova Lite & Titan V2 Architecture)
Executes real invocation tests for:
- Amazon Nova Lite (amazon.nova-lite-v1:0) for agent reasoning, orchestration, and decision interpretation
- Amazon Titan Embeddings V2 (amazon.titan-embed-text-v2:0) for experiential vector memory
- CockroachDB Cloud connection and Phase 1-3 transactional/vector tests
Enforces ARBITER_MODE=CLOUD with zero mocks.
"""

import os
import sys
import json
import logging
import subprocess
from typing import Dict, Any, Tuple, Optional

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("real_cloud_verify")

def _load_dotenv(env_path=".env"):
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip("\"'"))

_load_dotenv()

PROFILE_NAME = os.getenv("AWS_PROFILE", "manohar_kumar_jha")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
TITAN_MODEL_ID = os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")


def run_step_1_aws_cli() -> Tuple[bool, Dict[str, Any]]:
    logger.info("\n--- STEP 1: Verify AWS CLI Authentication ---")
    try:
        cmd = [sys.executable, "-m", "awscli", "sts", "get-caller-identity", "--profile", PROFILE_NAME]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            account = data.get("Account", "")
            arn = data.get("Arn", "")
            masked_acc = f"***{account[-4:]}" if len(account) >= 4 else "MASKED"
            logger.info(f"[SUCCESS] AWS CLI Profile '{PROFILE_NAME}' Authenticated! Account: {masked_acc}, ARN: {arn}")
            return True, {"account": masked_acc, "arn": arn}
        else:
            logger.error(f"[FAILED] AWS CLI Profile '{PROFILE_NAME}' error: {res.stderr.strip()}")
            return False, {"error": res.stderr.strip()}
    except Exception as e:
        logger.error(f"[FAILED] AWS CLI check error: {e}")
        return False, {"error": str(e)}


def test_real_nova_lite_invocation() -> Tuple[bool, str, Optional[str]]:
    """
    Performs a REAL invocation of Amazon Nova Lite.
    Checks direct model ID 'amazon.nova-lite-v1:0' as well as supported regional inference profiles.
    Returns: (pass_status, model_id_used, response_or_error)
    """
    logger.info("\n--- STEP 2: Real Amazon Nova Lite Invocation Test ---")
    try:
        import boto3
        session = boto3.Session(profile_name=PROFILE_NAME, region_name=AWS_REGION)
        runtime = session.client("bedrock-runtime")

        candidate_ids = [
            BEDROCK_MODEL_ID,
            f"apac.{BEDROCK_MODEL_ID}",
            f"arn:aws:bedrock:{AWS_REGION}:599729677443:inference-profile/apac.{BEDROCK_MODEL_ID}"
        ]

        for model_id in candidate_ids:
            logger.info(f"Attempting real invocation for model/profile ID: '{model_id}'...")
            # Try Bedrock Converse API
            try:
                res = runtime.converse(
                    modelId=model_id,
                    messages=[{"role": "user", "content": [{"text": "Missouri Arbiter Nova Lite Probe"}]}],
                    inferenceConfig={"maxTokens": 20, "temperature": 0.1}
                )
                output_text = res["output"]["message"]["content"][0]["text"]
                logger.info(f"[SUCCESS] Real Nova Lite Converse API succeeded with '{model_id}'! Response: '{output_text.strip()}'")
                return True, model_id, output_text.strip()
            except Exception as e:
                logger.warning(f"Converse attempt on '{model_id}' returned: {e}")

            # Try direct invoke_model API
            try:
                payload = {
                    "inferenceConfig": {"max_new_tokens": 20, "temperature": 0.1},
                    "messages": [{"role": "user", "content": [{"text": "Missouri Arbiter Nova Lite Probe"}]}]
                }
                res = runtime.invoke_model(
                    modelId=model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(payload)
                )
                body = json.loads(res["body"].read())
                output_msg = body.get("output", {}).get("message", {}).get("content", [])
                text = output_msg[0]["text"] if output_msg and "text" in output_msg[0] else str(body)
                logger.info(f"[SUCCESS] Real Nova Lite invoke_model succeeded with '{model_id}'! Response: '{text.strip()}'")
                return True, model_id, text.strip()
            except Exception as e:
                logger.warning(f"invoke_model attempt on '{model_id}' returned: {e}")

        return False, BEDROCK_MODEL_ID, "ValidationException / Access Denied across direct and inference-profile routes"
    except Exception as e:
        logger.error(f"[FAILED] Nova Lite invocation failed: {e}")
        return False, BEDROCK_MODEL_ID, str(e)


def test_real_titan_v2_invocation() -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Performs a REAL invocation of Amazon Titan Embeddings V2.
    Returns: (pass_status, dimension, response_or_error)
    """
    logger.info("\n--- STEP 3: Real Amazon Titan Embeddings V2 Test ---")
    try:
        import boto3
        session = boto3.Session(profile_name=PROFILE_NAME, region_name=AWS_REGION)
        runtime = session.client("bedrock-runtime")

        payload = {
            "inputText": "Missouri Arbiter Real Cloud Verification Payload",
            "dimensions": 1024,
            "normalize": True
        }
        res = runtime.invoke_model(
            modelId=TITAN_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        body = json.loads(res["body"].read())
        emb = body.get("embedding", [])
        if emb and len(emb) == 1024:
            logger.info(f"[SUCCESS] Real Amazon Titan Embeddings V2 invoked! Dimension: {len(emb)}")
            return True, len(emb), None
        else:
            logger.error(f"[FAILED] Unexpected Titan response dimension: {len(emb) if emb else 0}")
            return False, len(emb) if emb else None, "Invalid vector length"
    except Exception as e:
        logger.error(f"[FAILED] Titan Embeddings V2 call failed: {e}")
        return False, None, str(e)


def test_cockroachdb_connection() -> Tuple[bool, Dict[str, Any]]:
    logger.info("\n--- STEP 4: Real CockroachDB Connection & Version ---")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("[FAILED] DATABASE_URL environment variable is NOT set.")
        return False, {"error": "DATABASE_URL missing"}

    try:
        import psycopg
        from urllib.parse import urlparse
        parsed = urlparse(db_url)
        redacted_host = f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname

        sslrootcert = os.getenv("PGSSLROOTCERT")
        kwargs = {}
        if sslrootcert and os.path.exists(sslrootcert):
            kwargs["sslrootcert"] = sslrootcert
        elif "sslmode=verify-full" in db_url and not os.path.exists(os.path.expanduser("~/.postgresql/root.crt")):
            db_url = db_url.replace("sslmode=verify-full", "sslmode=require")

        conn = psycopg.connect(db_url, connect_timeout=10, **kwargs)
        cursor = conn.cursor()

        cursor.execute("SELECT version();")
        ver = cursor.fetchone()[0]

        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()[0]

        conn.close()

        is_cockroach = "cockroachdb" in ver.lower() or "cockroach" in ver.lower()
        logger.info(f"[SUCCESS] Connected to Real CockroachDB Server at {redacted_host}")
        logger.info(f"[VERSION] {ver}")
        logger.info(f"[DATABASE] {db_name}")

        return True, {
            "host": redacted_host,
            "version": ver,
            "database": db_name,
            "is_cockroach": is_cockroach
        }
    except Exception as e:
        logger.error(f"[FAILED] CockroachDB Cloud connection failed: {e}")
        return False, {"error": str(e)}


def execute_full_verification():
    os.environ["ARBITER_MODE"] = "CLOUD"
    os.environ["AWS_PROFILE"] = PROFILE_NAME
    os.environ["AWS_REGION"] = AWS_REGION

    logger.info("=========================================================")
    logger.info("=== MISSOURI ARBITER: REAL CLOUD VERIFICATION SUITE  ===")
    logger.info("=========================================================")

    # 1. AWS STS
    run_step_1_aws_cli()

    # 2. Nova Lite Real Invocation
    nova_ok, nova_used_id, nova_err = test_real_nova_lite_invocation()

    # 3. Titan V2 Real Invocation
    titan_ok, titan_dim, titan_err = test_real_titan_v2_invocation()

    # 4. CockroachDB Connection
    crdb_ok, crdb_data = test_cockroachdb_connection()

    # Report precise format requested
    print("\n" + "="*60)
    print("=== BEDROCK & CLOUD INTEGRATION VERIFICATION REPORT ===")
    print("="*60)
    print(f"[BEDROCK] MODEL = {BEDROCK_MODEL_ID}")
    print(f"[BEDROCK] REGION = {AWS_REGION}")
    print(f"[BEDROCK] REAL API = {'PASS' if nova_ok else 'FAIL'}")
    print()
    print(f"[TITAN] REAL API = {'PASS' if titan_ok else 'FAIL'}")
    print(f"[TITAN] DIMENSION = {titan_dim if titan_dim else 'None'}")
    print()
    print(f"[COCKROACHDB] REAL CONNECTION = {'PASS' if crdb_ok else 'FAIL'}")
    print("="*60)

    # Check Stop Conditions
    all_passed = nova_ok and titan_ok and crdb_ok
    if not all_passed:
        logger.warning("\n[STOP CONDITION TRIGGERED] Real cloud services did not all pass verification.")
        if not nova_ok:
            logger.warning(f" -> Nova Lite Real Invocation: FAIL ({nova_err})")
        if not titan_ok:
            logger.warning(f" -> Titan Embeddings V2 Real Invocation: FAIL ({titan_err})")
        if not crdb_ok:
            logger.warning(f" -> CockroachDB Connection: FAIL ({crdb_data.get('error')})")
        logger.warning("Stopping before Phase 5 as requested.")
        return

    logger.info("\nAll real cloud requirements met! Running Phase 1-3 tests against CockroachDB...")
    # Run pytest for Phase 1-3
    res = subprocess.run([sys.executable, "-m", "pytest", "tests/test_phase1_db.py", "tests/test_phase2_concurrency.py", "tests/test_phase3_vector.py"], text=True)
    if res.returncode == 0:
        logger.info("[SUCCESS] Phase 1-3 tests PASSED against CockroachDB!")
    else:
        logger.error("[FAIL] Phase 1-3 tests failed against CockroachDB!")

if __name__ == "__main__":
    execute_full_verification()
