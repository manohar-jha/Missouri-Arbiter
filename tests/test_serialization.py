"""
Unit and Regression Tests for JSON Serialization Helper (make_json_serializable)
Verifies Decimal, UUID, datetime/date/time, nested container, and database tool result serialization.
"""

import json
from decimal import Decimal
from uuid import UUID, uuid4
from datetime import datetime, date, time
from backend.agent.tools import (
    make_json_serializable,
    lookup_vessel,
    lookup_channel,
    select_available_tug,
    execute_tool_call
)

def test_decimal_serialization():
    data = {"draft": Decimal("11.5"), "length": Decimal("220.0")}
    sanitized = make_json_serializable(data)
    assert isinstance(sanitized["draft"], float)
    assert sanitized["draft"] == 11.5
    assert isinstance(sanitized["length"], float)
    assert sanitized["length"] == 220.0
    # Must be JSON serializable
    json_str = json.dumps(sanitized)
    assert '"draft": 11.5' in json_str

def test_uuid_serialization():
    u = uuid4()
    data = {"id": u, "nested": [{"item_id": u}]}
    sanitized = make_json_serializable(data)
    assert isinstance(sanitized["id"], str)
    assert sanitized["id"] == str(u)
    assert sanitized["nested"][0]["item_id"] == str(u)
    json_str = json.dumps(sanitized)
    assert str(u) in json_str

def test_datetime_serialization():
    now = datetime(2026, 8, 18, 12, 30, 0)
    today = date(2026, 8, 18)
    t = time(12, 30, 0)
    data = {"timestamp": now, "day": today, "clock": t}
    sanitized = make_json_serializable(data)
    assert sanitized["timestamp"] == "2026-08-18T12:30:00"
    assert sanitized["day"] == "2026-08-18"
    assert sanitized["clock"] == "12:30:00"
    json_str = json.dumps(sanitized)
    assert "2026-08-18T12:30:00" in json_str

def test_nested_complex_structures():
    u = uuid4()
    now = datetime(2026, 8, 18, 15, 0, 0)
    complex_data = {
        "status": "SUCCESS",
        "records": [
            {
                "id": u,
                "metrics": {
                    "draft": Decimal("12.25"),
                    "speed": Decimal("14.0"),
                    "updated_at": now
                },
                "tags": ("marine", "tug", Decimal("50.5"))
            }
        ]
    }
    sanitized = make_json_serializable(complex_data)
    json_output = json.dumps(sanitized)
    assert isinstance(json_output, str)
    parsed = json.loads(json_output)
    assert parsed["records"][0]["metrics"]["draft"] == 12.25
    assert parsed["records"][0]["id"] == str(u)

def test_tool_results_serialization():
    vessel_res = lookup_vessel("ship_alpha")
    json_vessel = json.dumps(vessel_res)
    assert isinstance(json_vessel, str)

    channel_res = lookup_channel("ch_main")
    json_channel = json.dumps(channel_res)
    assert isinstance(json_channel, str)

    tug_res = select_available_tug(50.0)
    json_tug = json.dumps(tug_res)
    assert isinstance(json_tug, str)

    tool_exec_res = execute_tool_call("lookup_vessel", '{"vessel_id": "ship_alpha"}')
    json_exec = json.dumps(tool_exec_res)
    assert isinstance(json_exec, str)
