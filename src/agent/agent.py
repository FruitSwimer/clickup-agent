import os
import asyncio
import logging
from typing import Optional
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

# Debug mode - set to False to disable detailed message logging
DEBUG_MESSAGES = os.environ.get('DEBUG_MESSAGES', 'true').lower() == 'true'

class AxleAgent(Agent):
    def __init__(self, agent_id: str, model: str = 'openai:gpt-4.1', deps_type= AppDependencies, system_prompt: str = "You are an helpfull AI agent working for AXLE AI.", instructions: str = None, tools: list = None, mcp_servers: list = None, message_history_limit: Optional[int] = None):
        
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
        self.message_history_limit = message_history_limit
    
    @property
    def message_service(self):
        if self._message_service is None:
            self._message_service = MessageService()
        return self._message_service
        

    async def run(self, user_input: str, user_id: str, deps: AppDependencies = None, message_history: list[dict] = None) -> AgentRunResult:
        """
        Run the agent with proper MCP server lifecycle management.
        Based on PydanticAI best practices.
        """
        result = None
        try:
            print("  🔌 Starting MCP servers...")
            logger.debug("DEBUG: About to start MCP servers context manager")
            
            # Proper usage of run_mcp_servers context manager
            async with super().run_mcp_servers():
                print("  ✅ MCP servers ready")
                logger.debug("DEBUG: MCP servers started successfully")
                
                logger.debug("DEBUG: About to get message history")
                message_history = await self.message_service.get_raw_messages(
                    session_id=user_id,
                    limit=self.message_history_limit
                )
                logger.debug(f"DEBUG: Retrieved {len(message_history) if message_history else 0} historical messages")
                
                # Debug logging for message history
                if DEBUG_MESSAGES and message_history:
                    logger.info(f"🔍 Message History (limit={self.message_history_limit}):")
                    logger.info(f"   Total messages retrieved: {len(message_history)}")
                    for i, msg in enumerate(message_history):
                        msg_type = type(msg).__name__
                        content_preview = ""
                        if hasattr(msg, 'parts') and msg.parts:
                            content = str(msg.parts[0].content if hasattr(msg.parts[0], 'content') else msg.parts[0])
                            content_preview = content[:100] + "..." if len(content) > 100 else content
                        logger.info(f"   [{i+1}] {msg_type}: {content_preview}")
                    logger.info(f"   ➡️  Sending these {len(message_history)} messages to the AI model")
                
                print("  🧠 Processing with AI...")
                logger.debug("DEBUG: About to call super().run() with AI processing")
                
                # Log the user input
                if DEBUG_MESSAGES:
                    logger.info(f"📝 User Input: {user_input[:200]}..." if len(user_input) > 200 else f"📝 User Input: {user_input}")
                
                result = await super().run(user_input, deps=deps, message_history=message_history)
                logger.debug("DEBUG: AI processing completed, result obtained")
                
                # Log the AI response
                if DEBUG_MESSAGES:
                    response_text = await self.get_agent_response(result)
                    if response_text:
                        logger.info(f"🤖 AI Response: {response_text[:200]}..." if len(response_text) > 200 else f"🤖 AI Response: {response_text}")
                
                print("  💾 Saving to database...")
                logger.debug("DEBUG: About to save agent run to database")
                
                # Log before saving
                if DEBUG_MESSAGES:
                    all_messages = result.all_messages()
                    logger.info(f"💾 Saving conversation to database:")
                    logger.info(f"   Session ID: {user_id}")
                    logger.info(f"   Total messages in result: {len(all_messages)}")
                    logger.info(f"   New messages to save: {len(all_messages) - (len(message_history) if message_history else 0)}")
                
                await self.message_service.save_agent_run(
                    session_id=user_id,
                    agent_run_result=result,
                    agent_id=self.agent_id,
                )
                logger.debug("DEBUG: Agent run saved to database successfully")
                
                # Verify save
                if DEBUG_MESSAGES:
                    # Check if messages were saved
                    saved_messages = await self.message_service.get_raw_messages(user_id)
                    logger.info(f"✅ Verification - Total messages now in database: {len(saved_messages) if saved_messages else 0}")
                
                print("  🔌 Closing MCP servers...")
                logger.debug("DEBUG: About to exit MCP servers context manager")
                # Context manager will exit here automatically
            
            # This line executes after the context manager closes
            logger.debug("DEBUG: MCP servers context manager exited successfully")
            return result
                
        except Exception as e:
            logger.error(f"❌ Agent run failed: {e}")
            logger.debug("DEBUG: Exception caught in agent.run()")
            raise

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
    try:
        # Get message history limit from database settings
        message_limit = db_connection.settings.message_history_limit
        
        ClickupAgent = AxleAgent(
            agent_id="ClickupAgent",
            system_prompt=(INSTRUCTIONS),
            mcp_servers=[MCPServerClickup],
            message_history_limit=message_limit
        )
        print(f"  ✅ Agent created with message history limit: {message_limit}")
        return ClickupAgent
    except Exception as e:
        logger.error(f"❌ Failed to create agent: {e}")
        raise