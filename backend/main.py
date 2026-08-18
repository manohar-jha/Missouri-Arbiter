"""
Missouri Arbiter FastAPI Application Entry Point
Provides REST API endpoints for agent orchestration, live traffic simulator, decision audit ledger, and serves frontend web dashboard.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db.connection import get_db_connection, _load_dotenv
from backend.agent.arbiter_agent import MissouriArbiterAgent
from backend.agent.tools import SIMULATOR_INSTANCE, make_json_serializable
from backend.agent.providers import get_llm_provider

_load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("main_api")

app = FastAPI(
    title="Missouri Arbiter AI",
    description="Agentic AI River Corridor Arbitration & Traffic Management System",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- REQUEST SCHEMAS ---

class AgentQueryRequest(BaseModel):
    prompt: str


class ClosureInjectRequest(BaseModel):
    channel_id: str
    reason: Optional[str] = "Severe Storm Hazard"
    max_draft_limit: Optional[float] = None


class StepSimRequest(BaseModel):
    delta_seconds: Optional[float] = 60.0


# --- API ENDPOINTS ---

@app.get("/health")
def health_check():
    """Diagnostic health check for CockroachDB Cloud, LLM Provider, and system state."""
    db_status = "DISCONNECTED"
    db_version = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        row = cursor.fetchone()
        if isinstance(row, dict):
            ver = list(row.values())[0]
        elif isinstance(row, (tuple, list)):
            ver = row[0]
        else:
            ver = str(row)
        conn.close()
        db_status = "CONNECTED (CockroachDB Cloud)"
        db_version = str(ver)[:60]
    except Exception as e:
        import traceback
        logger.error(f"Health check DB error: {traceback.format_exc()}")
        db_status = f"FAILED: {e}"

    provider_name = os.getenv("LLM_PROVIDER", "groq").upper()
    has_groq_key = bool(os.getenv("GROQ_API_KEY"))

    return {
        "status": "HEALTHY",
        "arbiter_mode": os.getenv("ARBITER_MODE", "LOCAL"),
        "cockroachdb_status": db_status,
        "cockroachdb_version": db_version,
        "llm_provider": provider_name,
        "groq_api_key_configured": has_groq_key,
        "embedding_provider": os.getenv("EMBEDDING_PROVIDER", "auto")
    }


@app.post("/api/agent/query")
def agent_query(req: AgentQueryRequest):
    """
    Main Agent Query Endpoint.
    Invokes MissouriArbiterAgent to execute real tool calls against CockroachDB & simulator.
    """
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt string cannot be empty.")

    try:
        agent = MissouriArbiterAgent()
        result = agent.process_request(req.prompt)
        return result
    except Exception as e:
        logger.error(f"Agent processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vessels")
def get_vessels():
    """Returns current vessel fleet state."""
    return {"status": "SUCCESS", "vessels": list(SIMULATOR_INSTANCE.vessels.values())}


@app.get("/api/channels")
def get_channels():
    """Returns channel corridor definitions and active restrictions."""
    return {
        "status": "SUCCESS",
        "channels": SIMULATOR_INSTANCE.channels,
        "restrictions": SIMULATOR_INSTANCE.active_restrictions
    }


@app.get("/api/reservations")
def get_reservations():
    """Queries confirmed channel reservations from CockroachDB."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channel_reservations WHERE status = 'CONFIRMED' ORDER BY created_at DESC;")
        rows = cursor.fetchall()
        conn.close()
        return make_json_serializable({"status": "SUCCESS", "reservations": [dict(r) for r in rows]})
    except Exception as e:
        logger.error(f"Failed to fetch reservations: {e}")
        return {"status": "ERROR", "message": str(e), "reservations": []}


@app.get("/api/ledger")
def get_decision_ledger():
    """Queries recent decision ledger records from CockroachDB."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM decision_ledger ORDER BY timestamp DESC LIMIT 20;")
        rows = cursor.fetchall()
        conn.close()
        return make_json_serializable({"status": "SUCCESS", "ledger_entries": [dict(r) for r in rows]})
    except Exception as e:
        logger.error(f"Failed to fetch decision ledger: {e}")
        return {"status": "ERROR", "message": str(e), "ledger_entries": []}


@app.post("/api/simulator/inject-closure")
def inject_closure(req: ClosureInjectRequest):
    """Injects dynamic channel hazard or draft restriction into simulator."""
    SIMULATOR_INSTANCE.inject_channel_closure(
        channel_id=req.channel_id,
        reason=req.reason or "Storm Hazard",
        max_draft_limit=req.max_draft_limit
    )
    return {
        "status": "SUCCESS",
        "message": f"Closure injected on channel '{req.channel_id}'",
        "restrictions": SIMULATOR_INSTANCE.active_restrictions
    }


@app.post("/api/simulator/step")
def step_simulator(req: StepSimRequest):
    """Advances traffic simulation state by delta_seconds."""
    updates = SIMULATOR_INSTANCE.step(delta_seconds=req.delta_seconds or 60.0)
    return {"status": "SUCCESS", "vessel_updates": updates}


# Serve Frontend Web Dashboard
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def read_root():
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Missouri Arbiter API Server is Running. Frontend index.html not found."}
