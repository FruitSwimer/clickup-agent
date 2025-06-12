"""
Tools for Pydantic AI agents.
"""
from datetime import datetime
from pydantic_ai import RunContext
from dataclasses import dataclass
from .dependencies import AppDependencies

class AgentTools:
    """Collection of tools for Pydantic AI agents."""
    
    @staticmethod
    async def get_current_datetime(ctx: RunContext[AppDependencies]) -> str:
        """
        Get the current date with time.
        
        Returns:
            str: Current datetime in format 'YYYY-MM-DD HH:MM:SS'
        """
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    @staticmethod
    async def get_user_info(ctx: RunContext[AppDependencies]) -> dict:
        """
        Get information about the current user.
        
        Returns:
            dict: User information including user_id and session_id
        """
        return {
            "user_id": ctx.deps.user_id,
            "session_id": ctx.deps.session_id
        }
