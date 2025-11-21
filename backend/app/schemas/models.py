from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal


class Query(BaseModel):
    """
    Query model for AI requests
    """
    text: str = Field(..., description="The query text")
    messages: List[dict] = Field(..., description="The conversation history")
    project_id: str = Field(..., description="The project ID to use for retrieval")


class Response(BaseModel):
    """
    Response model for AI responses
    """
    result: str = Field(..., description="The result text from the AI")
    

class BAWResponse(BaseModel):
    result: dict


class StreamResponse(BaseModel):
    """
    Response model for streaming AI responses
    """
    chunk: str = Field(..., description="A chunk of the response text")
    done: bool = Field(False, description="Whether this is the last chunk")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata about the response")


class Message(BaseModel):
    """
    Message model for chat history
    """
    role: str = Field(..., description="The role of the message sender (user or assistant)")
    content: str = Field(..., description="The message content")


class SummarizeRequest(BaseModel):
    """
    Request model for document summarization
    """
    summarization_type: Literal["detailed", "executive"] = Field(
        default="executive",
        description="Type of summarization: 'detailed' for comprehensive hierarchical analysis, 'executive' for fast high-level overview"
    )
    user_query: Optional[str] = Field(
        default=None,
        description="Optional user instructions for detailed summarization (e.g., focus areas, specific concerns). Only applies to 'detailed' type."
    )

# Made with Bob
