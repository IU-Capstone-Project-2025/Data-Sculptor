from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager

import asyncpg
import uvicorn
from fastapi import FastAPI

from router import router as progress_router
from settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    pg_pool = await asyncpg.create_pool(settings.progress_postgres_dsn)
    try:
        yield {"postgres_pool": pg_pool}
    finally:
        await pg_pool.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Progress Tracker Service", version="0.1.0", lifespan=lifespan)

    app.include_router(progress_router, prefix="/api/v1")
    return app


async def startup() -> None:
    app = create_app()

    config = uvicorn.Config(
        app,
        host=settings.progress_service_host,
        port=settings.progress_service_port,
        workers=settings.progress_service_n_workers,
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(startup()) 