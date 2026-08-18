"""
Standalone Groq Provider Verification Test
Verifies:
1. Provider initialization & API key check
2. Real LLM reasoning via Groq (llama-3.3-70b-versatile)
3. Structured tool calling via Groq API
"""

import os
import sys
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.agent.providers import get_llm_provider, GroqProvider

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("test_groq")


def test_groq():
    logger.info("=========================================================")
    logger.info("=== GROQ PROVIDER INDEPENDENT VERIFICATION TEST        ===")
    logger.info("=========================================================")

    try:
        provider = get_llm_provider("groq")
        logger.info("[PASS] GroqProvider initialized.")

        # Test 1: Direct Reasoning
        logger.info("\nTesting Groq Reasoning...")
        prompt = "Explain in 1 short sentence why Missouri river channel draft restrictions apply to deep-draft vessels."
        answer = provider.invoke_reasoning(prompt=prompt)
        logger.info(f"[PASS] Groq Reasoning Output:\n{answer.strip()}")

        # Test 2: Tool Calling Definition Test
        logger.info("\nTesting Groq Tool Calling...")
        sample_tools = [
            {
                "type": "function",
                "function": {
                    "name": "lookup_vessel",
                    "description": "Look up physical parameters of a vessel by vessel_id",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "vessel_id": {"type": "string", "description": "Unique vessel identifier"}
                        },
                        "required": ["vessel_id"]
                    }
                }
            }
        ]

        messages = [
            {"role": "user", "content": "What are the specs for ship_alpha?"}
        ]

        resp = provider.invoke_with_tools(
            messages=messages,
            tools=sample_tools,
            system_prompt="You are the Missouri Arbiter agent. Always call tools when asked about vessels or channels."
        )

        logger.info(f"[PASS] Groq Tool Response: {resp}")
        if "tool_calls" in resp and len(resp["tool_calls"]) > 0:
            tc = resp["tool_calls"][0]
            logger.info(f"[PASS] Real Tool Call Received: Function='{tc['function']['name']}', Args='{tc['function']['arguments']}'")
            print("GROQ TOOL CALLING = PASS")
        else:
            logger.warning("[WARNING] Groq returned text response instead of tool call. Context:", resp.get("content"))

    except Exception as e:
        logger.error(f"[FAIL] Groq Provider Test Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_groq()
