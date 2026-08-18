"""
Phase 1 Verification Test Suite
Tests schema initialization, connection management, repository operations, and transaction retry runners.
"""

import os
import pytest
from backend.db.connection import get_db_connection, execute_transaction_with_retry, BusinessValidationError
from backend.db.repository import initialize_schema, upsert_channel, upsert_tug, upsert_vessel, reserve_channel_and_tug, get_all_reservations

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "db", "schema.sql")
TEST_DB_URL = "sqlite3:///:memory:"


@pytest.fixture(autouse=True)
def setup_test_db():
    conn = get_db_connection(TEST_DB_URL)
    initialize_schema(conn, SCHEMA_PATH)
    yield conn
    conn.close()


def test_schema_and_upserts():
    """Verifies that schema creates tables and upsert statements function cleanly."""
    def tx_ops(conn):
        c_id = upsert_channel(
            conn, 
            channel_id="ch_main_1", 
            name="Missouri Main Channel", 
            max_draft=12.5, 
            width_meters=150.0, 
            requires_tug_escort=True, 
            coordinates=[[38.9, -92.3], [38.95, -92.25]]
        )
        assert c_id == "ch_main_1"
        
        t_id = upsert_tug(
            conn,
            tug_id="tug_alpha",
            name="Titan Escort Alpha",
            bollard_pull_tons=80.0,
            status="AVAILABLE",
            lat=38.9,
            lon=-92.3
        )
        assert t_id == "tug_alpha"
        
        v_id = upsert_vessel(
            conn,
            vessel_id="vessel_titan_1",
            name="MV Titan Trader",
            length_meters=220.0,
            draft_meters=11.2,
            speed_knots=10.5,
            heading=45.0,
            lat=38.88,
            lon=-92.35,
            status="UNDERWAY"
        )
        assert v_id == "vessel_titan_1"
        return True

    res = execute_transaction_with_retry(lambda: get_db_connection(TEST_DB_URL), tx_ops)
    assert res is True


def test_concurrency_safe_reservation():
    """Verifies single reservation succeeds and overlapping reservation raises BusinessValidationError."""
    def setup_data(conn):
        upsert_channel(conn, "ch_1", "Channel 1", 14.0, 200.0, False, [])
        upsert_vessel(conn, "v_1", "Vessel 1", 180.0, 10.0)
        upsert_vessel(conn, "v_2", "Vessel 2", 200.0, 11.0)

    execute_transaction_with_retry(lambda: get_db_connection(TEST_DB_URL), setup_data)
    
    # 1. Make first valid reservation
    res1 = execute_transaction_with_retry(
        lambda: get_db_connection(TEST_DB_URL),
        lambda c: reserve_channel_and_tug(c, "ch_1", "v_1", "2026-08-18T12:00:00Z", "2026-08-18T14:00:00Z")
    )
    assert res1["status"] == "CONFIRMED"

    # 2. Attempt overlapping reservation with v_2 (Should raise BusinessValidationError)
    with pytest.raises(BusinessValidationError) as excinfo:
        execute_transaction_with_retry(
            lambda: get_db_connection(TEST_DB_URL),
            lambda c: reserve_channel_and_tug(c, "ch_1", "v_2", "2026-08-18T13:00:00Z", "2026-08-18T15:00:00Z")
        )
    
    assert "Temporal reservation conflict" in str(excinfo.value)
    
    # 3. Verify exactly 1 reservation exists in DB
    conn = get_db_connection(TEST_DB_URL)
    all_res = get_all_reservations(conn, "ch_1")
    assert len(all_res) == 1
    assert all_res[0]["vessel_id"] == "v_1"
    conn.close()
