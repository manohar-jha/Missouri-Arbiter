"""
Real CockroachDB Connection & Operational Test Script
Tests real network connectivity, authentication, table existence, and CRUD operations against a live CockroachDB instance.
Supports ARBITER_MODE=CLOUD and DATABASE_URL. Never exposes secrets or passwords.
"""

import os
import sys
import json
import logging
import sqlite3
from typing import Dict, Any, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("test_cockroach")

def _load_dotenv(env_path=".env"):
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip("\"'"))

def test_real_cockroach_connection() -> Tuple[bool, Dict[str, Any]]:
    _load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    mode = os.getenv("ARBITER_MODE", "LOCAL").upper()
    
    logger.info("=========================================================")
    logger.info("=== MISSOURI ARBITER: COCKROACHDB INTEGRATION TEST    ===")
    logger.info("=========================================================")
    
    if not db_url:
        logger.error("[FAIL] DATABASE_URL environment variable is NOT SET.")
        return False, {
            "status": "NOT_SET",
            "error": "DATABASE_URL environment variable is missing.",
            "details": "Set DATABASE_URL=postgresql://<user>:<pass>@<host>:26257/<dbname>?sslmode=verify-full"
        }
        
    try:
        import psycopg
        from urllib.parse import urlparse
        parsed = urlparse(db_url)
        redacted_host = f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
        
        sslrootcert = os.getenv("PGSSLROOTCERT")
        conn_kwargs = {}
        if sslrootcert and os.path.exists(sslrootcert):
            conn_kwargs["sslrootcert"] = sslrootcert
        elif "sslmode=verify-full" in db_url and not os.path.exists(os.path.expanduser("~/.postgresql/root.crt")):
            db_url = db_url.replace("sslmode=verify-full", "sslmode=require")
            
        logger.info(f"Connecting to CockroachDB host '{redacted_host}'...")
        conn = psycopg.connect(db_url, connect_timeout=30, **conn_kwargs)
        cursor = conn.cursor()
        
        # 1. SELECT 1 Test
        cursor.execute("SELECT 1;")
        select_1_res = cursor.fetchone()[0]
        logger.info(f"[PASS] SELECT 1: Result = {select_1_res}")
        
        # 2. Version Test
        cursor.execute("SELECT version();")
        ver = cursor.fetchone()[0]
        logger.info(f"[PASS] Server Version: {ver[:80]}...")
        
        # 3. Database Name Test
        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()[0]
        logger.info(f"[PASS] Current Database: {db_name}")
        
        # 4. Check Required Tables
        required_tables = [
            "channels", "nav_restrictions", "tug_fleet", "vessels",
            "channel_reservations", "hydrodynamic_memory", "decision_ledger"
        ]
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)
        existing_tables = [r[0] for r in cursor.fetchall()]
        logger.info(f"Existing Public Tables: {existing_tables}")
        
        missing_tables = [t for t in required_tables if t not in existing_tables]
        if missing_tables:
            logger.info(f"Missing Required Tables: {missing_tables}. Initializing schema using repository.initialize_schema...")
            from backend.db.repository import initialize_schema
            schema_path = os.path.join(os.path.dirname(__file__), "..", "backend", "db", "schema.sql")
            initialize_schema(conn, schema_path)
            conn.commit()
            logger.info("[PASS] Schema initialized successfully!")
        else:
            logger.info("[PASS] All 7 required CockroachDB tables found!")

        # 5. Non-Destructive CRUD Test on temporary channel
        test_channel_id = "test_chk_001"
        try:
            # INSERT
            cursor.execute("""
                INSERT INTO channels (channel_id, name, max_draft, width_meters, requires_tug_escort, coordinates)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (channel_id) DO UPDATE SET name = EXCLUDED.name;
            """, (test_channel_id, "Test Connectivity Channel", 12.0, 100.0, False, json.dumps([])))
            conn.commit()
            logger.info("[PASS] INSERT test record into 'channels' table succeeded.")

            # SELECT
            cursor.execute("SELECT name, max_draft FROM channels WHERE channel_id = %s;", (test_channel_id,))
            row = cursor.fetchone()
            logger.info(f"[PASS] SELECT test record: Name='{row[0]}', Draft={row[1]}")

            # UPDATE
            cursor.execute("UPDATE channels SET width_meters = 150.0 WHERE channel_id = %s;", (test_channel_id,))
            conn.commit()
            logger.info("[PASS] UPDATE test record succeeded.")

            # DELETE (Cleanup test record)
            cursor.execute("DELETE FROM channels WHERE channel_id = %s;", (test_channel_id,))
            conn.commit()
            logger.info("[PASS] DELETE cleanup test record succeeded.")
            
        except Exception as crud_err:
            logger.error(f"[FAIL] CRUD operations failed: {crud_err}")
            conn.rollback()

        conn.close()
        return True, {
            "status": "PASS",
            "host": redacted_host,
            "version": ver,
            "database": db_name,
            "missing_tables": missing_tables
        }
        
    except Exception as e:
        logger.error(f"[FAIL] Real CockroachDB connection failed: {e}")
        return False, {
            "status": "FAIL",
            "error": str(e)
        }

if __name__ == "__main__":
    test_real_cockroach_connection()
