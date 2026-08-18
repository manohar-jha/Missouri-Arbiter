"""
Phase 2 Verification Test Suite
Two-Vessel Concurrent Reservation Proof.
Verifies that when two concurrent threads attempt incompatible overlapping reservations:
1. Exactly one transaction commits.
2. The other request retries and fails business validation (or is rejected after observing the committed reservation).
3. The final database state contains EXACTLY ONE valid reservation.
"""

import os
import pytest
import concurrent.futures
import time
from backend.db.connection import get_db_connection, execute_transaction_with_retry, BusinessValidationError
from backend.db.repository import initialize_schema, upsert_channel, upsert_vessel, reserve_channel_and_tug, get_all_reservations

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "db", "schema.sql")
TEST_DB_URL = "sqlite3:///:memory:"


@pytest.fixture(autouse=True)
def setup_phase2_db():
    conn = get_db_connection(TEST_DB_URL)
    initialize_schema(conn, SCHEMA_PATH)
    # Seed initial test channel and vessels
    def seed(c):
        upsert_channel(c, "ch_concurrency_test", "Missouri Narrow Cut", 12.0, 100.0, True, [])
        upsert_vessel(c, "vessel_alpha", "MV Alpha Star", 190.0, 10.5)
        upsert_vessel(c, "vessel_beta", "MV Beta Voyager", 210.0, 11.0)
    execute_transaction_with_retry(lambda: get_db_connection(TEST_DB_URL), seed)
    yield conn
    conn.close()


def attempt_reservation(vessel_id: str, start_time: str, end_time: str):
    """Worker function executed by concurrent threads."""
    def tx(conn):
        time.sleep(0.005)
        return reserve_channel_and_tug(conn, "ch_concurrency_test", vessel_id, start_time, end_time)
    
    try:
        result = execute_transaction_with_retry(
            lambda: get_db_connection(TEST_DB_URL),
            tx,
            max_retries=5
        )
        return {"vessel_id": vessel_id, "success": True, "result": result, "error": None}
    except Exception as e:
        return {"vessel_id": vessel_id, "success": False, "result": None, "error": str(e)}


def test_two_vessel_concurrent_reservation_proof():
    """
    Core Phase 2 Acceptance Test:
    Launches vessel_alpha and vessel_beta simultaneously to request overlapping windows on ch_concurrency_test.
    Asserts exactly 1 success, 1 failure, and 1 final database record.
    """
    start_time = "2026-08-18T14:00:00Z"
    end_time = "2026-08-18T16:00:00Z"
    
    # Launch concurrent requests in parallel threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(attempt_reservation, "vessel_alpha", start_time, end_time)
        f2 = executor.submit(attempt_reservation, "vessel_beta", start_time, end_time)
        
        results = [f1.result(), f2.result()]

    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    # Verification Criterion 1: Exactly 1 transaction committed
    assert len(successes) == 1, f"Expected exactly 1 committed reservation, got {len(successes)}"
    
    # Verification Criterion 2: Exactly 1 transaction rejected with conflict/lock error
    assert len(failures) == 1, f"Expected exactly 1 rejected reservation, got {len(failures)}"
    err_msg = failures[0]["error"].lower()
    assert any(k in err_msg for k in ["conflict", "overlap", "locked", "serialization"]), f"Unexpected error message: {err_msg}"

    # Verification Criterion 3: Final database state contains EXACTLY ONE valid reservation
    conn = get_db_connection(TEST_DB_URL)
    reservations = get_all_reservations(conn, "ch_concurrency_test")
    assert len(reservations) == 1, f"Database contains {len(reservations)} reservations, expected exactly 1!"
    
    committed_vessel = reservations[0]["vessel_id"]
    assert committed_vessel in ["vessel_alpha", "vessel_beta"]
    conn.close()
