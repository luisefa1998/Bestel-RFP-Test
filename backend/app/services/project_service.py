import os
import uuid
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import aiofiles

from pydantic import BaseModel
from app.core.settings import settings

# Set up logging
logger = logging.getLogger(__name__)

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class Project(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime

class ProjectService:
    def __init__(self):
        self.projects_dir = settings.PROJECTS_DIR
        os.makedirs(self.projects_dir, exist_ok=True)
        
    def _get_project_dir(self, project_id: str) -> Path:
        """Get the directory path for a project"""
        return self.projects_dir / project_id
        
    def _get_metadata_path(self, project_id: str) -> Path:
        """Get the path to the project's metadata file"""
        return self._get_project_dir(project_id) / "metadata.json"
        
    async def create_project(self, project_data: ProjectCreate) -> Project:
        """
        Create a new project with the given name and description
        
        Args:
            project_data: The project data containing name and optional description
            
        Returns:
            The created project with generated ID and timestamp
        """
        project_id = "proj_" + str(uuid.uuid4()).replace("-", "_")
        project = Project(
            project_id=project_id,
            name=project_data.name,
            description=project_data.description,
            created_at=datetime.now()
        )
        
        # Create project directory structure
        project_dir = self._get_project_dir(project_id)
        uploads_dir = project_dir / "uploads"
        status_dir = project_dir / "status"
        
        os.makedirs(project_dir, exist_ok=True)
        os.makedirs(uploads_dir, exist_ok=True)
        os.makedirs(status_dir, exist_ok=True)
        
        # Save project metadata within the project directory
        metadata_file = self._get_metadata_path(project_id)
        async with aiofiles.open(metadata_file, 'w') as f:
            await f.write(project.json())
            
        logger.info(f"Created project: {project_id} - {project.name}")
        return project
        
    async def get_project(self, project_id: str) -> Optional[Project]:
        """
        Get a project by its ID
        
        Args:
            project_id: The unique identifier of the project
            
        Returns:
            The project if found, None otherwise
        """
        metadata_file = self._get_metadata_path(project_id)
        if not os.path.exists(metadata_file):
            logger.warning(f"Project not found: {project_id}")
            return None
            
        async with aiofiles.open(metadata_file, 'r') as f:
            content = await f.read()
            project = Project.parse_raw(content)
            return project
            
    async def list_projects(self) -> List[Project]:
        """
        List all projects
        
        Returns:
            List of all projects
        """
        projects = []
        if not os.path.exists(self.projects_dir):
            return projects
            
        # Look for directories in the projects directory
        for item in os.listdir(self.projects_dir):
            dir_path = self.projects_dir / item
            if os.path.isdir(dir_path):
                # Check if this directory has a metadata.json file
                metadata_file = dir_path / "metadata.json"
                if os.path.exists(metadata_file):
                    project = await self.get_project(item)
                    if project:
                        projects.append(project)
        
        logger.info(f"Listed {len(projects)} projects")
        return projects
    
    async def delete_project(self, project_id: str) -> bool:
        """
        Delete a project and its directory
        
        Args:
            project_id: The unique identifier of the project
            
        Returns:
            True if deletion was successful, False otherwise
        """
        project_dir = self._get_project_dir(project_id)
        
        if not os.path.exists(project_dir):
            logger.warning(f"Project directory not found: {project_id}")
            return False
        
        try:
            shutil.rmtree(project_dir)
            logger.info(f"Deleted project directory: {project_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {str(e)}")
            raise

# Made with Bob
