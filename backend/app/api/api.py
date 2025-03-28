from fastapi import APIRouter

from app.api.endpoints import auth, users, text_processing, speech, documents

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(text_processing.router, prefix="/text", tags=["text processing"])
api_router.include_router(speech.router, prefix="/speech", tags=["speech"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"]) 