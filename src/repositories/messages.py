from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import os
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from ..models.messages import AgentSession
from ..config.database import db_connection
from .base import BaseRepository
from pymongo.asynchronous.collection import AsyncCollection

logger = logging.getLogger(__name__)

# Debug mode - set to False to disable detailed message logging
DEBUG_MESSAGES = os.environ.get('DEBUG_MESSAGES', 'true').lower() == 'true'


class ModelMessageRepository:
    """Repository for handling ModelMessage storage directly in MongoDB"""
    
    def __init__(self):
        self.collection: AsyncCollection = db_connection.raw_messages_collection
    
    async def save_messages_for_session(self, session_id: str, messages: List[ModelMessage]) -> None:
        """Save messages for a session, replacing any existing messages"""
        try:
            # Serialize messages using ModelMessagesTypeAdapter
            messages_data = ModelMessagesTypeAdapter.dump_python(messages, mode='json')
            
            document = {
                "session_id": session_id,
                "messages": messages_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Saving {len(messages)} messages for session {session_id}")
            
            # Upsert - replace if exists, create if not
            result = await self.collection.replace_one(
                {"session_id": session_id},
                document,
                upsert=True
            )
            
            logger.info(f"Save result - matched: {result.matched_count}, modified: {result.modified_count}, upserted_id: {result.upserted_id}")
        except Exception as e:
            logger.error(f"Failed to save messages for session {session_id}: {e}", exc_info=True)
            raise
    
    async def get_messages_by_session_id(self, session_id: str, limit: Optional[int] = None) -> Optional[List[ModelMessage]]:
        """Get messages for a session with optional limit
        
        Args:
            session_id: The session ID
            limit: Maximum number of messages to return (0 or None for all messages)
                  If limit > 0, returns the most recent messages
        """
        document = await self.collection.find_one({"session_id": session_id})
        
        if document and "messages" in document:
            # Deserialize using ModelMessagesTypeAdapter
            all_messages = ModelMessagesTypeAdapter.validate_python(document["messages"])
            
            if DEBUG_MESSAGES:
                logger.info(f"📛 Retrieved {len(all_messages)} total messages from DB for session {session_id}")
            
            # Apply limit if specified and greater than 0
            if limit and limit > 0 and len(all_messages) > limit:
                # Return the last 'limit' messages
                limited_messages = all_messages[-limit:]
                if DEBUG_MESSAGES:
                    logger.info(f"🎯 Applied limit {limit}, returning last {len(limited_messages)} messages")
                return limited_messages
            
            if DEBUG_MESSAGES and limit:
                logger.info(f"📤 No limit applied (total messages {len(all_messages)} <= limit {limit})")
            
            return all_messages
        
        if DEBUG_MESSAGES:
            logger.info(f"⚠️ No messages found for session {session_id}")
        
        return None
    
    async def append_messages_to_session(self, session_id: str, all_messages_from_run: List[ModelMessage]) -> None:
        """Update session with messages from an agent run.
        
        Note: all_messages_from_run contains ALL messages from the conversation,
        not just new ones. We need to detect which ones are actually new.
        """
        # Get existing messages
        existing_messages = await self.get_messages_by_session_id(session_id)
        
        if existing_messages is None:
            # No existing session, save all messages
            await self.save_messages_for_session(session_id, all_messages_from_run)
        else:
            # Only keep messages that are not already in the session
            existing_count = len(existing_messages)
            
            if DEBUG_MESSAGES:
                logger.info(f"🔄 Appending messages: existing={existing_count}, received={len(all_messages_from_run)}")
            
            # The new messages are those after the existing ones
            if len(all_messages_from_run) > existing_count:
                # Save all messages (the full conversation)
                await self.save_messages_for_session(session_id, all_messages_from_run)
                if DEBUG_MESSAGES:
                    logger.info(f"✅ Updated session with {len(all_messages_from_run) - existing_count} new messages")
            else:
                if DEBUG_MESSAGES:
                    logger.info(f"⏸️ No new messages to append")
            # If no new messages, don't update
    
    async def delete_session_messages(self, session_id: str) -> bool:
        """Delete all messages for a session"""
        result = await self.collection.delete_one({"session_id": session_id})
        return result.deleted_count > 0


class AgentSessionRepository(BaseRepository[AgentSession]):
    def __init__(self):
        super().__init__(db_connection.agent_sessions_collection, AgentSession)
    
    async def create_session(self, session: AgentSession) -> str:
        try:
            session.updated_at = datetime.utcnow()
            logger.info(f"Creating session: {session.session_id}")
            result = await self.create(session)
            logger.info(f"Session created successfully: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to create session {session.session_id}: {e}", exc_info=True)
            raise
    
    async def update_session(self, session_id: str, update_data: Dict[str, Any]) -> bool:
        update_data["updated_at"] = datetime.utcnow()
        return await self.update_one(
            filter={"session_id": session_id},
            update=update_data
        )
    
    async def find_by_session_id(self, session_id: str) -> Optional[AgentSession]:
        return await self.find_one({"session_id": session_id})
    
    async def find_by_agent_id(self, agent_id: str, skip: int = 0, limit: int = 100) -> List[AgentSession]:
        return await self.find_many(
            filter={"agent_id": agent_id},
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )
    
    async def find_recent_sessions(self, limit: int = 100) -> List[AgentSession]:
        return await self.find_many(
            filter={},
            limit=limit,
            sort=[("updated_at", -1)]
        )