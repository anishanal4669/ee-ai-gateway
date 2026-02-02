from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ChatMessage(BaseModel):
    """Represents a message in a chat conversation"""
    role: str  # e.g., "user", "assistant", "system"
    content: str  # The actual message content

class ChatCompletionRequest(BaseModel):
    """Request model for chat completion"""
    messages: List[ChatMessage]
    model: str  # e.g., "gpt-4"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 500
    top_p: Optional[float] = 0.9
    n: Optional[int] = 1  # Number of completions to generate
    stream: Optional[bool] = False  # Whether to stream responses
    stop: Optional[List[str]] = None  # Stop sequences

    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {"role": "user", "content": "Hello, how are you?"},
                    {"role": "assistant", "content": "I'm good, thank you! How can I assist you today?"}
                ],
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 500,
                "top_p": 0.9,
                "n": 1,
                "stream": False,
                "stop": ["\n"]
            }
        }

class ChatCompletionResponse(BaseModel):
    """Response model for chat completion"""
    id: str  # Unique identifier for the completion
    object: str  # e.g., "chat.completion"
    created: int  # Timestamp of creation
    model: str  # Model used for completion
    choices: List[Dict[str, Any]]  # List of generated choices
    usage: Optional[Dict[str, int]] = None  # Token usage statistics

    class Config:
        json_schema_extra = {
            "example": {
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "created": 1677652288,
                "model": "gpt-4",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "I'm good, thank you! How can I assist you today?"
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 15,
                    "total_tokens": 25
                }
            }
        }

class ChatCompletionError(BaseModel):
    """Error model for chat completion"""
    message: str  # Error message
    type: Optional[str] = None  # Type of error
    param: Optional[str] = None  # Parameter related to error
    code: Optional[str] = None  # Error code

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Invalid request",
                "type": "invalid_request_error",
                "param": "model",
                "code": "model_not_found"
            }
        }

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str  # e.g., "healthy"
    redis_status: str  # Redis connection status
    version: str  # Application version
    uptime_seconds: float  # Uptime in seconds
    details: Optional[Dict[str, Any]] = None  # Additional health details

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "redis_status": "connected",
                "version": "1.0.0",
                "uptime_seconds": 123456.78,
                "details": {
                    "database": "connected",
                    "cache": "operational"
                }
            }
        }