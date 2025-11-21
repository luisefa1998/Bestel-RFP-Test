from fastapi import APIRouter, Depends, HTTPException
from app.services.ai_service import AIService, get_ai_service
from app.schemas.models import Query, Response
import logging

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/query", response_model=Response)
async def process_query(query: Query, ai_service: AIService = Depends(get_ai_service)):
    """
    Process a query using the AI service
    
    Args:
        query: The query to process
        ai_service: The AI service to use
        
    Returns:
        The AI response
    """
    try:
        result = await AIService.process_query(query.text, query.messages, query.project_id)
        return Response(result=result)
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")
