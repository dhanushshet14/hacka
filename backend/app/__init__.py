import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.api import api_router

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
    )
    
    # Set up CORS
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Set up startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting application")
        
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down application")
        
    # Include API routers
    app.include_router(api_router)
    
    return app