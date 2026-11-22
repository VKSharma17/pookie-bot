"""
PookieBot Core Architecture Package
===================================
Modular, plug-and-play components for the PookieBot Physical AI companion:
- HAL (Hardware Abstraction Layer for 100% Sim-to-Real parity)
- Face Bridge (WebSocket communication to animated HTML5 face)
- Vision Pipeline (MuJoCo offscreen rendering & camera stream)
- Agent Brain (Embodied Multimodal Physical AI with tool calling)
"""

from .hal import BaseRobotBridge, SimRobotBridge, RealRobotBridge, get_robot_bridge
from .face_bridge import FaceBridgeServer
from .vision import BaseVision, SimVision, RealVision, get_vision
from .agent_brain import PookieBrain

__all__ = [
    "BaseRobotBridge",
    "SimRobotBridge",
    "RealRobotBridge",
    "get_robot_bridge",
    "FaceBridgeServer",
    "BaseVision",
    "SimVision",
    "RealVision",
    "get_vision",
    "PookieBrain"
]
