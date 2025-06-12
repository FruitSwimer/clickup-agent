from typing import List, Dict, Any, Optional, Union
from ..models.messages import (
    SimpleMessage, MessageRole, TokenUsage, TokenUsageDetails,
    ModelMessage, ModelRequest, ModelResponse,
    SystemPromptPart, UserPromptPart, ToolReturnPart, RetryPromptPart,
    TextPart, ToolCallPart
)


class MessageTransformer:
    @staticmethod
    def extract_simple_message(message_part: Union[SystemPromptPart, UserPromptPart, ToolReturnPart, RetryPromptPart, TextPart, ToolCallPart]) -> Optional[SimpleMessage]:
        if isinstance(message_part, UserPromptPart):
            content = message_part.content
            if isinstance(content, list):
                text_parts = [item for item in content if isinstance(item, str)]
                content = " ".join(text_parts) if text_parts else str(content)
            return SimpleMessage(role=MessageRole.USER, content=str(content))
        
        elif isinstance(message_part, SystemPromptPart):
            return SimpleMessage(role=MessageRole.SYSTEM, content=message_part.content)
        
        elif isinstance(message_part, TextPart):
            return SimpleMessage(role=MessageRole.ASSISTANT, content=message_part.content)
        
        elif isinstance(message_part, ToolReturnPart):
            content = message_part.content
            if not isinstance(content, str):
                content = str(content)
            return SimpleMessage(
                role=MessageRole.TOOL,
                content=f"[Tool: {message_part.tool_name}] {content}"
            )
        
        elif isinstance(message_part, ToolCallPart):
            args = message_part.args
            if isinstance(args, str):
                args_str = args
            else:
                args_str = str(args)
            return SimpleMessage(
                role=MessageRole.ASSISTANT,
                content=f"[Calling tool: {message_part.tool_name}] Args: {args_str}"
            )
        
        elif isinstance(message_part, RetryPromptPart):
            return SimpleMessage(
                role=MessageRole.SYSTEM,
                content=f"[Retry requested] {message_part.model_response()}"
            )
        
        return None
    
    @staticmethod
    def transform_messages(raw_messages: List[ModelMessage]) -> List[SimpleMessage]:
        simple_messages = []
        
        for message in raw_messages:
            if isinstance(message, ModelRequest):
                for part in message.parts:
                    simple_msg = MessageTransformer.extract_simple_message(part)
                    if simple_msg:
                        simple_messages.append(simple_msg)
            elif isinstance(message, ModelResponse):
                for part in message.parts:
                    simple_msg = MessageTransformer.extract_simple_message(part)
                    if simple_msg:
                        simple_messages.append(simple_msg)
        
        return simple_messages
    
    @staticmethod
    def extract_model_info(raw_messages: List[ModelMessage]) -> Optional[str]:
        for message in raw_messages:
            if isinstance(message, ModelResponse) and message.model_name:
                return message.model_name
        return None
    
    @staticmethod
    def aggregate_token_usage(raw_messages: List[ModelMessage]) -> Optional[TokenUsage]:
        total_usage = {
            "requests": 0,
            "request_tokens": 0,
            "response_tokens": 0,
            "total_tokens": 0
        }
        
        details_aggregated = {
            "accepted_prediction_tokens": 0,
            "audio_tokens": 0,
            "reasoning_tokens": 0,
            "rejected_prediction_tokens": 0,
            "cached_tokens": 0
        }
        
        has_usage = False
        
        for message in raw_messages:
            if isinstance(message, ModelResponse) and message.usage:
                has_usage = True
                usage = message.usage
                total_usage["requests"] += usage.requests
                total_usage["request_tokens"] += usage.request_tokens
                total_usage["response_tokens"] += usage.response_tokens
                total_usage["total_tokens"] += usage.total_tokens
                
                if usage.details:
                    details = usage.details
                    if hasattr(details, 'accepted_prediction_tokens') and details.accepted_prediction_tokens:
                        details_aggregated["accepted_prediction_tokens"] += details.accepted_prediction_tokens
                    if hasattr(details, 'audio_tokens') and details.audio_tokens:
                        details_aggregated["audio_tokens"] += details.audio_tokens
                    if hasattr(details, 'reasoning_tokens') and details.reasoning_tokens:
                        details_aggregated["reasoning_tokens"] += details.reasoning_tokens
                    if hasattr(details, 'rejected_prediction_tokens') and details.rejected_prediction_tokens:
                        details_aggregated["rejected_prediction_tokens"] += details.rejected_prediction_tokens
                    if hasattr(details, 'cached_tokens') and details.cached_tokens:
                        details_aggregated["cached_tokens"] += details.cached_tokens
        
        if not has_usage:
            return None
        
        token_usage = TokenUsage(
            **total_usage,
            details=TokenUsageDetails(**details_aggregated) if any(details_aggregated.values()) else None
        )
        
        return token_usage