from app.agents.agent_factory import RFPAgent
import logging
from typing import Dict, Any, Optional, AsyncGenerator, Tuple
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends

# Set up logging
logger = logging.getLogger(__name__)

# Global registry of AI agents
agents: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize AI agents on startup and clean up on shutdown.
    This ensures agents are created only once during application lifecycle.
    """
    try:
        logger.info("Initializing AI agents...")
        # Initialize RFP agent
        agents["rfp_agent"] = RFPAgent()
        # Future agents can be added here:
        # agents["summarization_agent"] = SummarizationAgent()
        # agents["classification_agent"] = ClassificationAgent()
        logger.info("AI agents initialized successfully!")
        yield
    except Exception as e:
        logger.error(f"Error initializing AI agents: {e}")
        raise
    finally:
        # Cleanup resources when the app shuts down
        logger.info("Cleaning up AI agents...")
        agents.clear()

class AIService:
    """
    Service class that provides access to various AI capabilities.
    This class acts as a facade for different AI agents and services.
    """
    
    @staticmethod
    async def process_query(query: str | None, messages: list | None, project_id: str) -> str:
        """
        Process a query using the RFP agent. Accepts either a single query or a conversation
        
        Args:
            query: The user's question
            messages: User's conversation
            project_id: The project ID to use for retrieval
            
        Returns:
            The agent's response
        """

        query_text: str = messages[-1]["content"] if messages else query or ""
        logger.info(f"Processing query: '{query_text}' for project: {project_id}")
        
        # Get the RFP agent from the global registry
        rfp_agent = agents.get("rfp_agent")
        if not rfp_agent:
            raise RuntimeError("RFP agent not initialized. Ensure the application lifespan is properly configured.")
        
        # Invoke the agent
        if messages:
            result = await rfp_agent.achat(messages, project_id)
        else:
            result = await rfp_agent.ainvoke(query, project_id)
        return result
    
    @staticmethod
    async def stream_query(messages: list, project_id: str) -> AsyncGenerator[Tuple[str, Dict[str, Any]], None]:
        """
        Stream a query response using the RFP agent
        
        Args:
            messages: List of conversation messages
            project_id: The project ID to use for retrieval
            
        Yields:
            Tuples of (chunk_text, metadata) where metadata contains information about the chunk
        """
        query_text = messages[-1]["content"] if messages else ""
        logger.info(f"Streaming query: '{query_text}' for project: {project_id}")
        
        # Get the RFP agent from the global registry
        rfp_agent = agents.get("rfp_agent")
        if not rfp_agent:
            raise RuntimeError("RFP agent not initialized. Ensure the application lifespan is properly configured.")
        
        # Stream the response
        async for chunk, metadata in rfp_agent.astream(messages, project_id):
            yield chunk, metadata
    
    @staticmethod
    async def summarize_document(document_id: str, project_id: str) -> str:
        """
        Summarize a document using a summarization agent (placeholder for future implementation)
        
        Args:
            document_id: The document to summarize
            project_id: The project ID
            
        Returns:
            The document summary
        """
        # This is a placeholder for future implementation
        logger.info(f"Summarizing document: {document_id} for project: {project_id}")
        
        # In the future, you would use a dedicated summarization agent:
        # summarization_agent = agents.get("summarization_agent")
        # return await summarization_agent.summarize(document_id, project_id)
        
        return "Document summarization not yet implemented"

# Dependency to get the AIService
def get_ai_service() -> AIService:
    """
    Factory function that returns an AIService instance.
    This is used for FastAPI dependency injection.
    """
    return AIService()