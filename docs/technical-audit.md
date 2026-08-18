# Missouri Arbiter: Technical Audit & Architectural Specification (Revised)

**System:** Multi-Agent Maritime Orchestration Engine  
**Core Technologies:** CockroachDB (SERIALIZABLE + Vector Search + Managed MCP), AWS Bedrock (Claude 3.5 Sonnet, Titan Embeddings V2), Model Context Protocol (MCP), React + Leaflet.js  
**Author:** Principal Software Architect & Lead Engineer  

---

## 1. Executive Summary & Architectural Principles

This document establishes the revised technical audit, safety constraints, transaction isolation rules, and 16-phase implementation blueprint for **Missouri Arbiter**.

Missouri Arbiter is a high-concurrency multi-agent maritime orchestration system where autonomous vessel agents compete for shared maritime resources (channels, tugs), reason over dynamic weather conditions, detect cascading conflicts, execute bounded what-if simulations, and recover from failures autonomously.

### Core Architecture Principle:
> **CockroachDB is the authoritative source of truth** for operational state, reservations, resource allocations, historical experience, agent decisions, and evaluation logs.  
> **AI agents (Bedrock) propose actions.**  
> **The deterministic application layer validates them.**  
> **CockroachDB transactions decide whether state changes commit.**  
> LLM agents are strictly prohibited from bypassing database or business logic constraints.

### The Six Core Capabilities (Must be fully implemented in backend logic):
1. **Dynamic Weather / Channel Capacity Management**
2. **Cascading Conflict Detection**
3. **What-If Simulation Engine**
4. **Autonomous Recovery Pipeline**
5. **Explainable Decision Timeline & Ledger**
6. **Persistent Experiential Vector Memory**

---

## 2. CockroachDB Schema & Concurrency Strategy

### 2.1 Database Schema Design

```sql
-- 1. Physical Infrastructure (Operational State)
CREATE TABLE IF NOT EXISTS channels (
    channel_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    max_draft NUMERIC(4, 2) NOT NULL, -- in meters
    width_meters NUMERIC(6, 2) NOT NULL,
    requires_tug_escort BOOLEAN DEFAULT FALSE,
    coordinates JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS nav_restrictions (
    restriction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id VARCHAR(64) REFERENCES channels(channel_id),
    max_draft NUMERIC(4, 2),
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
    channel_id VARCHAR(64) REFERENCES channels(channel_id),
    vessel_id VARCHAR(64) REFERENCES vessels(vessel_id),
    tug_id VARCHAR(64) REFERENCES tug_fleet(tug_id),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(32) DEFAULT 'CONFIRMED', -- 'CONFIRMED', 'CANCELLED', 'COMPLETED'
    created_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

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
    created_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

-- Cosine Distance Vector Index (CockroachDB HNSW Vector Indexing)
CREATE INDEX IF NOT EXISTS hydrodynamic_vector_idx 
ON hydrodynamic_memory USING HNSW (drift_vector vector_cosine_ops);
```

### 2.2 Temporal Overlap & Race-Safety Proof

> **Correctness Property:** The final committed database state must NEVER contain two incompatible reservations for the same resource (`channel_id` or `tug_id`) within overlapping time intervals.

#### Why Application-Side Overlap Checking Alone is Vulnerable:
If two concurrent transactions $T_1$ and $T_2$ execute `SELECT ... WHERE start < new.end AND end > new.start` simultaneously without proper locking or serializable retry semantics, both might see 0 existing overlapping reservations and both perform an `INSERT`, creating a double-booking race condition.

#### Race-Safety Guarantee under CockroachDB `SERIALIZABLE`:
1. **Serializable Snapshot Isolation (SSI):** CockroachDB tracks transaction read-sets and write-sets.
2. **Explicit Lock Acquisition:** Every allocation transaction executes `SELECT reservation_id FROM channel_reservations WHERE channel_id = $1 AND status = 'CONFIRMED' AND start_time < $3 AND end_time > $2 FOR UPDATE;`.
3. **Concurrency Execution Flow:**
   - If $T_1$ and $T_2$ arrive concurrently:
   - CockroachDB detects the conflict in their read/write sets during row inspection or commit.
   - One transaction ($T_1$) succeeds and commits its `INSERT`.
   - The second transaction ($T_2$) receives a `SERIALIZATION_FAILURE` (`SQLSTATE 40001`).
   - The application transaction retry runner automatically retries $T_2$.
   - Upon retry, $T_2$'s fresh `SELECT ... FOR UPDATE` observes $T_1$'s committed reservation.
   - $T_2$'s business validation logic detects the overlap, rejects the request, and aborts without inserting.
4. **Acceptance Criteria for Phase 2:**
   - Two concurrent incompatible reservation requests are launched simultaneously.
   - Exactly one incompatible reservation ultimately commits.
   - The losing request retries, observes the committed reservation, and fails business validation (or is rejected).
   - Final DB state contains **exactly one** valid reservation.

---

## 3. Vector Embedding Strategy & CockroachDB Indexing

1. **Embedding Generator:** AWS Bedrock Amazon Titan Embeddings V2 configured for 1024-dimensional normalized vectors.
2. **Vector Indexing in CockroachDB:**
   - CockroachDB v24.1+ natively supports the `VECTOR(1024)` data type and HNSW vector index creation (`USING HNSW (drift_vector vector_cosine_ops)`).
   - Vector similarity search uses the `<=>` cosine distance operator:
     ```sql
     SELECT memory_id, weather_summary, maneuver_telemetry, outcome,
            1 - (drift_vector <=> $1::VECTOR(1024)) AS similarity_score
     FROM hydrodynamic_memory
     ORDER BY drift_vector <=> $1::VECTOR(1024) ASC
     LIMIT 5;
     ```

---

## 4. MCP Architecture: Managed MCP vs. Custom Application Tools

To maintain clean separation of concerns and avoid redundant custom code:

### Preferred Architecture:
```
AWS Bedrock Agent (Claude 3.5 Sonnet)
      ├──> CockroachDB Managed MCP Server ──> CockroachDB (Direct DB queries & state inspect)
      └──> Missouri Arbiter Custom Application Tools (Complex business logic)
```

### Tool Allocation Matrix:

| Tool Endpoint | Layer | Justification |
| :--- | :--- | :--- |
| `read_table_schema`, `execute_select_query` | **CockroachDB Managed MCP** | Direct, secure, standard SQL reads of operational state without custom wrappers. |
| `search_historical_maneuvers` | **CockroachDB Managed MCP** | Vector KNN queries against `hydrodynamic_memory`. |
| `simulate_plan` | **Custom Application Tool** | Executes in-memory state branching, bounded Depth 2-3 cascading graph search, and risk scoring. |
| `run_safety_verification` | **Custom Application Tool** | Runs deterministic non-LLM physics/tide/UKC rule engine checks. |
| `trigger_autonomous_recovery` | **Custom Application Tool** | Executes multi-step recovery flow when a resource bottleneck or failure is detected. |
| `reserve_channel_and_tug` | **Custom Application Tool** | Wraps CockroachDB `SERIALIZABLE` transaction execution with Python retry runner. |

---

## 5. Autonomous Recovery Pipeline

When a channel closure, storm event, or tug failure is detected, the system triggers the **Autonomous Recovery Pipeline**:

```
[Failure / Restriction Event Detected]
                 │
                 ▼
[1. Identify Affected Vessels & Resources]
                 │
                 ▼
[2. Invalidate / Reassess Active Plans]
                 │
                 ▼
[3. Generate Alternative Rerouting Candidates]
                 │
                 ▼
[4. Run What-If Simulation Engine (Depth 2-3)]
                 │
                 ▼
[5. Perform Cascading Conflict Analysis]
                 │
                 ▼
[6. Execute Safety Verifier (UKC / Tide Checks)]
                 │
                 ▼
[7. Harbor Master Arbitration]
                 │
                 ├───> Valid Plan Found ───> [8. Transactional Commit in CockroachDB]
                 │                                        │
                 │                                        ▼
                 │                          [9. Update Operational State & Log to Decision Ledger]
                 │
                 └───> No Valid Plan ──────> [Escalate to Human Harbor Master Review]
```

---

## 6. Deterministic Maritime Traffic Simulator

The Phase 4 simulator is named **Deterministic Maritime Traffic Simulator**.

It maintains deterministic calculations (without stochastic noise) modeling:
- **Position & Trajectory:** Dynamic latitude/longitude interpolation along channel corridors.
- **Speed & Heading:** Knots and compass heading adjustments based on channel geometry.
- **ETA & Transit Duration:** Computed based on distance, draft constraints, and speed limits.
- **Channel Movement:** Waypoint-based progress tracking.
- **Environmental Effects:** Current drift and wind retardation factors applied to speed.
- **Delays & Bottlenecks:** Waiting patterns when resources are locked.
- **Resource Availability:** Real-time status of tugs (`AVAILABLE` vs `RESERVED`).
- **Injected Failure Events:** Simulated channel closures, draft restrictions, and tug maintenance.

---

## 7. Dependency Order & Phase Matrix (Phases 0 - 15)

Every phase requires: **Implementation + Automated Tests + Documented Acceptance Criteria + Successful Test Output** before proceeding.

| Phase | Phase Title | Core Focus | Automated Verification Test |
| :---: | :--- | :--- | :--- |
| **0** | **Technical Audit** | Architectural blueprint & specification approval | `docs/technical-audit.md` & `implementation_plan.md` |
| **1** | **CockroachDB Schema & Transaction Layer** | Tables, DDL, `psycopg3` pool, retry runner | DB connection & table migration test script |
| **2** | **Two-Vessel Concurrent Reservation Proof** | Overlapping temporal reservation race test | `pytest tests/test_concurrency.py` (Exactly 1 commit, 1 retry & rejected) |
| **3** | **Historical Experience + Vector Memory** | Titan V2 1024-dim embeddings & HNSW index | KNN vector retrieval accuracy test |
| **4** | **Deterministic Maritime Simulator** | Telemetry engine for 5-10 ships & resources | Telemetry loop & position update assertion test |
| **5** | **Operational Tools + MCP Integration** | CockroachDB Managed MCP + Custom App Tools | Tool invocation & schema validation unit tests |
| **6** | **Three-Agent Bedrock Orchestration** | Pilot, Harbor Master, Safety Verifier agents | End-to-end multi-agent dialogue test |
| **7** | **Dynamic Weather / Capacity** | Weather updates & dynamic draft/tide limits | Dynamic restriction activation test |
| **8** | **Cascading Conflict Detection** | Multi-resource bottleneck graph analysis | 2-level cascading conflict detection test |
| **9** | **What-If Simulation** | In-memory state branching & risk scoring | Branch simulation & risk evaluation test |
| **10** | **Safety Verification** | Deterministic non-LLM UKC & tide rule engine | Under-keel clearance violation rejection test |
| **11** | **Autonomous Recovery** | Multi-step recovery workflow on failure | Storm event recovery pipeline assertion test |
| **12** | **Evaluation & Explainable Decision Ledger** | Ledger event logger & metrics persistence | Audit ledger event stream test |
| **13** | **Multi-Region / Failure Testing** | Database node failover & retry resilience | Simulated connection drop & retry test |
| **14** | **React + Leaflet Dashboard** | 2D ECDIS radar map & Decision Ledger UI | Frontend build & WebSocket connection test |
| **15** | **End-to-End Demo & Final Polish** | Full scenario execution & documentation | Full system integration test suite |

---

## 8. Status & Next Steps

This revised technical audit incorporates all 10 architectural corrections. Upon user confirmation of the revised `implementation_plan.md`, development will proceed strictly phase-by-phase starting with Phase 1.
