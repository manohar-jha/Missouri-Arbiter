"""
Missouri Arbiter Tool Calling Registry & Handlers
Maps LLM tool calls directly to real Python functions, CockroachDB queries, transactions, and simulator operations.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from backend.db.connection import get_db_connection, execute_transaction_with_retry
from backend.db.repository import (
    get_all_reservations,
    reserve_channel_and_tug,
    upsert_vessel,
    upsert_channel,
    upsert_tug,
    ensure_seed_data
)
from backend.db.vector_memory import search_historical_maneuvers, generate_titan_embedding
from backend.simulator.traffic_sim import DeterministicTrafficSimulator

logger = logging.getLogger("agent_tools")

# Global singleton simulator instance for live state
SIMULATOR_INSTANCE = DeterministicTrafficSimulator()


from decimal import Decimal
from uuid import UUID
from datetime import datetime, date, time

def make_json_serializable(value: Any) -> Any:
    """
    Recursively converts database-returned non-JSON-native objects (Decimal, UUID, datetime/date/time)
    into standard JSON-serializable types.
    - Decimal -> float
    - UUID -> str
    - datetime/date/time -> ISO-formatted str
    - dict -> recursively sanitized dict
    - list/tuple/set -> recursively sanitized list
    """
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: make_json_serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_serializable(v) for v in value]
    return value


# --- TOOL IMPLEMENTATION FUNCTIONS ---

def lookup_vessel(vessel_id: Optional[str] = None) -> Dict[str, Any]:
    """Queries vessel state from CockroachDB and simulator."""
    sim_vessels = SIMULATOR_INSTANCE.vessels
    if vessel_id:
        if vessel_id in sim_vessels:
            return make_json_serializable({"status": "SUCCESS", "vessel": sim_vessels[vessel_id]})
        # Query CockroachDB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vessels WHERE vessel_id = %s;", (vessel_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return make_json_serializable({"status": "SUCCESS", "vessel": dict(row)})
        return {"status": "NOT_FOUND", "message": f"Vessel '{vessel_id}' not found."}
    
    return make_json_serializable({"status": "SUCCESS", "vessels": list(sim_vessels.values())})


def lookup_channel(channel_id: Optional[str] = None) -> Dict[str, Any]:
    """Queries channel limits and coordinates from CockroachDB and simulator."""
    sim_channels = SIMULATOR_INSTANCE.channels
    if channel_id:
        if channel_id in sim_channels:
            return make_json_serializable({"status": "SUCCESS", "channel": sim_channels[channel_id]})
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels WHERE channel_id = %s;", (channel_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return make_json_serializable({"status": "SUCCESS", "channel": dict(row)})
        return {"status": "NOT_FOUND", "message": f"Channel '{channel_id}' not found."}
        
    return make_json_serializable({"status": "SUCCESS", "channels": sim_channels})


def lookup_restrictions(channel_id: Optional[str] = None) -> Dict[str, Any]:
    """Checks active navigation restrictions or channel closures."""
    restrictions = SIMULATOR_INSTANCE.active_restrictions
    if channel_id:
        restr = restrictions.get(channel_id)
        return make_json_serializable({"status": "SUCCESS", "channel_id": channel_id, "restriction": restr or "NONE_ACTIVE"})
    return make_json_serializable({"status": "SUCCESS", "active_restrictions": list(restrictions.values())})


def select_available_tug(min_bollard_pull: float = 0.0) -> Dict[str, Any]:
    """Queries CockroachDB tug_fleet for available tugboats matching bollard pull requirement."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM tug_fleet WHERE status = 'AVAILABLE' AND bollard_pull_tons >= %s ORDER BY bollard_pull_tons DESC;",
        (min_bollard_pull,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    tugs = [dict(r) for r in rows]
    if not tugs:
        # Provide default available tug from fleet repository if table is freshly initialized
        default_tug = {"tug_id": "tug_titan_1", "name": "Titan Tug Alpha", "bollard_pull_tons": 75.0, "status": "AVAILABLE"}
        return make_json_serializable({"status": "SUCCESS", "recommended_tug": default_tug, "all_available": [default_tug]})
        
    return make_json_serializable({"status": "SUCCESS", "recommended_tug": tugs[0], "all_available": tugs})


def make_reservation_tool(
    channel_id: str,
    vessel_id: str,
    start_time: str,
    end_time: str,
    tug_id: Optional[str] = None
) -> Dict[str, Any]:
    """Performs concurrency-safe transactional reservation in CockroachDB Cloud."""
    def tx(conn):
        ensure_seed_data(conn)
        return reserve_channel_and_tug(
            conn,
            channel_id=channel_id,
            vessel_id=vessel_id,
            start_time=start_time,
            end_time=end_time,
            tug_id=tug_id
        )

    try:
        res = execute_transaction_with_retry(get_db_connection, tx)
        return make_json_serializable({"status": "SUCCESS", "reservation": res})
    except Exception as e:
        logger.error(f"Reservation failed: {e}")
        return make_json_serializable({"status": "RESERVATION_FAILED", "error": str(e)})


def search_hydrodynamic_memory_tool(weather_summary: str, limit: int = 3) -> Dict[str, Any]:
    """Queries CockroachDB hydrodynamic_memory using 1024-dimensional vector similarity."""
    conn = get_db_connection()
    try:
        # Generate vector for query
        q_vec = generate_titan_embedding(weather_summary, dimensions=1024)
        results = search_historical_maneuvers(conn, query_vector=q_vec, limit=limit)
        conn.close()
        
        return make_json_serializable({
            "status": "SUCCESS",
            "query_text": weather_summary,
            "matched_maneuvers": results
        })
    except Exception as e:
        conn.close()
        logger.error(f"Hydrodynamic memory search error: {e}")
        return make_json_serializable({"status": "ERROR", "error": str(e)})


def record_decision_ledger_tool(
    vessel_id: str,
    channel_id: str,
    decision_type: str,
    recommendation: str,
    risk_score: float = 0.0
) -> Dict[str, Any]:
    """Logs the final agent operational decision to CockroachDB decision_ledger table."""
    conn = get_db_connection()
    try:
        ensure_seed_data(conn)
        cursor = conn.cursor()
        details_json = json.dumps({"risk_score": risk_score, "decision_type": decision_type})
        query = """
        INSERT INTO decision_ledger (vessel_id, channel_id, event_type, summary, details)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING ledger_id, timestamp;
        """
        cursor.execute(query, (vessel_id, channel_id, decision_type, recommendation, details_json))
        row = cursor.fetchone()
        conn.commit()
        conn.close()
        d_id = row["ledger_id"] if isinstance(row, dict) else row[0]
        return make_json_serializable({
            "status": "SUCCESS",
            "decision_id": d_id,
            "vessel_id": vessel_id,
            "channel_id": channel_id,
            "decision_type": decision_type,
            "recommendation": recommendation,
            "risk_score": risk_score
        })
    except Exception as e:
        conn.close()
        logger.error(f"Failed to record decision ledger: {e}")
        return make_json_serializable({"status": "ERROR", "error": str(e)})


def get_traffic_simulation_state_tool(**kwargs) -> Dict[str, Any]:
    """Retrieves full traffic simulator snapshot."""
    return make_json_serializable({"status": "SUCCESS", "simulation_state": SIMULATOR_INSTANCE.get_state()})


# --- TOOL SCHEMAS FOR OPENAI / GROQ FORMAT ---

OPENAI_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_vessel",
            "description": "Retrieves vessel physical dimensions (length, draft, speed, coordinates) by vessel_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vessel_id": {"type": "string", "description": "Unique vessel identifier (e.g. ship_alpha, ship_beta)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_channel",
            "description": "Retrieves channel physical limits (max_draft, width_meters, waypoints) by channel_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_id": {"type": "string", "description": "Unique channel identifier (e.g. ch_main, ch_north)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_restrictions",
            "description": "Checks active weather closures or draft restrictions on Missouri river channels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_id": {"type": "string", "description": "Optional channel identifier to filter restrictions."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "select_available_tug",
            "description": "Finds available tugboats in CockroachDB tug_fleet matching bollard pull requirements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_bollard_pull": {"type": "number", "description": "Minimum required bollard pull capacity in tons."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reserve_channel_and_tug",
            "description": "Executes a concurrency-safe transactional reservation in CockroachDB for a channel and tug.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_id": {"type": "string", "description": "Channel ID to reserve"},
                    "vessel_id": {"type": "string", "description": "Vessel ID reserving the corridor"},
                    "start_time": {"type": "string", "description": "ISO start timestamp (e.g. 2026-08-18T10:00:00Z)"},
                    "end_time": {"type": "string", "description": "ISO end timestamp (e.g. 2026-08-18T12:00:00Z)"},
                    "tug_id": {"type": "string", "description": "Optional Tug ID to escort"}
                },
                "required": ["channel_id", "vessel_id", "start_time", "end_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_hydrodynamic_memory",
            "description": "Performs KNN vector similarity search on historical hydrodynamic maneuvers in CockroachDB.",
            "parameters": {
                "type": "object",
                "properties": {
                    "weather_summary": {"type": "string", "description": "Description of weather/current conditions (e.g., 'high crosswinds 25 knots')"},
                    "limit": {"type": "integer", "description": "Number of nearest historical maneuvers to return."}
                },
                "required": ["weather_summary"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_decision_ledger",
            "description": "Records the final operational arbitration decision into CockroachDB decision_ledger table.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vessel_id": {"type": "string", "description": "Vessel ID"},
                    "channel_id": {"type": "string", "description": "Channel ID"},
                    "decision_type": {"type": "string", "description": "Type of decision (e.g. PASSAGE_APPROVED, REROUTED, HOLDING_PATTERN)"},
                    "recommendation": {"type": "string", "description": "Full operational recommendation text"},
                    "risk_score": {"type": "number", "description": "Assessed risk score between 0.0 and 1.0"}
                },
                "required": ["vessel_id", "channel_id", "decision_type", "recommendation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_traffic_simulation_state",
            "description": "Returns full snapshot of current Missouri river vessel positions, speeds, and channel states.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]


TOOL_FUNCTION_MAP = {
    "lookup_vessel": lookup_vessel,
    "lookup_channel": lookup_channel,
    "lookup_restrictions": lookup_restrictions,
    "select_available_tug": select_available_tug,
    "reserve_channel_and_tug": make_reservation_tool,
    "search_hydrodynamic_memory": search_hydrodynamic_memory_tool,
    "record_decision_ledger": record_decision_ledger_tool,
    "get_traffic_simulation_state": get_traffic_simulation_state_tool
}


def execute_tool_call(tool_name: str, arguments_json: str) -> Dict[str, Any]:
    """Executes a tool call by name with parsed JSON arguments."""
    if tool_name not in TOOL_FUNCTION_MAP:
        return {"status": "ERROR", "message": f"Unknown tool '{tool_name}'"}
    
    handler = TOOL_FUNCTION_MAP[tool_name]
    try:
        args = json.loads(arguments_json) if isinstance(arguments_json, str) and arguments_json.strip() else {}
        logger.info(f"Executing tool '{tool_name}' with args: {args}")
        result = handler(**args)
        return make_json_serializable(result)
    except Exception as e:
        logger.error(f"Error executing tool '{tool_name}': {e}")
        return {"status": "ERROR", "message": f"Execution error in tool '{tool_name}': {e}"}
