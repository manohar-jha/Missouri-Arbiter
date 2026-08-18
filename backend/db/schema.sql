-- CockroachDB Schema for Missouri Arbiter
-- Multi-Agent Maritime Orchestration Platform

-- 1. Physical Infrastructure (Operational State)
CREATE TABLE IF NOT EXISTS channels (
    channel_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    max_draft NUMERIC(4, 2) NOT NULL, -- Maximum allowed vessel draft in meters
    width_meters NUMERIC(6, 2) NOT NULL,
    requires_tug_escort BOOLEAN DEFAULT FALSE,
    coordinates JSONB NOT NULL -- GeoJSON geometry / polyline coordinates array
);

CREATE TABLE IF NOT EXISTS nav_restrictions (
    restriction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id VARCHAR(64) REFERENCES channels(channel_id) ON DELETE CASCADE,
    max_draft NUMERIC(4, 2), -- Lowered max draft during low tide or storm
    is_closed BOOLEAN DEFAULT FALSE,
    reason VARCHAR(256),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS tug_fleet (
    tug_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    bollard_pull_tons NUMERIC(5, 1) NOT NULL,
    status VARCHAR(32) DEFAULT 'AVAILABLE', -- 'AVAILABLE', 'RESERVED', 'MAINTENANCE'
    current_lat NUMERIC(9, 6),
    current_lon NUMERIC(9, 6)
);

CREATE TABLE IF NOT EXISTS vessels (
    vessel_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    length_meters NUMERIC(6, 2) NOT NULL,
    draft_meters NUMERIC(4, 2) NOT NULL,
    speed_knots NUMERIC(4, 1) DEFAULT 0.0,
    heading_degrees NUMERIC(5, 1) DEFAULT 0.0,
    current_lat NUMERIC(9, 6) NOT NULL,
    current_lon NUMERIC(9, 6) NOT NULL,
    destination_id VARCHAR(64),
    status VARCHAR(32) DEFAULT 'UNDERWAY' -- 'UNDERWAY', 'ANCHORED', 'WAITING', 'TRANSITING'
);

-- 2. Operational Reservations (Collision Barrier)
CREATE TABLE IF NOT EXISTS channel_reservations (
    reservation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id VARCHAR(64) REFERENCES channels(channel_id) ON DELETE CASCADE,
    vessel_id VARCHAR(64) REFERENCES vessels(vessel_id) ON DELETE CASCADE,
    tug_id VARCHAR(64) REFERENCES tug_fleet(tug_id) ON DELETE SET NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(32) DEFAULT 'CONFIRMED', -- 'CONFIRMED', 'CANCELLED', 'COMPLETED'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast range queries on temporal overlaps
CREATE INDEX IF NOT EXISTS idx_reservations_channel_time 
ON channel_reservations (channel_id, status, start_time, end_time);

CREATE INDEX IF NOT EXISTS idx_reservations_tug_time 
ON channel_reservations (tug_id, status, start_time, end_time) 
WHERE tug_id IS NOT NULL;

-- 3. Experiential Memory (Vector Store)
CREATE TABLE IF NOT EXISTS hydrodynamic_memory (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vessel_class VARCHAR(64) NOT NULL,
    weather_summary TEXT NOT NULL,
    wind_speed_knots NUMERIC(4, 1) NOT NULL,
    current_speed_knots NUMERIC(4, 1) NOT NULL,
    drift_vector VECTOR(1024) NOT NULL,
    maneuver_telemetry JSONB NOT NULL,
    outcome VARCHAR(64) NOT NULL, -- 'SUCCESS', 'NEAR_MISS', 'DELAYED'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- HNSW Vector Index for Cosine Distance Similarity
CREATE INDEX IF NOT EXISTS hydrodynamic_vector_idx 
ON hydrodynamic_memory USING HNSW (drift_vector vector_cosine_ops);

-- 4. Decision Ledger & Audit Trail
CREATE TABLE IF NOT EXISTS decision_ledger (
    ledger_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(64) NOT NULL, -- 'CONFLICT_DETECTED', 'VECTOR_RETRIEVED', 'WHAT_IF_SIMULATED', 'SAFETY_PASSED', 'LOCK_ACQUIRED', 'RECOVERY_EXECUTED'
    vessel_id VARCHAR(64),
    channel_id VARCHAR(64),
    summary TEXT NOT NULL,
    details JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ledger_timestamp ON decision_ledger (timestamp DESC);
