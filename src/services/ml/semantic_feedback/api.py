"""Main application file for the feedback service.

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


from router import router as feedback_router
from settings import settings


def create_app() -> FastAPI:
    """Creates and configures the FastAPI application instance."""

    app = FastAPI(
        title="Semantic Feedback Service",
        description="An API to get LLM-powered feedback on code.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(feedback_router, prefix="/api/v1")

    return app


async def startup():
    """Initializes and runs the FastAPI application."""
    app = create_app()

    config = uvicorn.Config(
        app,
        host=settings.feedback_service_host,
        port=settings.feedback_service_port,
        workers=settings.feedback_service_n_workers,
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(startup())
