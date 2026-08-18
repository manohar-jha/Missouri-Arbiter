"""
Amazon Bedrock LLM Provider Abstraction Layer
Provides a configurable, unified interface for agent reasoning, tool calling, and orchestration.
Supports Amazon Nova Lite (amazon.nova-lite-v1:0) as primary hackathon model and Anthropic Claude as fallback/configurable target.
Enforces ARBITER_MODE=CLOUD constraints (no mock fallbacks in CLOUD mode).
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("bedrock_provider")

DEFAULT_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
DEFAULT_AWS_PROFILE = os.getenv("AWS_PROFILE", "manohar_kumar_jha")
DEFAULT_AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


class BedrockAgentProvider:
    """
    Abstractions for Amazon Bedrock LLM Invocation.
    Decouples agent logic from model-specific request/response schemas.
    """

    def __init__(
        self,
        model_id: Optional[str] = None,
        region_name: Optional[str] = None,
        profile_name: Optional[str] = None
    ):
        self.model_id = model_id or os.getenv("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)
        self.region_name = region_name or os.getenv("AWS_REGION", DEFAULT_AWS_REGION)
        self.profile_name = profile_name or os.getenv("AWS_PROFILE", DEFAULT_AWS_PROFILE)
        self.mode = os.getenv("ARBITER_MODE", "LOCAL").upper()

    def _get_client(self):
        """Creates a boto3 bedrock-runtime client."""
        import boto3
        session = boto3.Session(
            profile_name=self.profile_name,
            region_name=self.region_name
        )
        return session.client("bedrock-runtime")

    def invoke_reasoning(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.2
    ) -> str:
        """
        Invokes LLM for agent reasoning and orchestration.
        Uses Bedrock Converse API as primary unified interface, with format-specific invoke_model fallbacks.
        """
        if self.mode == "CLOUD":
            logger.info(f"[BEDROCK] Invoking Real Cloud Model '{self.model_id}' in region '{self.region_name}'")

        try:
            client = self._get_client()

            # 1. Primary Unified Approach: Bedrock Converse API
            messages = [{"role": "user", "content": [{"text": prompt}]}]
            kwargs = {
                "modelId": self.model_id,
                "messages": messages,
                "inferenceConfig": {
                    "maxTokens": max_tokens,
                    "temperature": temperature
                }
            }
            if system_prompt:
                kwargs["system"] = [{"text": system_prompt}]

            try:
                response = client.converse(**kwargs)
                content = response.get("output", {}).get("message", {}).get("content", [])
                if content and "text" in content[0]:
                    return content[0]["text"]
            except Exception as conv_err:
                logger.debug(f"Converse API call did not complete: {conv_err}. Trying direct invoke_model...")

            # 2. Format-Specific invoke_model logic
            if "nova" in self.model_id.lower():
                payload = {
                    "inferenceConfig": {
                        "max_new_tokens": max_tokens,
                        "temperature": temperature
                    },
                    "messages": [
                        {"role": "user", "content": [{"text": prompt}]}
                    ]
                }
                if system_prompt:
                    payload["system"] = [{"text": system_prompt}]
                    
                res = client.invoke_model(
                    modelId=self.model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(payload)
                )
                body = json.loads(res["body"].read())
                # Handle Nova response body
                output_msg = body.get("output", {}).get("message", {}).get("content", [])
                if output_msg and "text" in output_msg[0]:
                    return output_msg[0]["text"]
                return json.dumps(body)

            elif "claude" in self.model_id.lower():
                payload = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [{"role": "user", "content": prompt}]
                }
                if system_prompt:
                    payload["system"] = system_prompt
                    
                res = client.invoke_model(
                    modelId=self.model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(payload)
                )
                body = json.loads(res["body"].read())
                content = body.get("content", [])
                if content and "text" in content[0]:
                    return content[0]["text"]
                return json.dumps(body)

            else:
                # Generic fallback payload
                payload = {"prompt": prompt, "max_tokens": max_tokens}
                res = client.invoke_model(
                    modelId=self.model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(payload)
                )
                return res["body"].read().decode("utf-8")

        except Exception as e:
            if self.mode == "CLOUD":
                raise RuntimeError(
                    f"[MODE: CLOUD] Bedrock API call failed for model '{self.model_id}': {e}. "
                    f"Local fallback is strictly DISABLED in CLOUD mode!"
                )
            logger.warning(f"Bedrock invocation failed ({e}). Returning local mock reasoning in LOCAL mode.")
            return f"[LOCAL MOCK REASONING] Agent decision for prompt snippet: {prompt[:40]}..."


def get_agent_provider(model_id: Optional[str] = None) -> BedrockAgentProvider:
    """Factory method to get a configured BedrockAgentProvider instance."""
    return BedrockAgentProvider(model_id=model_id)
