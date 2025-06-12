"""
App dependencies.
"""

from dataclasses import dataclass

@dataclass
class AppDependencies:
    """Dependencies for the agent."""
    user_id: int
    session_id: str | None = None