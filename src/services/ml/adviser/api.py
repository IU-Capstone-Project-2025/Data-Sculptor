"""Main application file for the adviser chat service.

This module initializes the FastAPI application, includes the API router,
and sets up the server to run with uvicorn.

Public API:
    - create_app: Creates and configures the FastAPI application instance.
    - startup: Initializes and runs the FastAPI application.
"""

import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import redis.asyncio as aioredis
import asyncpg
from tokenizers import Tokenizer

from router import router as advisor_router
from settings import settings


def create_app() -> FastAPI:
    """Creates and configures the FastAPI application instance."""

    app = FastAPI(
        title="Adviser Chat Service",
        description="An API to communicate with the LLM for coding assistance.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(advisor_router, prefix="/api/v1")

    return app


async def startup():
    """Initializes and runs the FastAPI application."""
    app = create_app()

    config = uvicorn.Config(
        app,
        host=settings.chat_service_host,
        port=settings.chat_service_port,
        workers=settings.chat_service_n_workers,
    )
    server = uvicorn.Server(config)
    await server.serve()


# Lifespan to manage shared resources
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and graceful shutdown of shared resources.

    Creates Redis and Postgres connections and a tokenizer instance once
    per process.  The objects are exposed through the `state` mapping so
    that they can be accessed from request handlers.
    """
    # startup
    redis = await aioredis.from_url(settings.redis_url, decode_responses=True)
    pg_pool = await asyncpg.create_pool(settings.postgres_dsn)
    tokenizer = Tokenizer.from_pretrained(settings.tokenizer_model)

    # expose objects through lifespan state dict
    yield {
        "redis_pool": redis,
        "postgres_pool": pg_pool,
        "tokenizer": tokenizer,
    }

    await redis.aclose()
    await pg_pool.close()


if __name__ == "__main__":
    asyncio.run(startup())
