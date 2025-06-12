from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict, Union, Literal
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    UserPromptPart,
    ToolReturnPart,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    Usage,
    ModelMessagesTypeAdapter
)
from pydantic_ai._utils import now_utc


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class SimpleMessage(BaseModel):
    """Application-specific simplified message format"""
    role: MessageRole
    content: str


class TokenUsageDetails(BaseModel):
    accepted_prediction_tokens: Optional[int] = None
    audio_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    rejected_prediction_tokens: Optional[int] = None
    cached_tokens: Optional[int] = None


class TokenUsage(BaseModel):
    requests: int
    request_tokens: int
    response_tokens: int
    total_tokens: int
    details: Optional[TokenUsageDetails] = None


class AgentSession(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the session")
    agent_id: str = Field(..., description="Identifier for the agent")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    raw_messages_collection: str = Field(..., description="Reference to raw messages collection")
    messages: Optional[List[SimpleMessage]] = Field(default=None, description="Simplified conversation messages")
    model: Optional[str] = Field(default=None, description="Model used in the session")
    token_usage: Optional[TokenUsage] = Field(default=None, description="Aggregated token usage for the session")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional session metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


