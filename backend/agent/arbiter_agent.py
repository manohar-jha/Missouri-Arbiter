"""
Missouri Arbiter Agent Orchestration Engine
Multi-turn agent reasoning loop using LLMProvider and Real Tool Execution against CockroachDB Cloud.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from backend.agent.providers import get_llm_provider, LLMProvider
from backend.agent.tools import OPENAI_TOOL_DEFINITIONS, execute_tool_call

logger = logging.getLogger("arbiter_agent")

SYSTEM_PROMPT = """You are Missouri Arbiter, an autonomous Agentic AI orchestrator for Missouri River maritime traffic, passage authorization, and channel safety.

You have direct access to REAL operational tools connected to a live CockroachDB Cloud cluster and maritime traffic simulator.

RULES:
1. ALWAYS inspect vessel parameters (draft, length), channel limits, and active restrictions using tools before authorizing passage.
2. If draft exceeds channel max draft or channel is closed, check alternative channels or recommend tug assistance / holding pattern.
3. Use `select_available_tug` if tug escort is required.
4. Use `reserve_channel_and_tug` to lock channel passage slots in CockroachDB cleanly.
5. Use `search_hydrodynamic_memory` to check historical maneuver strategies under severe weather.
6. ALWAYS call `record_decision_ledger` at the end to record your operational recommendation into CockroachDB.
7. Be clear, concise, and structured in your final operational response.
"""


class MissouriArbiterAgent:
    """
    Primary Agent Orchestrator.
    Decoupled from LLM vendor specifics via LLMProvider interface.
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or get_llm_provider()

    def process_request(self, user_prompt: str, max_turns: int = 10) -> Dict[str, Any]:
        """
        Executes multi-turn agent reasoning loop:
        User Request -> LLM -> Tool Call(s) -> Real Python/CockroachDB Execution -> LLM Synthesis -> Final Decision.
        """
        logger.info(f"[AGENT] Processing operational request: '{user_prompt}'")
        messages = [{"role": "user", "content": user_prompt}]
        tool_execution_trace = []
        decision_recorded = False

        for turn in range(max_turns):
            logger.info(f"[AGENT] Turn {turn + 1}/{max_turns} invoking LLM provider...")
            response_msg = self.provider.invoke_with_tools(
                messages=messages,
                tools=OPENAI_TOOL_DEFINITIONS,
                system_prompt=SYSTEM_PROMPT,
                max_tokens=1000,
                temperature=0.0
            )

            # Check if LLM returned tool calls
            tool_calls = response_msg.get("tool_calls")
            if tool_calls and len(tool_calls) > 0:
                logger.info(f"[AGENT] LLM requested {len(tool_calls)} tool call(s).")
                
                # Append assistant message with tool calls to trajectory
                messages.append(response_msg)

                for tc in tool_calls:
                    tc_id = tc.get("id", f"call_turn_{turn}")
                    func_info = tc.get("function", {})
                    tool_name = func_info.get("name", "")
                    raw_args = func_info.get("arguments", "{}")

                    logger.info(f"[AGENT] Executing tool '{tool_name}'...")
                    result = execute_tool_call(tool_name, raw_args)
                    
                    if tool_name == "record_decision_ledger" and result.get("status") == "SUCCESS":
                        decision_recorded = True

                    trace_entry = {
                        "turn": turn + 1,
                        "tool_name": tool_name,
                        "arguments": raw_args,
                        "result": result
                    }
                    tool_execution_trace.append(trace_entry)

                    # Append tool result message for LLM context
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "name": tool_name,
                        "content": json.dumps(result)
                    })
            else:
                # LLM produced final response
                content = response_msg.get("content", "")
                logger.info(f"[AGENT] Reasoning complete in turn {turn + 1}.")
                return {
                    "status": "SUCCESS",
                    "request": user_prompt,
                    "response": content,
                    "tool_execution_trace": tool_execution_trace,
                    "decision_ledger_recorded": decision_recorded,
                    "turns_taken": turn + 1
                }

        # Fallback if max_turns reached
        return {
            "status": "COMPLETED_MAX_TURNS",
            "request": user_prompt,
            "response": messages[-1].get("content", "Operation completed max iterations."),
            "tool_execution_trace": tool_execution_trace,
            "decision_ledger_recorded": decision_recorded,
            "turns_taken": max_turns
        }
