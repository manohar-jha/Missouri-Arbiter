"""
LLM Provider Abstraction Layer
Provides a provider-agnostic interface for agent reasoning and real tool calling.
Supports Groq (llama-3.3-70b-versatile) for real-time hackathon demo and Bedrock (amazon.nova-lite-v1:0) for production.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from backend.bedrock_provider import BedrockAgentProvider

logger = logging.getLogger("agent_providers")

GROQ_DEFAULT_MODEL = os.getenv("GROQ_MODEL_ID", "openai/gpt-oss-120b")
BEDROCK_DEFAULT_MODEL = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")


def _load_dotenv(env_path=".env"):
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip("\"'"))


class LLMProvider(ABC):
    """Abstract base interface for LLM Agent reasoning and tool execution."""

    @abstractmethod
    def invoke_reasoning(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.2
    ) -> str:
        """Standard text completion for reasoning."""
        pass

    @abstractmethod
    def invoke_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 800,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Tool calling completion. Returns a message dict with optional 'tool_calls' or 'content'.
        """
        pass


class GroqProvider(LLMProvider):
    """
    Real Groq API LLM Provider using OpenAI-compatible chat completions endpoint.
    Communicates via standard HTTP with full tool calling capability.
    """

    def __init__(self, model_id: Optional[str] = None):
        _load_dotenv()
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model_id = model_id or os.getenv("GROQ_MODEL_ID", GROQ_DEFAULT_MODEL)
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def _ensure_api_key(self):
        if not self.api_key:
            self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "[MODE: GROQ] GROQ_API_KEY environment variable is missing. "
                "Please configure GROQ_API_KEY in your local .env file or environment."
            )

    def invoke_reasoning(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.2
    ) -> str:
        self._ensure_api_key()
        msg_payload = []
        if system_prompt:
            msg_payload.append({"role": "system", "content": system_prompt})
        msg_payload.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_id,
            "messages": msg_payload,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "MissouriArbiter/2.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"] or ""
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            logger.error(f"Groq API HTTPError ({e.code}): {err_body}")
            raise RuntimeError(f"[MODE: GROQ] Groq API returned error HTTP {e.code}: {err_body}")
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            raise RuntimeError(f"[MODE: GROQ] Groq API request failed: {e}")

    def invoke_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 800,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        self._ensure_api_key()
        formatted_messages = []
        if system_prompt and not any(m.get("role") == "system" for m in messages):
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)

        payload = {
            "model": self.model_id,
            "messages": formatted_messages,
            "tools": tools,
            "tool_choice": "auto",
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "MissouriArbiter/2.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                message = data["choices"][0]["message"]
                return message
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            logger.error(f"Groq API Tool Calling HTTPError ({e.code}): {err_body}")
            raise RuntimeError(f"[MODE: GROQ] Groq Tool Calling failed HTTP {e.code}: {err_body}")
        except Exception as e:
            logger.error(f"Groq Tool Calling failed: {e}")
            raise RuntimeError(f"[MODE: GROQ] Groq Tool Calling request failed: {e}")


class BedrockProvider(LLMProvider):
    """
    Bedrock LLM Provider wrapping BedrockAgentProvider for Amazon Nova Lite / Claude.
    Preserved 100% intact for production deployment when AWS verification is complete.
    """

    def __init__(self, model_id: Optional[str] = None):
        self.inner = BedrockAgentProvider(model_id=model_id or BEDROCK_DEFAULT_MODEL)

    def invoke_reasoning(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.2
    ) -> str:
        return self.inner.invoke_reasoning(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )

    def invoke_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 800,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        # Formats prompt with tool definitions for Bedrock reasoning
        user_prompt = ""
        for m in messages:
            if m.get("role") == "user":
                user_prompt += m.get("content", "") + "\n"

        tool_desc = json.dumps(tools, indent=2)
        sys_with_tools = (system_prompt or "") + f"\n\nAvailable Tools:\n{tool_desc}"
        res_text = self.inner.invoke_reasoning(
            prompt=user_prompt,
            system_prompt=sys_with_tools,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return {"role": "assistant", "content": res_text}


def get_llm_provider(provider_type: Optional[str] = None) -> LLMProvider:
    """
    Factory function to retrieve configured LLM Provider.
    Reads LLM_PROVIDER from environment ('groq' vs 'bedrock'). Defaults to 'groq'.
    """
    _load_dotenv()
    selected = (provider_type or os.getenv("LLM_PROVIDER", "groq")).lower()

    if selected == "bedrock":
        logger.info("Using AWS Bedrock LLM Provider")
        return BedrockProvider()
    elif selected == "groq":
        logger.info("Using Groq LLM Provider")
        return GroqProvider()
    else:
        logger.warning(f"Unknown LLM_PROVIDER '{selected}', defaulting to GroqProvider")
        return GroqProvider()
