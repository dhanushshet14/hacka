from fastapi import APIRouter
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.documents import router as documents_router
from app.api.endpoints.speech import router as speech_router
from app.api.endpoints.textbooks import router as textbooks_router
from app.api.endpoints.assets import router as assets_router
from fastapi import APIRouter, Depends, HTTPException

# Create main API router
api_router = APIRouter()

# Include all API endpoints
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(speech_router, prefix="/speech", tags=["speech"])
api_router.include_router(textbooks_router, prefix="/textbooks", tags=["textbooks"])
api_router.include_router(assets_router, prefix="/assets", tags=["assets"])

# Add dummy endpoints for development
@api_router.get("/users/dashboard-stats", tags=["users"])
async def get_dashboard_stats():
    """
    Dummy endpoint for dashboard statistics
    """
    return {
        "projects": 12,
        "arSessions": 48,
        "textProcesses": 156,
        "hoursUsed": 24,
        "recentProjects": [
            {"id": 1, "name": "Virtual Assistant", "date": "2023-12-15"},
            {"id": 2, "name": "AR Office Tour", "date": "2023-12-10"},
            {"id": 3, "name": "Text Analysis Demo", "date": "2023-12-05"},
        ]
    } 