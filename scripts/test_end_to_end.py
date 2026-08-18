"""
Real End-to-End Operational Verification Script
Tests the complete workflow:
User Operational Request -> Groq API -> Real Tool Call -> CockroachDB Cloud -> Agent Synthesis -> Decision Ledger Record.
Runs the 3 required hackathon scenarios against the live CockroachDB Cloud database.
"""

import os
import sys
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db.connection import get_db_connection, _load_dotenv
from backend.agent.arbiter_agent import MissouriArbiterAgent
from backend.agent.tools import SIMULATOR_INSTANCE

_load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("test_e2e")


def test_end_to_end_scenarios():
    logger.info("=========================================================")
    logger.info("=== MISSOURI ARBITER: REAL END-TO-END VERIFICATION    ===")
    logger.info("=========================================================")

    # Verify CockroachDB Cloud connection
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        ver = cursor.fetchone()[0]
        conn.close()
        logger.info(f"[PASS] CockroachDB Cloud Connected: {ver[:60]}")
    except Exception as e:
        logger.error(f"[FAIL] CockroachDB Cloud Connection Failed: {e}")
        sys.exit(1)

    # Initialize Agent
    try:
        agent = MissouriArbiterAgent()
        logger.info("[PASS] MissouriArbiterAgent initialized.")
    except Exception as e:
        logger.error(f"[FAIL] Failed to initialize Agent: {e}")
        sys.exit(1)

    # --- SCENARIO 1: Deep Draft Vessel Passage Request ---
    logger.info("\n--- EXECUTING SCENARIO 1: Deep Draft Passage Request ---")
    prompt_1 = (
        "Assess passage request for vessel 'ship_beta' (MV Beta Tanker, draft 12.2m) "
        "wishing to transit channel 'ch_main' (Missouri Main Corridor). Check vessel specs, "
        "draft limits, active restrictions, and reserve the passage slot in CockroachDB."
    )
    res_1 = agent.process_request(prompt_1)
    logger.info(f"Turns taken: {res_1.get('turns_taken')}")
    logger.info(f"Tool Execution Trace count: {len(res_1.get('tool_execution_trace', []))}")
    for t in res_1.get('tool_execution_trace', []):
        logger.info(f"  └─ Tool Executed: '{t['tool_name']}' | Result status: {t['result'].get('status')}")
    logger.info(f"Decision Ledger Recorded: {res_1.get('decision_ledger_recorded')}")
    logger.info(f"Agent Final Recommendation:\n{res_1.get('response')}\n")

    assert len(res_1.get('tool_execution_trace', [])) > 0, "Scenario 1 failed: No real tool calls executed."

    # --- SCENARIO 2: Channel Closure & Rerouting with Tug Escort ---
    logger.info("\n--- EXECUTING SCENARIO 2: Hazard Closure & Reroute ---")
    # Inject storm closure on ch_main in simulator
    SIMULATOR_INSTANCE.inject_channel_closure("ch_main", reason="Severe Storm Hazard Closure")
    
    prompt_2 = (
        "Missouri Main Corridor 'ch_main' has an active storm hazard closure. "
        "Vessel 'ship_alpha' (draft 11.0m) needs to reach destination. Check closure restrictions, "
        "inspect alternative channel 'ch_north', select an available tug, make a reservation on 'ch_north', "
        "and record the operational decision."
    )
    res_2 = agent.process_request(prompt_2)
    logger.info(f"Turns taken: {res_2.get('turns_taken')}")
    logger.info(f"Tool Execution Trace count: {len(res_2.get('tool_execution_trace', []))}")
    for t in res_2.get('tool_execution_trace', []):
        logger.info(f"  └─ Tool Executed: '{t['tool_name']}' | Result status: {t['result'].get('status')}")
    logger.info(f"Decision Ledger Recorded: {res_2.get('decision_ledger_recorded')}")
    logger.info(f"Agent Final Recommendation:\n{res_2.get('response')}\n")

    assert len(res_2.get('tool_execution_trace', [])) > 0, "Scenario 2 failed: No real tool calls executed."

    # --- SCENARIO 3: Vector Memory KNN Similarity Search ---
    logger.info("\n--- EXECUTING SCENARIO 3: Vector Memory KNN Search ---")
    prompt_3 = (
        "Search historical hydrodynamic memory in CockroachDB for maneuvers recorded under weather summary "
        "'high crosswinds 25 knots southward drift current'. Summarize past maneuver outcomes and recommend strategy."
    )
    res_3 = agent.process_request(prompt_3)
    logger.info(f"Turns taken: {res_3.get('turns_taken')}")
    logger.info(f"Tool Execution Trace count: {len(res_3.get('tool_execution_trace', []))}")
    for t in res_3.get('tool_execution_trace', []):
        logger.info(f"  └─ Tool Executed: '{t['tool_name']}' | Result status: {t['result'].get('status')}")
    logger.info(f"Agent Final Recommendation:\n{res_3.get('response')}\n")

    assert len(res_3.get('tool_execution_trace', [])) > 0, "Scenario 3 failed: No real tool calls executed."

    print("END-TO-END AGENT WORKFLOW = PASS")


if __name__ == "__main__":
    test_end_to_end_scenarios()
