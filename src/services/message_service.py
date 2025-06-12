from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import logging
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

logger = logging.getLogger(__name__)

from ..models.messages import AgentSession
from ..repositories.messages import ModelMessageRepository, AgentSessionRepository
from ..utils.message_transformer import MessageTransformer
from ..config.database import db_connection


class MessageService:
    def __init__(self):
        self.message_repo = ModelMessageRepository()
        self.session_repo = AgentSessionRepository()
        self.transformer = MessageTransformer()
    
    async def save_agent_run(
        self, 
        session_id: str,
        agent_run_result: AgentRunResult,
        agent_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Save or append agent run results to a session.
        
        If the session doesn't exist, it creates it. If it exists, it appends the new messages.
        """
        logger.info(f"Saving agent run for session_id: {session_id}, agent_id: {agent_id}")
        # Deserialize messages
        raw_messages_json = agent_run_result.all_messages_json()
        if isinstance(raw_messages_json, bytes):
            new_messages = ModelMessagesTypeAdapter.validate_json(raw_messages_json)
        elif isinstance(raw_messages_json, str):
            new_messages = ModelMessagesTypeAdapter.validate_json(raw_messages_json.encode())
        else:
            new_messages = raw_messages_json
        
        # Check if session exists
        existing_session = await self.session_repo.find_by_session_id(session_id)
        
        if existing_session:
            logger.info(f"Updating existing session: {session_id}")
            # Get existing messages count to detect new ones
            existing_raw_messages = await self.message_repo.get_messages_by_session_id(session_id)
            existing_count = len(existing_raw_messages) if existing_raw_messages else 0
            
            # Session exists - update with full conversation (pydantic-ai returns all messages)
            await self.message_repo.append_messages_to_session(session_id, new_messages)
            
            # Only process truly new messages for token counting
            truly_new_messages = new_messages[existing_count:] if len(new_messages) > existing_count else []
            
            if truly_new_messages:
                # Transform only new messages for display
                new_simple_messages = self.transformer.transform_messages(truly_new_messages)
                all_simple_messages = (existing_session.messages or []) + new_simple_messages
                
                # Extract model info from new messages
                model_name = self.transformer.extract_model_info(truly_new_messages) or existing_session.model
                
                # Aggregate token usage
                new_token_usage = self.transformer.aggregate_token_usage(truly_new_messages)
                if new_token_usage and existing_session.token_usage:
                    # Add to existing usage
                    total_usage = existing_session.token_usage.dict()
                    total_usage["requests"] += new_token_usage.requests
                    total_usage["request_tokens"] += new_token_usage.request_tokens
                    total_usage["response_tokens"] += new_token_usage.response_tokens
                    total_usage["total_tokens"] += new_token_usage.total_tokens
                    
                    if new_token_usage.details and existing_session.token_usage.details:
                        details = total_usage.get("details", {})
                        new_details = new_token_usage.details.dict()
                        for key in details:
                            if key in new_details and new_details[key] is not None:
                                details[key] = (details.get(key, 0) or 0) + new_details[key]
                    
                    final_token_usage = total_usage
                elif new_token_usage:
                    final_token_usage = new_token_usage.dict()
                else:
                    final_token_usage = existing_session.token_usage.dict() if existing_session.token_usage else None
                
                # Update session
                await self.session_repo.update_session(
                    session_id=session_id,
                    update_data={
                        "messages": [msg.dict() for msg in all_simple_messages],
                        "model": model_name,
                        "token_usage": final_token_usage
                    }
                )
        else:
            logger.info(f"Creating new session: {session_id}")
            # New session - create it
            await self.message_repo.save_messages_for_session(session_id, new_messages)
            
            simple_messages = self.transformer.transform_messages(new_messages)
            model_name = self.transformer.extract_model_info(new_messages)
            token_usage = self.transformer.aggregate_token_usage(new_messages)
            
            session = AgentSession(
                session_id=session_id,
                agent_id=agent_id,
                raw_messages_collection=db_connection.settings.raw_messages_collection,
                messages=simple_messages,
                model=model_name,
                token_usage=token_usage,
                metadata=metadata
            )
            
            await self.session_repo.create_session(session)
    
    
    async def get_session(self, session_id: str) -> Optional[AgentSession]:
        return await self.session_repo.find_by_session_id(session_id)
    
    async def get_raw_messages(self, session_id: str) -> Optional[List[ModelMessage]]:
        return await self.message_repo.get_messages_by_session_id(session_id)
    
    async def get_sessions_by_agent(
        self, 
        agent_id: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[AgentSession]:
        return await self.session_repo.find_by_agent_id(agent_id, skip, limit)
    
    async def get_recent_sessions(self, limit: int = 100) -> List[AgentSession]:
        return await self.session_repo.find_recent_sessions(limit)