"""Device Agent — Desktop + Browser Automation Agent.

Inspired by Open-AutoGLM (VLM-based UI understanding).
"""

from app.device_agent.engine import DeviceAgent, DeviceAction, get_agent, close_agent

__all__ = [
    "DeviceAgent", "DeviceAction", "get_agent", "close_agent",
]
