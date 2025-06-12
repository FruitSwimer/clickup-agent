import os
import asyncio
import logging
from pydantic_ai.agent import AgentRunResult
from pydantic_core import to_json, to_jsonable_python
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.messages import ModelResponse, TextPart
from datetime import datetime
from dataclasses import dataclass
from dotenv import load_dotenv

from ..config.database import db_connection
from ..services.message_service import MessageService
from .instructions import INSTRUCTIONS
from . import MCPServerClickup, AgentTools, AppDependencies
from .mcp_connection import wait_for_mcp_server
load_dotenv()

logger = logging.getLogger(__name__)

class AxleAgent(Agent):
    def __init__(self, agent_id: str, model: str = 'openai:gpt-4.1', deps_type= AppDependencies, system_prompt: str = "You are an helpfull AI agent working for AXLE AI.", instructions: str = None, tools: list = None, mcp_servers: list = None):
        
        default_tools = [
            AgentTools.get_current_datetime,
            AgentTools.get_user_info,
        ]

        # Initialiser final_tools avec une copie des outils par défaut
        final_tools = list(default_tools)
        if tools is not None:
            for tool in tools:
                if tool not in final_tools:
                    final_tools.append(tool)

        super().__init__(
            model=model,
            deps_type=deps_type,
            system_prompt=system_prompt,
            tools=final_tools,
            instructions = instructions,
            mcp_servers=mcp_servers or [],
        )
        
        self.agent_id = agent_id
        self._message_service = None
    
    @property
    def message_service(self):
        if self._message_service is None:
            self._message_service = MessageService()
        return self._message_service
        

    async def run(self, user_input: str, user_id: str, deps: AppDependencies = None, message_history: list[dict] = None) -> AgentRunResult:
        async with super().run_mcp_servers():
            message_history = await self.message_service.get_raw_messages(
                session_id=user_id,
            )
            result = await super().run(user_input, deps=deps, message_history=message_history)
            await self.message_service.save_agent_run(
                session_id=user_id,
                agent_run_result=result,
                agent_id=self.agent_id,
            )
            return result

    async def get_agent_response(self, agent_run_result: AgentRunResult):
        """
        Ignore tools responses and return the last agent response
        """
        messages = agent_run_result.all_messages()
        
        # Iterate through messages in reverse to find the last text response
        for message in reversed(messages):
            if isinstance(message, ModelResponse):
                # Check each part of the response
                for part in message.parts:
                    if isinstance(part, TextPart):
                        return part.content
        
        # If no text response found, return None or empty string
        return None


# ClickupAgent will be created after database connection
ClickupAgent = None

def create_clickup_agent():
    global ClickupAgent
    ClickupAgent = AxleAgent(
        agent_id="ClickupAgent",
        system_prompt=(INSTRUCTIONS),
        mcp_servers=[MCPServerClickup]
    )
    return ClickupAgent