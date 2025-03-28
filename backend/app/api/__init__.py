from fastapi import APIRouter
from app.api.auth import router as auth_router

# Create main API router
api_router = APIRouter()

# Include all API routers
api_router.include_router(auth_router)

# Add more routers as needed:
# api_router.include_router(text_processing_router)
# api_router.include_router(ar_integration_router)
# api_router.include_router(feedback_router)
