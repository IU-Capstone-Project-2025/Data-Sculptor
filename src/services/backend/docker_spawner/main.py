import os
import tempfile
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Path as FastAPIPath
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .docker_service import DockerSpawnerService
from .auth_service import AuthService

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
    """Request body for `/spawn` endpoint."""

    case_id: str = Field(
        ..., description="UUID кейса (Docker-образ хранится в S3 под этим идентификатором)",
        examples=["5ca16dbe-4abe-4f75-956f-2e2d9cb04e24"],
    )
    oauth_token: str = Field(
        ..., description="OAuth-токен пользователя, проверяется Auth-сервисом",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9…"],
    )
    container_name: Optional[str] = Field(
        None,
        description="Опциональное имя контейнера (если не задано, генерируется автоматически)",
        examples=["workshop-alice"],
    )
    port_mapping: Optional[dict] = Field(
        None,
        description="Словарь перенаправлений портов вида {'8888/tcp': 12345}. Если None, порт берётся из образа.",
        examples=[{"8888/tcp": 30123}],
    )

class SpawnResponse(BaseModel):
    """Успешный ответ от `/spawn`."""

    container_id: str = Field(..., description="ID запущенного контейнера")
    status: str = Field(..., description="Статус операции", examples=["success"])
    message: str = Field(..., description="Человекочитаемое сообщение")

class ContainerStatusResponse(BaseModel):
    """Ответ со статусом контейнера."""

    container_id: str = Field(..., description="ID контейнера")
    status: str = Field(..., description="Raw-статус Docker (e.g. 'running', 'exited')", examples=["running"])
    running: bool = Field(..., description="True если контейнер запущен")
    ports: dict = Field(..., description="Сопоставление внутренних ↔ хостовых портов")
    logs: Optional[str] = Field(None, description="Последние логи, если запрошено")

app = FastAPI(
    title="Docker Spawner Service",
    version="1.0.0",
    description="API для запуска Docker-контейнеров из образов, сохранённых в S3, с проверкой аутентификации.",
)

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

@app.post(
    "/spawn",
    response_model=SpawnResponse,
    summary="Запустить контейнер по case_id",
    description=(
        "Создаёт Docker-контейнер из образа, связанного с указанным *case_id*. Перед запуском проверяет "
        "OAuth-токен через Auth-сервис. При успехе возвращает ID контейнера и информацию о портах."
    ),
    tags=["Containers"],
)
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
        
        return SpawnResponse(
            container_id=container_info["container_id"],
            status="success",
            message=f"Container {container_info['container_id']} spawned successfully"
        )
        
    except Exception as e:
        logger.error(f"Error spawning container: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/container/{container_id}/status",
    response_model=ContainerStatusResponse,
    summary="Получить статус контейнера",
    description="Возвращает текущий статус Docker-контейнера, его порты и (опционально) конец логов.",
    tags=["Containers"],
)
async def get_container_status(container_id: str = FastAPIPath(..., description="ID Docker-контейнера")):
    """
    Get the status of a running container.
    
    Args:
        container_id: The ID of the container to check
    
    Returns:
        ContainerStatusResponse with container status information
    """
    try:
        status_info = await docker_service.get_container_status(container_id)
        return ContainerStatusResponse(**status_info)
        
    except Exception as e:
        logger.error(f"Error getting container status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete(
    "/container/{container_id}",
    summary="Остановить и удалить контейнер",
    description="Останавливает работающий Docker-контейнер и удаляет его вместе с ресурсами.",
    tags=["Containers"],
)
async def stop_container(container_id: str = FastAPIPath(..., description="ID Docker-контейнера")):
    """
    Stop and remove a container.
    
    Args:
        container_id: The ID of the container to stop
    """
    try:
        await docker_service.stop_container(container_id)
        return JSONResponse({"message": f"Container {container_id} stopped and removed"})
        
    except Exception as e:
        logger.error(f"Error stopping container: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health", summary="Health-check", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "docker-spawner"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 