"""
CockroachDB Repository Layer
Contains transactional queries and concurrency-safe reservation operations.
"""

import json
import logging
import sqlite3
import re
from typing import Dict, Any, List, Optional
from backend.db.connection import BusinessValidationError

logger = logging.getLogger("db_repository")


def initialize_schema(conn, schema_sql_path: str):
    """
    Executes the SQL schema DDL file to initialize CockroachDB tables and indexes.
    Sanitizes dialect differences if running in sqlite3 fallback mode.
    """
    with open(schema_sql_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    is_sqlite = isinstance(conn, sqlite3.Connection)
    
    if is_sqlite:
        # Convert CockroachDB specific DDL to SQLite compatible syntax for local offline tests
        schema_sql = re.sub(r'VECTOR\(\d+\)', 'TEXT', schema_sql, flags=re.IGNORECASE)
        schema_sql = re.sub(r'TIMESTAMPTZ', 'TEXT', schema_sql, flags=re.IGNORECASE)
        schema_sql = re.sub(r'UUID PRIMARY KEY DEFAULT gen_random_uuid\(\)', 'VARCHAR(64) PRIMARY KEY', schema_sql, flags=re.IGNORECASE)
        # Convert HNSW index syntax to standard index syntax: ON table USING HNSW (col ops) -> ON table (col)
        schema_sql = re.sub(r'USING HNSW \(([^)\s]+)[^)]*\)', r'(\1)', schema_sql, flags=re.IGNORECASE)
    
    cursor = conn.cursor()
    if is_sqlite:
        cursor.executescript(schema_sql)
    else:
        cursor.execute(schema_sql)
    logger.info("Schema initialized successfully.")


def ensure_seed_data(conn):
    """Ensures default channels, vessels, and tugs exist in CockroachDB to maintain FK constraints."""
    try:
        upsert_channel(conn, "ch_main", "Missouri Main Channel", 12.0, 150.0, True, [[38.9, -92.3], [38.95, -92.25]])
        upsert_channel(conn, "ch_north", "North Bypass Corridor", 10.5, 120.0, False, [[38.96, -92.24], [39.0, -92.2]])
        upsert_channel(conn, "ch_south", "South Auxiliary Route", 11.0, 130.0, False, [[38.85, -92.35], [38.88, -92.3]])

        upsert_vessel(conn, "ship_alpha", "MV Alpha Tanker", 220.0, 11.5, 12.0, 45.0, 38.88, -92.35, "ch_main", "UNDERWAY")
        upsert_vessel(conn, "ship_beta", "MV Beta Carrier", 180.0, 10.0, 10.5, 90.0, 38.92, -92.28, "ch_main", "UNDERWAY")

        upsert_tug(conn, "tug_titan_1", "Titan Tug Alpha", 75.0, "AVAILABLE", 38.9, -92.3)
        upsert_tug(conn, "tug_titan_2", "Titan Tug Beta", 60.0, "AVAILABLE", 38.95, -92.25)
    except Exception as e:
        logger.warning(f"Failed to seed data: {e}")



def upsert_channel(conn, channel_id: str, name: str, max_draft: float, width_meters: float, requires_tug_escort: bool, coordinates: list) -> str:
    """Inserts or updates a channel physical record."""
    cursor = conn.cursor()
    coords_json = json.dumps(coordinates)
    is_sqlite = isinstance(conn, sqlite3.Connection)
    
    if is_sqlite:
        query = """
        INSERT OR REPLACE INTO channels (channel_id, name, max_draft, width_meters, requires_tug_escort, coordinates)
        VALUES (?, ?, ?, ?, ?, ?);
        """
        cursor.execute(query, (channel_id, name, max_draft, width_meters, requires_tug_escort, coords_json))
    else:
        query = """
        INSERT INTO channels (channel_id, name, max_draft, width_meters, requires_tug_escort, coordinates)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (channel_id) DO UPDATE SET
            name = EXCLUDED.name,
            max_draft = EXCLUDED.max_draft,
            width_meters = EXCLUDED.width_meters,
            requires_tug_escort = EXCLUDED.requires_tug_escort,
            coordinates = EXCLUDED.coordinates;
        """
        cursor.execute(query, (channel_id, name, max_draft, width_meters, requires_tug_escort, coords_json))
        
    return channel_id


def upsert_tug(conn, tug_id: str, name: str, bollard_pull_tons: float, status: str = "AVAILABLE", lat: float = 0.0, lon: float = 0.0) -> str:
    """Inserts or updates a tugboat record."""
    cursor = conn.cursor()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    
    if is_sqlite:
        query = """
        INSERT OR REPLACE INTO tug_fleet (tug_id, name, bollard_pull_tons, status, current_lat, current_lon)
        VALUES (?, ?, ?, ?, ?, ?);
        """
        cursor.execute(query, (tug_id, name, bollard_pull_tons, status, lat, lon))
    else:
        query = """
        INSERT INTO tug_fleet (tug_id, name, bollard_pull_tons, status, current_lat, current_lon)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (tug_id) DO UPDATE SET
            name = EXCLUDED.name,
            bollard_pull_tons = EXCLUDED.bollard_pull_tons,
            status = EXCLUDED.status,
            current_lat = EXCLUDED.current_lat,
            current_lon = EXCLUDED.current_lon;
        """
        cursor.execute(query, (tug_id, name, bollard_pull_tons, status, lat, lon))
        
    return tug_id


def upsert_vessel(conn, vessel_id: str, name: str, length_meters: float, draft_meters: float, speed_knots: float = 0.0, heading: float = 0.0, lat: float = 0.0, lon: float = 0.0, destination_id: Optional[str] = None, status: str = "UNDERWAY") -> str:
    """Inserts or updates a vessel record."""
    cursor = conn.cursor()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    
    if is_sqlite:
        query = """
        INSERT OR REPLACE INTO vessels (vessel_id, name, length_meters, draft_meters, speed_knots, heading_degrees, current_lat, current_lon, destination_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        cursor.execute(query, (vessel_id, name, length_meters, draft_meters, speed_knots, heading, lat, lon, destination_id, status))
    else:
        query = """
        INSERT INTO vessels (vessel_id, name, length_meters, draft_meters, speed_knots, heading_degrees, current_lat, current_lon, destination_id, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (vessel_id) DO UPDATE SET
            name = EXCLUDED.name,
            length_meters = EXCLUDED.length_meters,
            draft_meters = EXCLUDED.draft_meters,
            speed_knots = EXCLUDED.speed_knots,
            heading_degrees = EXCLUDED.heading_degrees,
            current_lat = EXCLUDED.current_lat,
            current_lon = EXCLUDED.current_lon,
            destination_id = EXCLUDED.destination_id,
            status = EXCLUDED.status;
        """
        cursor.execute(query, (vessel_id, name, length_meters, draft_meters, speed_knots, heading, lat, lon, destination_id, status))
        
    return vessel_id


def reserve_channel_and_tug(
    conn,
    channel_id: str,
    vessel_id: str,
    start_time: str,
    end_time: str,
    tug_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Concurrency-Safe Transactional Reservation.
    Must be called inside `execute_transaction_with_retry`.
    
    Checks temporal range overlap: (existing.start < new.end AND existing.end > new.start).
    If overlap exists, raises BusinessValidationError causing immediate transaction rollback.
    Otherwise inserts reservation and returns details.
    """
    cursor = conn.cursor()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    
    # 1. Temporal overlap check for channel
    if is_sqlite:
        check_query = """
        SELECT reservation_id, vessel_id, start_time, end_time 
        FROM channel_reservations
        WHERE channel_id = ?
          AND status = 'CONFIRMED'
          AND start_time < ?
          AND end_time > ?;
        """
        cursor.execute(check_query, (channel_id, end_time, start_time))
    else:
        check_query = """
        SELECT reservation_id, vessel_id, start_time, end_time 
        FROM channel_reservations
        WHERE channel_id = %s
          AND status = 'CONFIRMED'
          AND start_time < %s
          AND end_time > %s
        FOR UPDATE;
        """
        cursor.execute(check_query, (channel_id, end_time, start_time))
        
    overlaps = cursor.fetchall()
    
    if overlaps:
        conflict_res = overlaps[0]
        v_id = conflict_res["vessel_id"] if isinstance(conflict_res, dict) else conflict_res[1]
        raise BusinessValidationError(
            f"Temporal reservation conflict on channel '{channel_id}' between {start_time} and {end_time}. "
            f"Overlaps with active reservation by vessel '{v_id}'."
        )
    
    # 2. Temporal overlap check for tug (if specified)
    if tug_id:
        if is_sqlite:
            tug_check_query = """
            SELECT reservation_id, vessel_id 
            FROM channel_reservations
            WHERE tug_id = ?
              AND status = 'CONFIRMED'
              AND start_time < ?
              AND end_time > ?;
            """
            cursor.execute(tug_check_query, (tug_id, end_time, start_time))
        else:
            tug_check_query = """
            SELECT reservation_id, vessel_id 
            FROM channel_reservations
            WHERE tug_id = %s
              AND status = 'CONFIRMED'
              AND start_time < %s
              AND end_time > %s
            FOR UPDATE;
            """
            cursor.execute(tug_check_query, (tug_id, end_time, start_time))
            
        tug_overlaps = cursor.fetchall()
        if tug_overlaps:
            t_res = tug_overlaps[0]
            v_id = t_res["vessel_id"] if isinstance(t_res, dict) else t_res[1]
            raise BusinessValidationError(
                f"Tug '{tug_id}' is already reserved between {start_time} and {end_time} by vessel '{v_id}'."
            )
            
    # 3. Perform Insert
    if is_sqlite:
        insert_query = """
        INSERT INTO channel_reservations (channel_id, vessel_id, tug_id, start_time, end_time, status)
        VALUES (?, ?, ?, ?, ?, 'CONFIRMED');
        """
        cursor.execute(insert_query, (channel_id, vessel_id, tug_id, start_time, end_time))
    else:
        insert_query = """
        INSERT INTO channel_reservations (channel_id, vessel_id, tug_id, start_time, end_time, status)
        VALUES (%s, %s, %s, %s, %s, 'CONFIRMED');
        """
        cursor.execute(insert_query, (channel_id, vessel_id, tug_id, start_time, end_time))
    
    return {
        "status": "CONFIRMED",
        "channel_id": channel_id,
        "vessel_id": vessel_id,
        "tug_id": tug_id,
        "start_time": start_time,
        "end_time": end_time
    }


def get_all_reservations(conn, channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches confirmed channel reservations."""
    cursor = conn.cursor()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    
    if channel_id:
        query = "SELECT * FROM channel_reservations WHERE channel_id = ? AND status = 'CONFIRMED';" if is_sqlite else "SELECT * FROM channel_reservations WHERE channel_id = %s AND status = 'CONFIRMED';"
        cursor.execute(query, (channel_id,))
    else:
        query = "SELECT * FROM channel_reservations WHERE status = 'CONFIRMED';"
        cursor.execute(query)
    
    rows = cursor.fetchall()
    results = []
    for r in rows:
        if isinstance(r, dict):
            results.append(r)
        else:
            results.append(dict(r))
    return results
