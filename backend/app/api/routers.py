from fastapi import APIRouter
from app.api.endpoints import auth
from app.api import text_understanding
from app.api.endpoints import textbooks
from app.api.endpoints import assets
from app.api import ar_integration
from app.api import feedback

api_router = APIRouter()

# Include routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(text_understanding.router, prefix="", tags=["text-understanding"])
api_router.include_router(textbooks.router, prefix="/textbooks", tags=["textbooks"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(ar_integration.router, prefix="/ar", tags=["ar"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])

# Add other routers here
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(documents.router, prefix="/documents", tags=["documents"]) 