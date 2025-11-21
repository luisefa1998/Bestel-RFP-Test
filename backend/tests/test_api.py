import requests
import json
import sys
import os
from pathlib import Path

# Add the backend directory to the path so we can import from app if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_first_project_id():
    """Get the first available project ID"""
    projects_dir = Path("../data/projects")
    if not projects_dir.exists():
        print("No projects directory found")
        return None
    
    project_dirs = [d for d in projects_dir.iterdir() if d.is_dir()]
    if not project_dirs:
        print("No projects found")
        return None
    
    # Extract the UUID part from the directory name
    project_id = project_dirs[0].name.split("_", 1)[1] if "_" in project_dirs[0].name else project_dirs[0].name
    print(f"Using project: {project_id}")
    return project_id

def test_query_endpoint(query, project_id=None):
    """
    Test the query endpoint with a specific query
    
    Args:
        query: The query to test
        project_id: The project ID to use (if None, will use the first available project)
    """
    # API endpoint
    url = "http://localhost:8000/api/v1/query"
    
    # Request payload
    payload = {
        "text": query,
        "project_id": project_id
    }
    
    print(f"Sending query: '{query}' to project: {project_id}")
    
    # Make the request
    try:
        response = requests.post(url, json=payload)
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            print("\n" + "-" * 80)
            print("Response:")
            print(result["result"])
            print("-" * 80 + "\n")
            return result
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Error making request: {str(e)}")
        return None

if __name__ == "__main__":
    # Sample query about the RFP
    query = "Se permite subcontratar parte del trabajo según la licitación?"
    project_id: str = "proj_6046829a_a22d_4465_9461_2c209ca07234"
    
    # Run the test
    test_query_endpoint(query, project_id)

# Made with Bob
