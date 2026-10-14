"""
A.GRID Real-time 1Hz In-Transit Telemetry Streaming & Boundary Monitor.
Processes live GPS, G-force impact, battery SoC, and temperature sensor data.
Broadcasting active alerts for dynamic rerouting and parametric dispute logging.
"""

import json
from typing import Dict, Any, List
from fastapi import WebSocket, WebSocketDisconnect

class TelemetryStreamManager:
    """Manages active WebSocket connections for in-flight/in-transit autonomous agents."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, mission_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[mission_id] = websocket

    def disconnect(self, mission_id: str):
        if mission_id in self.active_connections:
            del self.active_connections[mission_id]

    @staticmethod
    def process_telemetry_frame(frame: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates physical thresholds:
        - Excessive G-force impact (shock warning)
        - Cold-chain temperature violations
        - Critical battery degradation (< 15% SoC)
        """
        alerts: List[str] = []
        is_critical_breach = False

        g_force = frame.get("g_force", 1.0)
        max_allowed_g = frame.get("max_allowed_g", 2.5)
        if g_force > max_allowed_g:
            alerts.append(f"G_FORCE_BREACH: Detected {g_force:.2f}G > limit {max_allowed_g:.2f}G")
            is_critical_breach = True

        temp = frame.get("temperature_celsius")
        req_min_temp = frame.get("required_min_temp")
        req_max_temp = frame.get("required_max_temp")
        if temp is not None:
            if req_min_temp is not None and temp < req_min_temp:
                alerts.append(f"COLD_CHAIN_UNDERCOOL: {temp:.1f}C < min {req_min_temp:.1f}C")
                is_critical_breach = True
            if req_max_temp is not None and temp > req_max_temp:
                alerts.append(f"COLD_CHAIN_OVERHEAT: {temp:.1f}C > max {req_max_temp:.1f}C")
                is_critical_breach = True

        battery_soc = frame.get("battery_soc_percent", 100.0)
        if battery_soc < 15.0:
            alerts.append(f"LOW_BATTERY_WARNING: SoC dropped to {battery_soc:.1f}%")

        status = "CRITICAL_VIOLATION" if is_critical_breach else ("WARNING" if alerts else "NORMAL")

        return {
            "mission_id": frame.get("mission_id"),
            "status": status,
            "alerts": alerts,
            "telemetry_echo": {
                "lat": frame.get("lat"),
                "lon": frame.get("lon"),
                "altitude_m": frame.get("altitude_m"),
                "g_force": g_force,
                "temperature_celsius": temp,
                "battery_soc_percent": battery_soc
            }
        }


stream_manager = TelemetryStreamManager()
