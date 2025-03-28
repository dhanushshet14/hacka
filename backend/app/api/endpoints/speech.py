from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Body, File, UploadFile, Form, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
import base64
import io
from loguru import logger

from app.core.config import settings
from app.api.deps import get_current_user
from app.schemas.users import User
from app.integrations.speech_processing import generate_speech, transcribe_audio

router = APIRouter()

class TextToSpeechRequest(BaseModel):
    """Request model for text-to-speech conversion"""
    text: str
    provider: Optional[str] = None
    voice: Optional[str] = None
    output_format: str = "mp3"
    return_base64: bool = False

class TextToSpeechResponse(BaseModel):
    """Response model for text-to-speech conversion with base64 data"""
    audio_data: str
    format: str
    success: bool = True

@router.post("/text-to-speech", response_model=TextToSpeechResponse)
async def text_to_speech(
    request: TextToSpeechRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Convert text to speech using the configured TTS provider
    
    This endpoint accepts text and returns speech audio data in base64 format.
    """
    try:
        # Always request base64 for API response
        audio_data = await generate_speech(
            text=request.text,
            provider=request.provider,
            voice=request.voice,
            output_format=request.output_format,
            return_base64=True
        )
        
        return TextToSpeechResponse(
            audio_data=audio_data,
            format=request.output_format
        )
    except Exception as e:
        logger.error(f"Error in text-to-speech conversion: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Text-to-speech conversion failed: {str(e)}"
        )

@router.post("/text-to-speech/stream")
async def text_to_speech_stream(
    request: TextToSpeechRequest = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Convert text to speech and stream the audio data
    
    This endpoint accepts text and returns the audio data as a streaming response,
    which can be played directly in supported browsers.
    """
    try:
        # Request binary data for streaming
        audio_data = await generate_speech(
            text=request.text,
            provider=request.provider,
            voice=request.voice,
            output_format=request.output_format,
            return_base64=False
        )
        
        # Create a streaming response
        content_type = f"audio/{request.output_format}"
        if request.output_format == "mp3":
            content_type = "audio/mpeg"
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=speech.{request.output_format}"
            }
        )
    except Exception as e:
        logger.error(f"Error in text-to-speech streaming: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Text-to-speech streaming failed: {str(e)}"
        )

class SpeechToTextResponse(BaseModel):
    """Response model for speech-to-text conversion"""
    text: str
    confidence: Optional[float] = None
    language: Optional[str] = None
    duration: Optional[float] = None
    segments: Optional[List[Dict[str, Any]]] = None
    success: bool = True

@router.post("/speech-to-text", response_model=SpeechToTextResponse)
async def speech_to_text(
    audio: UploadFile = File(...),
    provider: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Convert speech to text using the configured STT provider
    
    This endpoint accepts an audio file and returns the transcribed text.
    """
    try:
        # Read audio file
        audio_data = await audio.read()
        
        # Transcribe audio
        result = await transcribe_audio(
            audio_data=audio_data,
            provider=provider,
            language=language,
            prompt=prompt
        )
        
        # Process result
        response = SpeechToTextResponse(
            text=result.get("text", ""),
            success=True
        )
        
        # Add additional fields if available
        if "confidence" in result:
            response.confidence = result["confidence"]
        
        if "language" in result:
            response.language = result["language"]
            
        if "duration" in result:
            response.duration = result["duration"]
            
        if "segments" in result:
            response.segments = result["segments"]
        
        return response
    except Exception as e:
        logger.error(f"Error in speech-to-text conversion: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Speech-to-text conversion failed: {str(e)}"
        )

@router.post("/speech-to-text/base64", response_model=SpeechToTextResponse)
async def speech_to_text_base64(
    audio_data: str = Body(..., embed=True),
    provider: Optional[str] = Body(None),
    language: Optional[str] = Body(None),
    prompt: Optional[str] = Body(None),
    current_user: User = Depends(get_current_user)
):
    """
    Convert base64-encoded speech to text
    
    This endpoint accepts base64-encoded audio data and returns the transcribed text.
    """
    try:
        # Transcribe audio
        result = await transcribe_audio(
            audio_data=audio_data,
            provider=provider,
            is_base64=True,
            language=language,
            prompt=prompt
        )
        
        # Process result
        response = SpeechToTextResponse(
            text=result.get("text", ""),
            success=True
        )
        
        # Add additional fields if available
        if "confidence" in result:
            response.confidence = result["confidence"]
        
        if "language" in result:
            response.language = result["language"]
            
        if "duration" in result:
            response.duration = result["duration"]
            
        if "segments" in result:
            response.segments = result["segments"]
        
        return response
    except Exception as e:
        logger.error(f"Error in speech-to-text conversion: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Speech-to-text conversion failed: {str(e)}"
        ) 