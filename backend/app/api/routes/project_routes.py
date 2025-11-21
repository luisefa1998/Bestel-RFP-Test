# backend/app/api/routes/project_routes.py
from fastapi import APIRouter, HTTPException
from app.services.project_service import ProjectService, ProjectCreate, Project
from app.services.data_reset_service import DataResetService
from typing import List
import logging

router = APIRouter()
project_service = ProjectService()
data_reset_service = DataResetService()
logger = logging.getLogger(__name__)

@router.post("", response_model=Project)
async def create_project(project_data: ProjectCreate):
    """Create a new project"""
    try:
        project = await project_service.create_project(project_data)
        return project
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating project: {str(e)}")

@router.get("", response_model=List[Project])
async def list_projects():
    """List all projects"""
    try:
        projects = await project_service.list_projects()
        return projects
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing projects: {str(e)}")

@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    """Get a specific project by ID"""
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return project

@router.delete("/{project_id}", status_code=200)
async def delete_project(project_id: str):
    """
    Delete a single project by ID, including its Milvus collection and project directory.
    WARNING: This operation cannot be undone!
    """
    try:
        # Delete Milvus collection
        collection_result = await data_reset_service.delete_project_data(project_id)
        
        # Delete project directory
        project_deleted = await project_service.delete_project(project_id)
        
        # Check for errors
        has_errors = collection_result.get("error") is not None or not project_deleted
        
        if has_errors:
            return {
                "status": "partial_success" if project_deleted or collection_result["collection_deleted"] else "error",
                "message": "Project deletion completed with some errors",
                "details": {
                    "collection": collection_result,
                    "project_directory_deleted": project_deleted
                }
            }
        
        return {
            "status": "success",
            "message": f"Project {project_id} has been successfully deleted",
            "details": {
                "collection": collection_result,
                "project_directory_deleted": project_deleted
            }
        }
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting project: {str(e)}")

@router.delete("/reset/all", status_code=200)
async def reset_all_data():
    """
    Reset all data by deleting all Milvus cloud collections and projects.
    WARNING: This operation cannot be undone!
    """
    
    logger.info("Initiating full data reset...")
    
    try:
        result = await data_reset_service.reset_all_data()
        
        # Check if there were any errors
        has_errors = (
            len(result["embeddings"]["errors"]) > 0 or
            len(result["projects"]["errors"]) > 0
        )
        
        if has_errors:
            return {
                "status": "partial_success",
                "message": "Data reset completed with some errors",
                "details": result
            }
        
        return {
            "status": "success",
            "message": "All data has been successfully reset",
            "details": result
        }
    except Exception as e:
        logger.error(f"Error during data reset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error resetting data: {str(e)}")

# Made with Bob
