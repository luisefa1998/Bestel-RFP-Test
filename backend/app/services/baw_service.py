import os
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import aiofiles
import base64
import ssl
import http.client
import json


from pydantic import BaseModel
from app.core.settings import settings

# Set up logging
logger = logging.getLogger(__name__)

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class BAWLogin(BaseModel):
    username: str
    password: str

class BAWIDs(BaseModel):
    username: str
    password: str
    processAppName: str

class BAWStartProcess(BaseModel):
    username: str
    password: str
    itemID: str
    processAppID: str
    action: str

class BAWProcessActions(BaseModel):
    username: str
    password: str
    piid: str
    action: str

class Project(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime

class BAWService:
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

    
    async def start_logging(self, username: str, password: str) -> dict:
      
        # Start login process (mock implementation)
        logger.info(f"Starting BAW login for user: {username}")

        # Obtain the CSRF token
        login_endpoint = "/bpm/system/login/"
        body = {
            "refresh_groups": True,
            "requested_lifetime": 7200
        }
        login_response = rest_request("POST", login_endpoint, body, username, password)

        return login_response

    async def retrive_process_ids(self, username: str, password: str, processAppName: str) -> dict:
      
        # Starting the search for the itemID and processAppID of the indicated process
        logger.info(f"Searching for BAW IDs for process: {processAppName}")

        # Exposed processes endpoint
        processes_endpoint = "/rest/bpm/wle/v1/exposed/process"
        
        # Recovering all exposed processes in BAW (this request doesn't need any parameters)
        exposed_processes = rest_request("GET", processes_endpoint, {} , username, password)["data"]["exposedItemsList"]

        itemID = ""
        processAppID = ""
        ids_result = {}

        for process in exposed_processes:

            if process["processAppName"] == processAppName:
                itemID = process["itemID"]
                processAppID = process["processAppID"]
            
            ids_result = {
                "itemID": itemID,
                "processAppID": processAppID
            }

        return ids_result



    async def start_process(self, username: str, password: str, itemID: str, processAppID: str, action: str) -> dict:
        
        # Depending on the type of action selected, execute one option or another.
        start_process_endpoint = f"/rest/bpm/wle/v1/process?action={action}&bpdId={itemID}&processAppId={processAppID}&parts=all"
        params = {
            "action": action,
            "bpdId": itemID,
            "processAppId": processAppID,
            "parts": "all"
        }
        action_response = rest_request("POST", start_process_endpoint, body=json.dumps(params), username=username, password=password)
        
        action_result = {
            "status": action_response["status"],
            "data": {
                "creationTime": action_response["data"]["creationTime"],
                "piid": action_response["data"]["piid"],
                "tasks": action_response["data"]["tasks"]
            }
        }


        return action_result
    

    async def triggering_process_actions(self, username: str, password: str, piid: str, action: str) -> dict:
        
        # Depending on the type of action selected, execute one option or another.

        current_status_endpoint = f"/rest/bpm/wle/v1/process/{piid}?parts=all"
        main_actions_endpoint = f"/rest/bpm/wle/v1/process/{piid}?action={action}&parts=all"

        action_response = {}

        if action == "current_status":
            action_response = rest_request("GET", current_status_endpoint, body={}, username=username, password=password)

        elif action in ["suspend", "resume", "terminate", "retry"]:
            action_response = rest_request("PUT", main_actions_endpoint, body={}, username=username, password=password)

        elif action == "delete":
            action_response = rest_request("DELETE", main_actions_endpoint, body={}, username=username, password=password)
        
        action_result = action_response

        return action_result


# ======== Complementary functions ===========

# Send REST-API requests
def rest_request(req_type: str, endpoint: str, body: dict, username: str, password: str) -> dict:
    """
    Send a REST API request to IBM BAW.
    """

    # BAW Server
    host = "useast.services.cloud.techzone.ibm.com"
    port = 25665

    # Encode credentials (Basic Auth)
    auth_base64 = base64.b64encode(f"{username}:{password}".encode()).decode()

    # Disable SSL verification
    context = ssl._create_unverified_context()

    # Create HTTPS connection
    conn = http.client.HTTPSConnection(host, port, context=context)

    # Define headers
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # Convert the body dict to JSON string
    json_body = json.dumps(body)

    # Prepare response container
    req_response = {}

    # Normalize method type
    req_type = req_type.upper()

    # === Send request ===
    match req_type:
        case "GET":
            conn.request("GET", endpoint, headers=headers)

        case "POST":
            conn.request("POST", endpoint, body=json_body, headers=headers)

        case "PUT":
            conn.request("PUT", endpoint, body=json_body, headers=headers)

        case "DELETE":
            conn.request("DELETE", endpoint, body=json_body, headers=headers)

        case _:
            print(f"Unsupported request type: {req_type}")
            conn.close()
            return {}

    # Get response
    res = conn.getresponse()
    data = res.read().decode("utf-8")

    # Parse JSON response
    try:
        req_response = json.loads(data)
    except json.JSONDecodeError:
        req_response = {"raw_response": data}

    # Close connection
    conn.close()

    return req_response