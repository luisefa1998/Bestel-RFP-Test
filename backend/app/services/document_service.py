import os
import uuid
import json
import logging
import datetime
import aiofiles
from fastapi import UploadFile
from pathlib import Path
from app.core.settings import settings

# Set up logging
logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        self.projects_dir = settings.PROJECTS_DIR
    
    def get_upload_dir(self, project_id: str) -> Path:
        """Get the upload directory for a specific project"""
        upload_dir = self.projects_dir / project_id / "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        return upload_dir
    
    def get_status_dir(self, project_id: str) -> Path:
        """Get the status directory for a specific project"""
        status_dir = self.projects_dir / project_id / "status"
        os.makedirs(status_dir, exist_ok=True)
        return status_dir
    
    def get_markdown_dir(self, project_id: str) -> Path:
        """Get the markdown directory for a specific project"""
        markdown_dir = self.projects_dir / project_id / "markdowns"
        os.makedirs(markdown_dir, exist_ok=True)
        return markdown_dir
    
    def get_summary_dir(self, project_id: str) -> Path:
        """Get the summary directory for a specific project"""
        summary_dir = self.projects_dir / project_id / "summaries"
        os.makedirs(summary_dir, exist_ok=True)
        return summary_dir
    
    async def save_uploaded_file(self, project_id: str, file: UploadFile) -> tuple[str, str]:
        """
        Save the uploaded file to the project's upload directory
        
        Args:
            project_id: The ID of the project
            file: The uploaded file
            
        Returns:
            Tuple of (file_path, document_id)
        """
        if file.filename:
            original_filename = file.filename
            document_id = Path(original_filename).stem
        else:
            # Generate a random filename with UUID if none is provided
            random_id = str(uuid.uuid4())
            original_filename = f"{random_id}.pdf"
            document_id = random_id
            
        upload_dir = self.get_upload_dir(project_id)
        file_path = upload_dir / original_filename
        
        # Write file content using aiofiles for non-blocking I/O
        async with aiofiles.open(file_path, "wb") as out_file:
            # Read and write in chunks to avoid loading entire file into memory
            chunk_size = 1024 * 1024  # 1MB chunks
            while chunk := await file.read(chunk_size):
                await out_file.write(chunk)
        
        # Initialize processing status directly to file
        status_data = {
            "status": "saved",
            "progress": 10,
            "filename": original_filename,
            "document_id": document_id,
            "project_id": project_id,
            "timestamp": str(datetime.datetime.now())
        }
        
        # Save initial status to file
        status_dir = self.get_status_dir(project_id)
        status_file = status_dir / f"{document_id}.json"
        async with aiofiles.open(status_file, 'w') as f:
            await f.write(json.dumps(status_data))
        
        return str(file_path), document_id
    
    async def get_processing_status(self, project_id: str, document_id: str):
        """
        Get the current processing status directly from file
        
        Args:
            project_id: The ID of the project
            document_id: The ID of the document
            
        Returns:
            Status data as a dictionary
        """
        # Check the status file
        status_dir = self.get_status_dir(project_id)
        status_file = status_dir / f"{document_id}.json"
        if os.path.exists(status_file):
            try:
                async with aiofiles.open(status_file, 'r') as f:
                    content = await f.read()
                    status_data = json.loads(content)
                    return status_data
            except Exception as e:
                logger.error(f"Error reading status file for document {document_id}: {str(e)}")
        
        return {"status": "not_found", "document_id": document_id, "project_id": project_id}
    
    async def get_markdown_content(self, project_id: str, document_id: str) -> str:
        """
        Get the markdown content for a document
        
        Args:
            project_id: The ID of the project
            document_id: The ID of the document
            
        Returns:
            Dictionary containing document_id, project_id, and markdown content
            
        Raises:
            FileNotFoundError: If document or markdown file is not found
            Exception: For other errors reading the markdown file
        """
        # Check if document exists
        status = await self.get_processing_status(project_id, document_id)
        if "status" in status and status["status"] == "not_found":
            raise FileNotFoundError("Document not found or processing not completed")
        
        # Get the markdown file path
        markdown_dir = self.get_markdown_dir(project_id)
        markdown_path = markdown_dir / f"{document_id}.md"
        
        # Check if markdown file exists
        if not os.path.exists(markdown_path):
            if status["status"] != "completed":
                raise FileNotFoundError(f"Markdown not available yet. Document status: {status['status']}")
            else:
                raise FileNotFoundError("Markdown file not found even though processing is complete")
        
        try:
            # Read the markdown file
            async with aiofiles.open(markdown_path, 'r', encoding='utf-8') as f:
                markdown_content = await f.read()
            
            return markdown_content
        except Exception as e:
            logger.error(f"Error reading markdown file for document {document_id}: {str(e)}")
            raise Exception(f"Error reading markdown file: {str(e)}")
    
    async def save_summary(self, project_id: str, document_id: str, summary_data: dict):
        """
        Save document summary to file system. Supports multiple summary types per document.
        
        The summary file structure is:
        {
            "document_id": "...",
            "project_id": "...",
            "summaries": [
                {"type": "executive", "summary": "...", "timestamp": "...", ...},
                {"type": "detailed", "summary": "...", "timestamp": "...", ...}
            ]
        }
        
        Args:
            project_id: The ID of the project
            document_id: The ID of the document
            summary_data: Dictionary containing summary type, content, and metadata
        """
        summary_dir = self.get_summary_dir(project_id)
        summary_path = summary_dir / f"{document_id}.json"
        
        try:
            # Try to load existing summary file using get_summary, or create new structure
            try:
                existing_data = await self.get_summary(project_id, document_id)
            except FileNotFoundError:
                existing_data = {
                    "document_id": document_id,
                    "project_id": project_id,
                    "summaries": []
                }
            
            # Extract the summary type from the new summary data
            summary_type = summary_data.get("summarization_type", "executive")
            
            # Create new summary entry
            new_summary = {
                "type": summary_type,
                "summary": summary_data.get("summary"),
                "collapse_level": summary_data.get("collapse_level", "none"),
                "num_chunks": summary_data.get("num_chunks", 0),
                "timestamp": summary_data.get("timestamp")
            }
            
            # Remove any existing summary of the same type and add the new one
            existing_data["summaries"] = [
                s for s in existing_data.get("summaries", [])
                if s.get("type") != summary_type
            ]
            existing_data["summaries"].append(new_summary)
            
            # Save updated summary file
            async with aiofiles.open(summary_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(existing_data, indent=2, ensure_ascii=False))
            
            logger.info(f"{summary_type.capitalize()} summary saved for document {document_id} in project {project_id}")
        except Exception as e:
            logger.error(f"Error saving summary for document {document_id}: {str(e)}")
            raise Exception(f"Error saving summary: {str(e)}")
    
    async def get_summary(self, project_id: str, document_id: str) -> dict:
        """
        Get document summary from file system
        
        Args:
            project_id: The ID of the project
            document_id: The ID of the document
            
        Returns:
            Dictionary containing summary and metadata
            
        Raises:
            FileNotFoundError: If summary file is not found
            Exception: For other errors reading the summary file
        """
        summary_dir = self.get_summary_dir(project_id)
        summary_path = summary_dir / f"{document_id}.json"
        
        if not os.path.exists(summary_path):
            raise FileNotFoundError(f"Summary not found for document {document_id}")
        
        try:
            async with aiofiles.open(summary_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                summary_data = json.loads(content)
            return summary_data
        except Exception as e:
            logger.error(f"Error reading summary for document {document_id}: {str(e)}")
            raise Exception(f"Error reading summary: {str(e)}")

# Made with Bob
