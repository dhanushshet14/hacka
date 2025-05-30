from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel

from app.core.config import settings
from app.api.auth import get_current_user
from app.models.user import User
from app.integrations.stt import process_audio
from app.mcp.mcp_server import mcp_server

router = APIRouter(prefix=f"{settings.API_V1_STR}/text-processing", tags=["text-processing"])

# Models
class TextAnalysisRequest(BaseModel):
    text: str
    context_id: Optional[str] = None
    options: Optional[Dict[str, Any]] = None

class TextAnalysisResponse(BaseModel):
    request_id: str
    entities: List[Dict[str, Any]]
    concepts: List[Dict[str, Any]]
    intent: Optional[Dict[str, Any]] = None
    sentiment: Optional[Dict[str, Any]] = None

class SpeechToTextRequest(BaseModel):
    audio_format: str = "wav"
    language: str = "en"
    context_id: Optional[str] = None

class SpeechToTextResponse(BaseModel):
    request_id: str
    text: str
    confidence: float
    segments: Optional[List[Dict[str, Any]]] = None

# Routes
@router.post("/analyze", response_model=TextAnalysisResponse)
async def analyze_text(
    request: TextAnalysisRequest, 
    current_user: User = Depends(get_current_user)
):
    """
    Analyze text for semantic meaning, entities, and concepts
    """
    try:
        # Prepare MCP request to text-to-scene agent
        mcp_request = {
            "action": "text_to_scene",
            "user_id": str(current_user.id),
            "data": {
                "text": request.text,
                "context_id": request.context_id,
                "options": request.options or {}
            }
        }
        
        # Process request through MCP
        client_id = f"api-{current_user.id}"
        response = await mcp_server.handle_text_to_scene(mcp_request)
        
        if not response.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.message
            )
        
        # Return text analysis result
        return {
            "request_id": response.request_id,
            "entities": response.data.get("entities", []),
            "concepts": response.data.get("concepts", []),
            "intent": response.data.get("intent"),
            "sentiment": response.data.get("sentiment")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing text: {str(e)}"
        )

@router.post("/speech-to-text", response_model=SpeechToTextResponse)
async def speech_to_text(
    audio_file: UploadFile = File(...),
    language: str = "en",
    context_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Convert speech audio to text using Whisper
    """
    try:
        # Process audio file with the STT integration
        stt_result = await process_audio(
            audio_file=audio_file,
            language=language
        )
        
        # Generate unique request ID
        request_id = f"stt-{audio_file.filename}-{current_user.id}"
        
        # Return speech-to-text result
        return {
            "request_id": request_id,
            "text": stt_result["text"],
            "confidence": stt_result["confidence"],
            "segments": stt_result.get("segments")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing speech: {str(e)}"
        )
