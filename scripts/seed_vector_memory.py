"""
Synthetic AIS & Hydrodynamic Memory Seeding Script.
Generates historical maritime maneuver records, computes 1024-dim Titan embeddings, and seeds hydrodynamic_memory.
"""

import os
import sys
import json
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db.connection import get_db_connection, execute_transaction_with_retry
from backend.db.repository import initialize_schema
from backend.db.vector_memory import generate_titan_embedding, insert_hydrodynamic_memory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_vector")

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "db", "schema.sql")

SAMPLE_HISTORICAL_DATA = [
    {
        "vessel_class": "Capesize Bulk Carrier",
        "weather_summary": "High crosswinds 35 knots, southward drift current 2.5 knots, low tide clearance",
        "wind_speed_knots": 35.0,
        "current_speed_knots": 2.5,
        "maneuver_telemetry": {"rudder_angle": 15, "engine_rpm": 65, "tug_escorts_used": 2, "under_keel_clearance_m": 1.8},
        "outcome": "SUCCESS"
    },
    {
        "vessel_class": "Panamax Container Ship",
        "weather_summary": "Severe storm squall 45 knots, strong flood tide current 4.0 knots, restricted visibility",
        "wind_speed_knots": 45.0,
        "current_speed_knots": 4.0,
        "maneuver_telemetry": {"rudder_angle": 25, "engine_rpm": 85, "tug_escorts_used": 3, "under_keel_clearance_m": 1.2},
        "outcome": "NEAR_MISS"
    },
    {
        "vessel_class": "Aframax Oil Tanker",
        "weather_summary": "Moderate breeze 18 knots, slack tide current 0.8 knots, calm water",
        "wind_speed_knots": 18.0,
        "current_speed_knots": 0.8,
        "maneuver_telemetry": {"rudder_angle": 5, "engine_rpm": 45, "tug_escorts_used": 1, "under_keel_clearance_m": 3.5},
        "outcome": "SUCCESS"
    },
    {
        "vessel_class": "Feeder Container Ship",
        "weather_summary": "Gale force gusts 40 knots, heavy river discharge 3.2 knots",
        "wind_speed_knots": 40.0,
        "current_speed_knots": 3.2,
        "maneuver_telemetry": {"rudder_angle": 20, "engine_rpm": 75, "tug_escorts_used": 2, "under_keel_clearance_m": 2.1},
        "outcome": "DELAYED"
    }
]


def seed_vector_database(db_url: str = None):
    conn = get_db_connection(db_url)
    initialize_schema(conn, SCHEMA_PATH)
    conn.commit()
    conn.close()

    def tx(conn):
        count = 0
        for item in SAMPLE_HISTORICAL_DATA:
            vec = generate_titan_embedding(item["weather_summary"], dimensions=1024)
            insert_hydrodynamic_memory(
                conn,
                vessel_class=item["vessel_class"],
                weather_summary=item["weather_summary"],
                wind_speed_knots=item["wind_speed_knots"],
                current_speed_knots=item["current_speed_knots"],
                drift_vector=vec,
                maneuver_telemetry=item["maneuver_telemetry"],
                outcome=item["outcome"]
            )
            count += 1
        return count

    inserted = execute_transaction_with_retry(lambda: get_db_connection(db_url), tx)
    logger.info(f"Successfully seeded {inserted} historical vector records.")
    return inserted


if __name__ == "__main__":
    seed_vector_database()
