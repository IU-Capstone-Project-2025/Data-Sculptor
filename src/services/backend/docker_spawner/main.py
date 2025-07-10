import os
import tempfile
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from docker_service import DockerSpawnerService
from auth_service import AuthService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Environment variables
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "case")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8080")

class SpawnRequest(BaseModel):
    case_id: str
    oauth_token: str
    container_name: Optional[str] = None
    port_mapping: Optional[dict] = None

class SpawnResponse(BaseModel):
    container_id: str
    status: str
    message: str

class ContainerStatusResponse(BaseModel):
    container_id: str
    status: str
    running: bool
    ports: dict
    logs: Optional[str] = None

app = FastAPI(title="Docker Spawner Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
auth_service = AuthService(AUTH_SERVICE_URL)
docker_service = DockerSpawnerService(S3_BUCKET_NAME, S3_REGION)

@app.post("/spawn", response_model=SpawnResponse)
async def spawn_container(request: SpawnRequest):
    """
    Spawn a Docker container from an S3 image.
    
    Args:
        request: SpawnRequest containing case_id, oauth_token, and optional container_name/port_mapping
    
    Returns:
        SpawnResponse with container_id and status
    """
    try:
        # Validate OAuth token
        if not await auth_service.validate_token(request.oauth_token):
            raise HTTPException(status_code=401, detail="Invalid OAuth token")
        
        # Spawn the container
        container_info = await docker_service.spawn_container(
            case_id=request.case_id,
            container_name=request.container_name,
            port_mapping=request.port_mapping
        )
        
***REMOVED*** SpawnResponse(
            container_id=container_info["container_id"],
            status="success",
            message=f"Container {container_info['container_id']} spawned successfully"
        )
        
    except Exception as e:
        logger.error(f"Error spawning container: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/container/{container_id}/status", response_model=ContainerStatusResponse)
async def get_container_status(container_id: str):
    """
    Get the status of a running container.
    
    Args:
        container_id: The ID of the container to check
    
    Returns:
        ContainerStatusResponse with container status information
    """
    try:
        status_info = await docker_service.get_container_status(container_id)
***REMOVED*** ContainerStatusResponse(**status_info)
        
    except Exception as e:
        logger.error(f"Error getting container status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/container/{container_id}")
async def stop_container(container_id: str):
    """
    Stop and remove a container.
    
    Args:
        container_id: The ID of the container to stop
    """
    try:
        await docker_service.stop_container(container_id)
***REMOVED*** JSONResponse({"message": f"Container {container_id} stopped and removed"})
        
    except Exception as e:
        logger.error(f"Error stopping container: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "docker-spawner"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 