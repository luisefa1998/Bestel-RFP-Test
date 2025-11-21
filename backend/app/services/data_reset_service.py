import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Any
from pymilvus import MilvusClient, connections, utility
from app.core.settings import settings

logger = logging.getLogger(__name__)


class DataResetService:
    """
    Service to handle complete data reset operations:
    - Delete all Milvus cloud collections
    - Delete all project directories
    """
    
    def __init__(self):
        self.projects_dir = settings.PROJECTS_DIR
        
        # Connect to cloud Milvus instance
        self.connection_args = {
            'host': settings.MILVUS_HOST,
            'port': settings.MILVUS_PORT,
            'user': settings.MILVUS_USER,
            'password': settings.MILVUS_KEY,
            'secure': True
        }
    
    async def reset_all_data(self) -> Dict[str, Any]:
        """
        Delete all Milvus collections and project data
        
        Returns:
            Dictionary with deletion status for embeddings (collections) and projects
        """
        result = {
            "embeddings": {"deleted": False, "errors": []},
            "projects": {"deleted_count": 0, "errors": []}
        }
        
        # Delete all Milvus collections (cloud-hosted embeddings)
        try:
            # Connect to Milvus
            connections.connect(
                alias='default',
                **self.connection_args
            )
            
            # Get all collections
            collections = utility.list_collections()
            logger.info(f"Found {len(collections)} collections in Milvus cloud")
            
            # Delete each collection
            deleted_count = 0
            for collection_name in collections:
                try:
                    utility.drop_collection(collection_name)
                    deleted_count += 1
                    logger.info(f"Deleted Milvus collection: {collection_name}")
                except Exception as e:
                    error_msg = f"Error deleting collection {collection_name}: {str(e)}"
                    logger.error(error_msg)
                    result["embeddings"]["errors"].append(error_msg)
            
            # Disconnect from Milvus
            connections.disconnect(alias='default')
            
            # Mark as deleted if we successfully processed all collections
            result["embeddings"]["deleted"] = True
            logger.info(f"Successfully deleted {deleted_count} Milvus collections from cloud")
            
        except Exception as e:
            error_msg = f"Error accessing Milvus cloud: {str(e)}"
            logger.error(error_msg)
            result["embeddings"]["errors"].append(error_msg)
        
        # Delete projects directory contents
        try:
            if os.path.exists(self.projects_dir):
                deleted_count = 0
                for item in os.listdir(self.projects_dir):
                    dir_path = self.projects_dir / item
                    if os.path.isdir(dir_path):
                        try:
                            shutil.rmtree(dir_path)
                            deleted_count += 1
                            logger.info(f"Deleted project directory: {item}")
                        except Exception as e:
                            error_msg = f"Error deleting project {item}: {str(e)}"
                            logger.error(error_msg)
                            result["projects"]["errors"].append(error_msg)
                
                result["projects"]["deleted_count"] = deleted_count
                logger.info(f"Successfully deleted {deleted_count} projects")
            else:
                logger.info("Projects directory does not exist")
        except Exception as e:
            error_msg = f"Error accessing projects directory: {str(e)}"
            logger.error(error_msg)
            result["projects"]["errors"].append(error_msg)
        
        return result
    
    async def delete_project_data(self, project_id: str) -> Dict[str, Any]:
        """
        Delete Milvus collection for a single project
        
        Args:
            project_id: The project ID (which is also the collection name)
            
        Returns:
            Dictionary with deletion status
        """
        result = {
            "collection_deleted": False,
            "error": None
        }
        
        try:
            # Connect to Milvus
            connections.connect(
                alias='default',
                **self.connection_args
            )
            
            # Check if collection exists
            collections = utility.list_collections()
            
            if project_id in collections:
                try:
                    utility.drop_collection(project_id)
                    result["collection_deleted"] = True
                    logger.info(f"Deleted Milvus collection for project: {project_id}")
                except Exception as e:
                    error_msg = f"Error deleting collection {project_id}: {str(e)}"
                    logger.error(error_msg)
                    result["error"] = error_msg
            else:
                error_msg = f"Collection {project_id} does not exist in Milvus"
                logger.info(error_msg)
                result["collection_deleted"] = False
            
            # Disconnect from Milvus
            connections.disconnect(alias='default')
            
        except Exception as e:
            error_msg = f"Error accessing Milvus cloud: {str(e)}"
            logger.error(error_msg)
            result["error"] = error_msg
        
        return result

# Made with Bob