"""
Deterministic Maritime Traffic Simulator
Models vessel movement, speed, heading, ETA, environmental wind/drift effects, resource locks, and failure events.
"""

import math
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("traffic_sim")

DEFAULT_CHANNELS = {
    "ch_main": {
        "name": "Missouri Main Corridor",
        "waypoints": [(38.90, -92.35), (38.92, -92.30), (38.95, -92.25)],
        "max_draft": 13.0,
        "width_meters": 160.0
    },
    "ch_north": {
        "name": "Missouri North Bypass",
        "waypoints": [(38.90, -92.35), (38.94, -92.32), (38.95, -92.25)],
        "max_draft": 11.5,
        "width_meters": 120.0
    }
}

DEFAULT_VESSELS = [
    {"vessel_id": "ship_alpha", "name": "MV Alpha Carrier", "length": 220.0, "draft": 11.0, "speed": 12.0, "lat": 38.90, "lon": -92.35, "channel_id": "ch_main", "target_idx": 1},
    {"vessel_id": "ship_beta", "name": "MV Beta Tanker", "length": 240.0, "draft": 12.2, "speed": 10.0, "lat": 38.90, "lon": -92.35, "channel_id": "ch_main", "target_idx": 1},
    {"vessel_id": "ship_gamma", "name": "MV Gamma Feeder", "length": 160.0, "draft": 8.5, "speed": 14.0, "lat": 38.92, "lon": -92.30, "channel_id": "ch_main", "target_idx": 2},
    {"vessel_id": "ship_delta", "name": "MV Delta Express", "length": 180.0, "draft": 9.8, "speed": 13.0, "lat": 38.90, "lon": -92.35, "channel_id": "ch_north", "target_idx": 1},
    {"vessel_id": "ship_epsilon", "name": "MV Epsilon Titan", "length": 260.0, "draft": 12.8, "speed": 9.5, "lat": 38.90, "lon": -92.35, "channel_id": "ch_main", "target_idx": 1}
]


class DeterministicTrafficSimulator:
    """
    Deterministic Simulator modeling maritime traffic progress, environmental drag, and injected closures.
    Calculations are strictly deterministic (no stochastic random noise) based on prototype physics assumptions:
    - Speed Over Ground (SOG) = Base Speed - (Wind Speed * 0.05) - (Head Current * 0.8)
    - Position interpolation along channel waypoints per time step (delta_t seconds).
    """
    def __init__(self):
        self.vessels: Dict[str, Dict[str, Any]] = {v["vessel_id"]: dict(v) for v in DEFAULT_VESSELS}
        self.channels: Dict[str, Dict[str, Any]] = dict(DEFAULT_CHANNELS)
        self.active_restrictions: Dict[str, Dict[str, Any]] = {}
        self.wind_speed_knots: float = 15.0
        self.current_speed_knots: float = 1.2

    def set_environment(self, wind_knots: float, current_knots: float):
        """Sets environmental weather parameters."""
        self.wind_speed_knots = wind_knots
        self.current_speed_knots = current_knots

    def inject_channel_closure(self, channel_id: str, reason: str = "Storm Hazard", max_draft_limit: Optional[float] = None):
        """Injects a channel restriction or full closure failure event."""
        self.active_restrictions[channel_id] = {
            "channel_id": channel_id,
            "reason": reason,
            "is_closed": max_draft_limit is None,
            "max_draft": max_draft_limit
        }
        logger.warning(f"Simulated dynamic failure injected on channel '{channel_id}': {reason}")

    def clear_restrictions(self, channel_id: Optional[str] = None):
        if channel_id:
            self.active_restrictions.pop(channel_id, None)
        else:
            self.active_restrictions.clear()

    def calculate_effective_speed(self, base_speed_knots: float) -> float:
        """Deterministic speed calculation incorporating environmental drag."""
        sog = base_speed_knots - (self.wind_speed_knots * 0.04) - (self.current_speed_knots * 0.6)
        return max(2.0, sog)

    def calculate_heading(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates compass heading angle (0-360 degrees) between two coordinates."""
        d_lat = lat2 - lat1
        d_lon = lon2 - lon1
        angle = math.degrees(math.atan2(d_lon, d_lat))
        return (angle + 360) % 360

    def step(self, delta_seconds: float = 60.0) -> List[Dict[str, Any]]:
        """
        Advances simulation by delta_seconds.
        Updates vessel coordinates, speed over ground, heading, and status.
        """
        updates = []
        for v_id, v in self.vessels.items():
            ch_id = v["channel_id"]
            waypoints = self.channels[ch_id]["waypoints"]
            target_idx = v["target_idx"]
            
            # Check for channel restriction/closure
            restr = self.active_restrictions.get(ch_id)
            if restr and (restr["is_closed"] or (restr["max_draft"] and v["draft"] > restr["max_draft"])):
                v["status"] = "HOLDING_PATTERN"
                v["speed_knots"] = 0.0
                updates.append(dict(v))
                continue
            
            v["status"] = "TRANSITING"
            target_lat, target_lon = waypoints[target_idx]
            current_lat, current_lon = v["lat"], v["lon"]
            
            heading = self.calculate_heading(current_lat, current_lon, target_lat, target_lon)
            v["heading_degrees"] = heading
            
            eff_speed = self.calculate_effective_speed(v["speed"])
            v["speed_knots"] = eff_speed
            
            # Distance step in degrees (approx 1 knot = 0.0003 degrees lat per minute)
            dist_step = (eff_speed * 0.0003) * (delta_seconds / 60.0)
            
            d_lat = target_lat - current_lat
            d_lon = target_lon - current_lon
            dist_to_target = math.sqrt(d_lat**2 + d_lon**2)
            
            if dist_to_target <= dist_step:
                # Reached waypoint
                v["lat"] = target_lat
                v["lon"] = target_lon
                if target_idx < len(waypoints) - 1:
                    v["target_idx"] += 1
                else:
                    v["status"] = "ARRIVED"
                    v["speed_knots"] = 0.0
            else:
                # Interpolate towards waypoint
                v["lat"] += (d_lat / dist_to_target) * dist_step
                v["lon"] += (d_lon / dist_to_target) * dist_step
                
            updates.append(dict(v))
            
        return updates

    def get_state(self) -> Dict[str, Any]:
        """Returns complete snapshot of active vessels, channels, and restrictions."""
        return {
            "vessels": list(self.vessels.values()),
            "channels": self.channels,
            "restrictions": self.active_restrictions,
            "environment": {
                "wind_speed_knots": self.wind_speed_knots,
                "current_speed_knots": self.current_speed_knots
            }
        }
