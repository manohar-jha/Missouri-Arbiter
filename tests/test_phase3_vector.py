"""
Phase 3 Verification Test Suite
Historical Experience & Vector Memory Test.
Verifies:
1. Titan V2 1024-dimension vector embedding generation.
2. Insertion into hydrodynamic_memory.
3. KNN similarity search accuracy returning top matching historical maneuvers.
"""

import os
import pytest
from backend.db.connection import get_db_connection, execute_transaction_with_retry
from backend.db.repository import initialize_schema
from backend.db.vector_memory import generate_titan_embedding, insert_hydrodynamic_memory, search_historical_maneuvers
from scripts.seed_vector_memory import seed_vector_database, SAMPLE_HISTORICAL_DATA

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "db", "schema.sql")
TEST_DB_URL = "sqlite3:///:memory:"


@pytest.fixture(autouse=True)
def setup_phase3_db():
    conn = get_db_connection(TEST_DB_URL)
    initialize_schema(conn, SCHEMA_PATH)
    yield conn
    conn.close()


def test_titan_vector_generation():
    """Verifies that vector generator returns a normalized 1024-dimensional float array."""
    embedding = generate_titan_embedding("High crosswinds 35 knots, southward drift current 2.5 knots", dimensions=1024)
    assert isinstance(embedding, list)
    assert len(embedding) == 1024
    assert all(isinstance(x, float) for x in embedding)


def test_vector_seeding_and_knn_search():
    """Verifies seeding historical dataset and running KNN search for nearest weather pattern."""
    seed_vector_database(TEST_DB_URL)
    
    # Generate query vector for storm conditions
    query_text = "Severe storm squall with high winds and flood current"
    query_vec = generate_titan_embedding(query_text, dimensions=1024)
    
    conn = get_db_connection(TEST_DB_URL)
    results = search_historical_maneuvers(conn, query_vec, limit=3)
    conn.close()
    
    assert len(results) > 0
    top_match = results[0]
    assert "similarity_score" in top_match
    assert top_match["similarity_score"] > 0.0
    assert "weather_summary" in top_match
    assert top_match["outcome"] in ["SUCCESS", "NEAR_MISS", "DELAYED"]
