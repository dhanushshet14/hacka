import os
import uvicorn
from dotenv import load_dotenv
import time
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from loguru import logger
import asyncio
from typing import List

# Import settings directly from config
from app.core.config import settings
from app.db import init_mongodb, init_redis

# Import API routers
from app.api.api import api_router
from app.api.endpoints.flow import router as flow_router

# Load environment variables
load_dotenv()

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    description="Aetherion AR Backend API",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SECRET_KEY
)

# Add request processing middleware for logging
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.debug(f"Request processed in {process_time:.4f} seconds")
    return response

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.API_VERSION}

# Include API router
app.include_router(api_router, prefix=settings.API_PREFIX)

# Include flow router
app.include_router(flow_router, prefix=f"{settings.API_PREFIX}/flow", tags=["flow"])

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Aetherion AR Backend...")
    
    # Initialize MongoDB connection
    try:
        await init_mongodb()
        logger.info("MongoDB connection established")
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB: {e}")
    
    # Initialize Redis connection
    try:
        init_redis()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
    
    logger.info(f"Aetherion AR Backend started with API version {settings.API_VERSION}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Aetherion AR Backend...")
    # Close any connections or perform cleanup here
    logger.info("Aetherion AR Backend shutdown complete")

if __name__ == "__main__":
    # Run the application with Uvicorn
    host = os.getenv("HOST", settings.MCP_HOST)
    port = int(os.getenv("PORT", settings.MCP_PORT))
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    ) 