# backend/app/api/routes/document_routes.py
import os
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Path, Body
from app.services.document_service import DocumentService
from app.services.project_service import ProjectService
from app.schemas.models import SummarizeRequest
from app.core.settings import settings
from app.core.celery_app import celery_app

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()
document_service = DocumentService()
project_service = ProjectService()


@router.post("/projects/{project_id}/documents/upload")
async def upload_document(
    project_id: str = Path(..., description="The ID of the project"),
    file: UploadFile = File(...)
):
    logger.info(f"Upload request received for file: {file.filename} in project: {project_id}")
    
    # Verify project exists
    project = await project_service.get_project(project_id)
    if not project:
        logger.warning(f"Project not found: {project_id}")
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    
    if not file.filename or not any(file.filename.lower().endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):
        logger.warning(f"Invalid file type: {file.filename}")
        raise HTTPException(status_code=400, detail=f"Only {', '.join(settings.ALLOWED_EXTENSIONS)} files are allowed")
    
    try:
        # Save the uploaded file to the project directory
        logger.info(f"Saving uploaded file: {file.filename} to project: {project_id}")
        file_path, document_id = await document_service.save_uploaded_file(project_id, file)
        logger.info(f"File saved: {file_path}, document_id: {document_id}")
        
        # Process the document using Celery task
        # This allows the API to respond quickly while processing continues in a separate worker
        logger.info(f"Submitting Celery task for document processing: {document_id} in project: {project_id}")
        celery_app.send_task(
            "process_document",
            args=[project_id, document_id, str(file_path)]
        )
        logger.info(f"Celery task submitted for document: {document_id}")

        # Return response immediately
        response_data = {
            "message": "Document upload started",
            "filename": file.filename,
            "document_id": document_id,
            "project_id": project_id
        }
        logger.info(f"Returning response for document: {document_id}")
        return response_data
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing upload: {str(e)}")

@router.get("/projects/{project_id}/documents/{document_id}/status")
async def get_processing_status(
    project_id: str = Path(..., description="The ID of the project"),
    document_id: str = Path(..., description="The ID of the document")
):
    # Verify project exists
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
    status = await document_service.get_processing_status(project_id, document_id)
    return status

@router.get("/projects/{project_id}/documents/{document_id}/markdown")
async def get_markdown_content(
    project_id: str = Path(..., description="The ID of the project"),
    document_id: str = Path(..., description="The ID of the document")
):
    """Get the markdown content for a document"""
    # Verify project exists
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    
    try:
        # Get markdown content from service
        markdown_content = await document_service.get_markdown_content(project_id, document_id)
        
        return {
            "document_id": document_id,
            "project_id": project_id,
            "markdown": markdown_content
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_id}/documents")
async def list_project_documents(
    project_id: str = Path(..., description="The ID of the project")
):
    """List all documents in a project"""
    # Verify project exists
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    
    try:
        # Get the status directory for the project
        status_dir = document_service.get_status_dir(project_id)
        
        # List all status files in the directory
        documents = []
        if os.path.exists(status_dir):
            for filename in os.listdir(status_dir):
                if filename.endswith('.json'):
                    document_id = filename.replace('.json', '')
                    status = await document_service.get_processing_status(project_id, document_id)
                    documents.append({
                        "document_id": document_id,
                        "status": status.get("status", "unknown"),
                        "filename": status.get("filename", "unknown"),
                        "progress": status.get("progress", 0)
                    })
        
        return documents
    except Exception as e:
        logger.error(f"Error listing documents for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@router.get("/projects/{project_id}/documents/status")
async def get_project_documents_status(
    project_id: str = Path(..., description="The ID of the project")
):
    """Get status of all documents in a project"""
    # Verify project exists
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    
    try:
        # Get the status directory for the project
        status_dir = document_service.get_status_dir(project_id)
        
        # List all status files in the directory
        documents = []
        if os.path.exists(status_dir):
            for filename in os.listdir(status_dir):
                if filename.endswith('.json'):
                    document_id = filename.replace('.json', '')
                    status = await document_service.get_processing_status(project_id, document_id)
                    documents.append(status)
        
        return documents
    except Exception as e:
        logger.error(f"Error getting document status for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting document status: {str(e)}")


@router.post("/projects/{project_id}/documents/{document_id}/summarize")
async def summarize_document(
    project_id: str = Path(..., description="The ID of the project"),
    document_id: str = Path(..., description="The ID of the document"),
    request: SummarizeRequest = Body(default=SummarizeRequest())
):
    """
    Start document summarization using hierarchical summarization workflow.
    This endpoint triggers an async Celery task and returns immediately.
    
    Supports two summarization types:
    - 'executive' (default): Fast, high-level overview for decision-makers
    - 'detailed': Comprehensive hierarchical analysis with full context
    
    Optional user_query parameter (for 'detailed' type only):
    - Provide natural language instructions to focus the summarization
    - Examples: "Focus on technical specifications and equipment", "Highlight legal concerns and compliance requirements"
    """
    summarization_type = request.summarization_type
    user_query = request.user_query
    
    logger.info(f"Summarization request received for document: {document_id} in project: {project_id}, type: {summarization_type}")
    if user_query:
        logger.info(f"User query provided: {user_query[:100]}...")
    
    # Verify project exists
    project = await project_service.get_project(project_id)
    if not project:
        logger.warning(f"Project not found: {project_id}")
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    
    # Verify document exists and is processed
    status = await document_service.get_processing_status(project_id, document_id)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    
    if status.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Document must be fully processed before summarization. Current status: {status.get('status')}"
        )
    
    # Check if a summarization is already in progress
    summary_status = status.get("summary_status", "not_started")
    if summary_status in ["initializing", "processing"]:
        raise HTTPException(
            status_code=409,  # 409 Conflict
            detail=f"A summarization is already in progress for this document. Current summary status: {summary_status}. Please wait for it to complete before starting a new one."
        )
    
    try:
        # Submit Celery task for summarization with type and user_query parameters
        logger.info(f"Submitting Celery task for {summarization_type} summarization: {document_id} in project: {project_id}")
        celery_app.send_task(
            "summarize_document",
            args=[project_id, document_id, summarization_type, user_query]
        )
        logger.info(f"Celery summarization task submitted for document: {document_id}")
        
        return {
            "message": f"Document summarization started ({summarization_type})",
            "document_id": document_id,
            "project_id": project_id,
            "summarization_type": summarization_type,
            "user_query": user_query,
            "status": "summarizing"
        }
    except Exception as e:
        logger.error(f"Error starting summarization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting summarization: {str(e)}")


@router.get("/projects/{project_id}/documents/{document_id}/summary")
async def get_document_summary(
    project_id: str = Path(..., description="The ID of the project"),
    document_id: str = Path(..., description="The ID of the document")
):
    """
    Get all summaries for a document.
    Returns all available summaries (executive and/or detailed), or status information if still processing.
    """
    # Verify project exists
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    
    # Check document status
    status = await document_service.get_processing_status(project_id, document_id)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    
    # Check if summary exists
    try:
        summary_data = await document_service.get_summary(project_id, document_id)
        return {
            "document_id": document_id,
            "project_id": project_id,
            "status": "completed",
            "summaries": summary_data.get("summaries", [])
        }
    except FileNotFoundError:
        # Summary doesn't exist yet, return status
        summary_status = status.get("summary_status", "not_started")
        return {
            "document_id": document_id,
            "project_id": project_id,
            "status": summary_status,
            "summaries": [],
            "message": "Summary not available yet" if summary_status == "not_started" else f"Summary status: {summary_status}"
        }
    except Exception as e:
        logger.error(f"Error retrieving summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving summary: {str(e)}")
