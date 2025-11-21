from fastapi import APIRouter, Depends, HTTPException
from app.services.ai_service import AIService, get_ai_service
from app.services.baw_service import BAWService, BAWLogin, BAWIDs, BAWStartProcess, BAWProcessActions
from app.schemas.models import Query, Response, BAWResponse
import logging

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()
baw_service = BAWService()

@router.post("/baw/login", response_model=BAWResponse)
async def start_logging(loggin_data: BAWLogin):
    
    """
    Obtain the IDs of a particular BAW process
    
    Args:
        loggin_data: The login data containing username and password

    Returns:
        The login response
    """
    try:
        logger.info(f"BAW login processed for user: {loggin_data.username}")
        result = await baw_service.start_logging(loggin_data.username, loggin_data.password)
        logger.info(f"BAW login result: {result}")
        
        # 👇 devolvemos el dict directamente
        return BAWResponse(result=result)
    
    except Exception as e:
        logger.error(f"Error processing login: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing login: {str(e)}")
    

@router.post("/baw/baw_process_ids", response_model=BAWResponse)
async def retrive_process_ids(baw_process_data: BAWIDs):
    
    """
    Start logging into BAW system
    
    Args:
        baw_process_data: The login data containing username and password and BAW processAppName

    Returns:
        The itemID and processAppID of the BAW process
    """
    try:
        result = await baw_service.retrive_process_ids(baw_process_data.username, baw_process_data.password,  baw_process_data.processAppName)
        logger.info(f"BAW process IDs result: {result}")
        return BAWResponse(result=result)
    
    except Exception as e:
        logger.error(f"Error retrieving process IDs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving process IDs: {str(e)}")


@router.post("/baw/start_process", response_model=BAWResponse)
async def start_process(process_action_data: BAWStartProcess):
    
    """
    Start a BAW process
    
    Args:
        process_actions_data: The login data containing username, password and BAW process IDs 
        and start action

    Returns:
        Process ID (piid) and current status
    """

    try:
        result = await baw_service.start_process(process_action_data.username, 
                                                       process_action_data.password,  
                                                       process_action_data.itemID,
                                                       process_action_data.processAppID,
                                                       process_action_data.action)
        logger.info(f"BAW process action result: {result}")
        
        return BAWResponse(result=result)
    
    except Exception as e:
        logger.error(f"Error processing process action: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing process action: {str(e)}")



@router.post("/baw/process_actions", response_model=BAWResponse)
async def triggering_process_actions(process_actions_data: BAWProcessActions):
    
    """
    Trigger different actions with a BAW process.
    Available actions: current_state, suspend, resume, terminate, retry and delete
    
    Args:
        process_actions_data: The login data containing username, password and BAW process instance ID 
        and a particular action

    Returns:
        
    """

    try:
        result = await baw_service.triggering_process_actions(process_actions_data.username, 
                                                              process_actions_data.password,  
                                                              process_actions_data.piid,
                                                              process_actions_data.action)
        logger.info(f"BAW process action result: {result}")
        
        return BAWResponse(result=result)
    
    except Exception as e:
        logger.error(f"Error processing process action: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing process action: {str(e)}")












@router.post("/summarize", response_model=Response)
async def summarize_document(document_id: str, project_id: str, ai_service: AIService = Depends(get_ai_service)):
    """
    Summarize a document using the AI service
    
    Args:
        document_id: The document to summarize
        project_id: The project ID
        ai_service: The AI service to use
        
    Returns:
        The document summary
    """
    try:
        logger.info(f"Summarizing document: '{document_id}' for project: {project_id}")
        result = await AIService.summarize_document(document_id, project_id)
        return Response(result=result)
    except Exception as e:
        logger.error(f"Error summarizing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error summarizing document: {str(e)}")
