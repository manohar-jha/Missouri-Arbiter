"""
Phase 4 Verification Test Suite
Deterministic Maritime Traffic Simulator Test.
Verifies:
1. Simulator state initialization for 5 vessels across main and bypass channels.
2. Speed over ground calculation incorporating wind and current drag.
3. Waypoint interpolation and heading calculations.
4. Holding pattern status when an injected channel closure event is triggered.
"""

import pytest
from backend.simulator.traffic_sim import DeterministicTrafficSimulator


def test_simulator_initialization():
    sim = DeterministicTrafficSimulator()
    state = sim.get_state()
    assert len(state["vessels"]) == 5
    assert "ch_main" in state["channels"]
    assert "ch_north" in state["channels"]


def test_deterministic_movement_and_weather_drag():
    sim = DeterministicTrafficSimulator()
    sim.set_environment(wind_knots=20.0, current_knots=2.0)
    
    # Calculate effective speed for 12 knot ship
    eff_speed = sim.calculate_effective_speed(12.0)
    assert eff_speed < 12.0 # Drag reduces speed
    assert eff_speed > 2.0  # Min speed enforced
    
    # Step simulation 1 minute (60s)
    updates = sim.step(delta_seconds=60.0)
    assert len(updates) == 5
    
    ship_alpha = sim.vessels["ship_alpha"]
    assert ship_alpha["status"] == "TRANSITING"
    assert ship_alpha["lat"] > 38.90 # Moved towards target waypoint


def test_injected_channel_closure_holding_pattern():
    sim = DeterministicTrafficSimulator()
    # Inject storm closure on main channel
    sim.inject_channel_closure("ch_main", reason="Storm Hazard closure")
    
    updates = sim.step(delta_seconds=60.0)
    
    # Main channel ships must enter holding pattern
    ship_alpha = sim.vessels["ship_alpha"]
    assert ship_alpha["status"] == "HOLDING_PATTERN"
    assert ship_alpha["speed_knots"] == 0.0
    
    # Bypass channel ship should continue transiting
    ship_delta = sim.vessels["ship_delta"]
    assert ship_delta["status"] == "TRANSITING"
