from typing import Dict, Any, Optional, List, Union
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field
import json
import uuid
from datetime import datetime
import asyncio

from app.core.config import settings
from app.api.auth import get_current_user
from app.models.user import User
from app.integrations.stt import process_audio
from app.mcp.mcp_server import mcp_server

router = APIRouter(prefix=f"{settings.API_V1_STR}/feedback", tags=["feedback"])

# Models for feedback requests
class SceneInteraction(str):
    ROTATE = "rotate"
    SCALE = "scale"
    REPOSITION = "reposition"
    COLOR_CHANGE = "color_change"
    TEXTURE_CHANGE = "texture_change"
    ADD_ELEMENT = "add_element"
    REMOVE_ELEMENT = "remove_element"
    LIGHTING_CHANGE = "lighting_change"
    CUSTOM = "custom"

class Position3D(BaseModel):
    x: float
    y: float
    z: float

class Rotation(BaseModel):
    x: float
    y: float
    z: float
    w: float = 1.0

class Scale(BaseModel):
    x: float = 1.0
    y: float = 1.0
    z: float = 1.0

class ElementInteractionRequest(BaseModel):
    interaction_type: SceneInteraction
    element_id: str
    position: Optional[Position3D] = None
    rotation: Optional[Rotation] = None
    scale: Optional[Scale] = None
    color: Optional[str] = None
    texture_url: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)

class SceneFeedbackRequest(BaseModel):
    scene_id: str
    session_id: Optional[str] = None
    context_id: Optional[str] = None
    text_feedback: Optional[str] = None
    element_interactions: List[ElementInteractionRequest] = Field(default_factory=list)
    environment_changes: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 0  # Higher numbers indicate higher priority
    options: Dict[str, Any] = Field(default_factory=dict)

class FeedbackResponse(BaseModel):
    request_id: str
    scene_id: str
    status: str
    scene_updates: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    updated_scene_url: Optional[str] = None
    update_preview: Optional[str] = None

# Endpoints
@router.post("/scene-interaction", response_model=FeedbackResponse)
async def handle_scene_interaction(
    request: SceneFeedbackRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Process feedback about an AR scene through direct interactions
    like rotating, scaling, or repositioning elements
    """
    try:
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Prepare MCP request
        mcp_request = {
            "action": "update_scene",
            "user_id": str(current_user.id),
            "data": {
                "scene_id": request.scene_id,
                "session_id": request.session_id,
                "context_id": request.context_id or str(current_user.id),
                "text_feedback": request.text_feedback,
                "element_interactions": [interaction.dict() for interaction in request.element_interactions],
                "environment_changes": request.environment_changes,
                "priority": request.priority,
                "options": request.options,
                "feedback_type": "interaction"
            }
        }
        
        # Process sentiment and context updates in background
        if request.text_feedback:
            background_tasks.add_task(
                process_text_feedback,
                request.text_feedback,
                str(current_user.id),
                request.context_id or str(current_user.id),
                request.scene_id
            )
        
        # Send request to MCP server
        response = await mcp_server.handle_request(mcp_request)
        
        if not response.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.message or "Failed to process scene interaction"
            )
        
        # Parse and return the response
        return FeedbackResponse(
            request_id=response.request_id,
            scene_id=request.scene_id,
            status="processing" if response.data.get("status") == "processing" else "completed",
            scene_updates=response.data.get("scene_updates"),
            message=response.message,
            actions=response.data.get("actions", []),
            updated_scene_url=response.data.get("scene_url"),
            update_preview=response.data.get("preview_image")
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing scene interaction: {str(e)}"
        )

@router.post("/text", response_model=FeedbackResponse)
async def handle_text_feedback(
    request: SceneFeedbackRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Process text feedback about an AR scene
    """
    try:
        if not request.text_feedback:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text feedback is required"
            )
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Process sentiment and context updates in background
        background_tasks.add_task(
            process_text_feedback,
            request.text_feedback,
            str(current_user.id),
            request.context_id or str(current_user.id),
            request.scene_id
        )
        
        # Prepare MCP request
        mcp_request = {
            "action": "update_scene",
            "user_id": str(current_user.id),
            "data": {
                "scene_id": request.scene_id,
                "session_id": request.session_id,
                "context_id": request.context_id or str(current_user.id),
                "text_feedback": request.text_feedback,
                "element_interactions": [interaction.dict() for interaction in request.element_interactions],
                "environment_changes": request.environment_changes,
                "priority": request.priority,
                "options": request.options,
                "feedback_type": "text"
            }
        }
        
        # Send request to MCP server
        response = await mcp_server.handle_request(mcp_request)
        
        if not response.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.message or "Failed to process text feedback"
            )
        
        # Parse and return the response
        return FeedbackResponse(
            request_id=response.request_id,
            scene_id=request.scene_id,
            status="processing" if response.data.get("status") == "processing" else "completed",
            scene_updates=response.data.get("scene_updates"),
            message=response.message,
            actions=response.data.get("actions", []),
            updated_scene_url=response.data.get("scene_url"),
            update_preview=response.data.get("preview_image")
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing text feedback: {str(e)}"
        )

@router.post("/voice", response_model=FeedbackResponse)
async def handle_voice_feedback(
    audio_file: UploadFile = File(...),
    scene_id: str = Form(...),
    session_id: Optional[str] = Form(None),
    context_id: Optional[str] = Form(None),
    priority: int = Form(0),
    options: str = Form("{}"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user)
):
    """
    Process voice feedback about an AR scene by first converting to text
    """
    try:
        # Process audio with Whisper
        stt_result = await process_audio(
            audio_file=audio_file,
            language="en"  # Can be made configurable
        )
        
        transcribed_text = stt_result["text"]
        confidence = stt_result["confidence"]
        
        if not transcribed_text or len(transcribed_text.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not transcribe audio or empty audio input"
            )
        
        # Process options
        try:
            parsed_options = json.loads(options)
        except json.JSONDecodeError:
            parsed_options = {}
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Process sentiment and context updates in background
        background_tasks.add_task(
            process_text_feedback,
            transcribed_text,
            str(current_user.id),
            context_id or str(current_user.id),
            scene_id
        )
        
        # Prepare MCP request
        mcp_request = {
            "action": "update_scene",
            "user_id": str(current_user.id),
            "data": {
                "scene_id": scene_id,
                "session_id": session_id,
                "context_id": context_id or str(current_user.id),
                "text_feedback": transcribed_text,
                "transcription_confidence": confidence,
                "priority": priority,
                "options": parsed_options,
                "feedback_type": "voice"
            }
        }
        
        # Send request to MCP server
        response = await mcp_server.handle_request(mcp_request)
        
        if not response.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.message or "Failed to process voice feedback"
            )
        
        # Parse and return the response
        return FeedbackResponse(
            request_id=response.request_id,
            scene_id=scene_id,
            status="processing" if response.data.get("status") == "processing" else "completed",
            scene_updates=response.data.get("scene_updates"),
            message=f"Processed voice feedback: '{transcribed_text}'",
            actions=response.data.get("actions", []),
            updated_scene_url=response.data.get("scene_url"),
            update_preview=response.data.get("preview_image")
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing voice feedback: {str(e)}"
        )

# Background tasks
async def process_text_feedback(
    text: str,
    user_id: str,
    context_id: str,
    scene_id: str
):
    """
    Process text feedback through sentiment analysis and context updates
    """
    try:
        # 1. Send to sentiment analysis
        sentiment_request = {
            "action": "analyze_sentiment",
            "user_id": user_id,
            "data": {
                "text": text,
                "context_id": context_id,
                "scene_id": scene_id
            }
        }
        
        await mcp_server.handle_request(sentiment_request)
        
        # 2. Update conversation context
        context_request = {
            "action": "update_context",
            "user_id": user_id,
            "data": {
                "context_id": context_id,
                "context": {
                    "last_feedback": text,
                    "last_feedback_timestamp": datetime.utcnow().isoformat(),
                    "current_scene_id": scene_id,
                    "conversation_turn": {
                        "role": "user",
                        "content": text,
                        "type": "feedback"
                    }
                }
            }
        }
        
        await mcp_server.handle_request(context_request)
        
    except Exception as e:
        # Log but don't fail the request
        print(f"Error processing feedback in background: {e}")

# Update MCP server to handle scene updates
async def handle_update_scene(request):
    """
    Extend MCP server to handle scene update requests
    (This function should be added to the MCP server class)
    """
    try:
        scene_id = request.data.get("scene_id")
        text_feedback = request.data.get("text_feedback")
        
        # Send to text-to-scene agent for updates
        message = {
            "request_id": request.request_id,
            "user_id": request.user_id,
            "scene_id": scene_id,
            "text": text_feedback,
            "context_id": request.data.get("context_id", request.user_id),
            "element_interactions": request.data.get("element_interactions", []),
            "environment_changes": request.data.get("environment_changes", {}),
            "options": request.data.get("options", {}),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # This would be implemented in the actual MCP server
        # Here we're just returning a mock response
        return {
            "request_id": request.request_id,
            "success": True,
            "message": "Scene update request submitted",
            "data": {"status": "processing"}
        }
    except Exception as e:
        return {
            "request_id": request.request_id,
            "success": False,
            "message": f"Error processing scene update: {str(e)}",
            "data": {}
        }
