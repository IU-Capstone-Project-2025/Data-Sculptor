"""Application entry point for the Profile Uploader micro-service."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import asyncpg
import uvicorn
from fastapi import FastAPI

from router import router as upload_router
from settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Allocate and gracefully dispose shared resources.

    A single *asyncpg* pool is created per process and made available via
    `request.state.postgres_pool` for request-time dependencies.
    """

    pg_pool = await asyncpg.create_pool(settings.profile_postgres_dsn)
    try:
        yield {"postgres_pool": pg_pool}
    finally:
        await pg_pool.close()


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""

    app = FastAPI(
        title="Profile Uploader Service",
        description="Accepts Jupyter notebooks and persists structured profiles.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(upload_router, prefix="/api/v1")
    return app


async def startup() -> None:
    """Run the HTTP server using *uvicorn* with the configured parameters."""

    app = create_app()

    config = uvicorn.Config(
        app,
        host=settings.profile_upload_service_host,
        port=settings.profile_upload_service_port,
        workers=settings.profile_upload_service_n_workers,
        timeout_keep_alive=300,  # 5 minutes keep-alive
        timeout_graceful_shutdown=300,  # 5 minutes graceful shutdown
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(startup())
