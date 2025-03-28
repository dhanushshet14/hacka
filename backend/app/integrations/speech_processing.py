from typing import Optional, Dict, Any, List, Union
import os
import asyncio
import httpx
import base64
from loguru import logger
from pathlib import Path
import tempfile
import json

from app.core.config import settings

# --------------------------
# Text-to-Speech Integration
# --------------------------

async def tts_elevenlabs(
    text: str, 
    voice_id: str = "21m00Tcm4TlvDq8ikWAM", 
    model_id: str = "eleven_monolingual_v1",
    output_format: str = "mp3"
) -> bytes:
    """
    Convert text to speech using ElevenLabs API
    
    Args:
        text: The text to convert to speech
        voice_id: The voice ID to use (default: Rachel voice)
        model_id: The model ID to use
        output_format: The output format (mp3, pcm, wav, etc.)
        
    Returns:
        bytes: The audio data
    """
    if not settings.ELEVENLABS_API_KEY:
        logger.error("ElevenLabs API key not set")
        raise ValueError("ElevenLabs API key is required")
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "application/json",
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"ElevenLabs TTS error: {response.status_code} - {response.text}")
                raise Exception(f"ElevenLabs TTS error: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error in TTS with ElevenLabs: {str(e)}")
        raise

async def tts_openai(
    text: str,
    voice: str = "alloy",
    model: str = "tts-1",
    output_format: str = "mp3"
) -> bytes:
    """
    Convert text to speech using OpenAI TTS API
    
    Args:
        text: The text to convert to speech
        voice: The voice to use (alloy, echo, fable, onyx, nova, shimmer)
        model: The model to use (tts-1, tts-1-hd)
        output_format: The output format (mp3 or opus)
        
    Returns:
        bytes: The audio data
    """
    if not settings.OPENAI_API_KEY:
        logger.error("OpenAI API key not set")
        raise ValueError("OpenAI API key is required")
        
    url = "https://api.openai.com/v1/audio/speech"
    
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "input": text,
        "voice": voice,
        "response_format": output_format
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"OpenAI TTS error: {response.status_code} - {response.text}")
                raise Exception(f"OpenAI TTS error: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error in TTS with OpenAI: {str(e)}")
        raise

async def generate_speech(
    text: str,
    provider: Optional[str] = None,
    voice: Optional[str] = None,
    output_format: str = "mp3",
    return_base64: bool = False
) -> Union[bytes, str]:
    """
    Generate speech from text using the configured provider
    
    Args:
        text: The text to convert to speech
        provider: The provider to use (elevenlabs, openai)
        voice: The voice to use (provider-specific)
        output_format: The output format
        return_base64: Whether to return base64-encoded data
        
    Returns:
        bytes or str: The audio data or base64-encoded audio data
    """
    # Use configured provider if not specified
    if not provider:
        provider = settings.TTS_PROVIDER.lower()
    
    # Generate speech based on provider
    audio_data = None
    if provider == "elevenlabs":
        voice_id = voice or "21m00Tcm4TlvDq8ikWAM"  # Default to Rachel voice
        audio_data = await tts_elevenlabs(text, voice_id=voice_id, output_format=output_format)
    elif provider == "openai":
        voice_name = voice or "alloy"
        audio_data = await tts_openai(text, voice=voice_name, output_format=output_format)
    else:
        raise ValueError(f"Unsupported TTS provider: {provider}")
    
    # Return data in requested format
    if return_base64:
        return base64.b64encode(audio_data).decode("utf-8")
    else:
        return audio_data

# --------------------------
# Speech-to-Text Integration
# --------------------------

async def stt_openai(
    audio_data: bytes,
    model: str = "whisper-1",
    language: Optional[str] = None,
    prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convert speech to text using OpenAI Whisper API
    
    Args:
        audio_data: The audio data as bytes
        model: The model to use
        language: The language code (optional)
        prompt: Optional prompt to guide the transcription
        
    Returns:
        dict: The transcription result
    """
    if not settings.OPENAI_API_KEY:
        logger.error("OpenAI API key not set")
        raise ValueError("OpenAI API key is required")
    
    url = "https://api.openai.com/v1/audio/transcriptions"
    
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
    }
    
    # Create temporary file for the audio
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
        temp_file.write(audio_data)
        temp_file_path = temp_file.name
    
    try:
        # Prepare form data
        form_data = {
            "file": open(temp_file_path, "rb"),
            "model": model,
        }
        
        if language:
            form_data["language"] = language
            
        if prompt:
            form_data["prompt"] = prompt
        
        # Send request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                headers=headers,
                files={"file": (os.path.basename(temp_file_path), open(temp_file_path, "rb"), "audio/mpeg")},
                data=form_data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"OpenAI STT error: {response.status_code} - {response.text}")
                raise Exception(f"OpenAI STT error: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error in STT with OpenAI: {str(e)}")
        raise
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

async def transcribe_audio(
    audio_data: Union[bytes, str],
    provider: Optional[str] = None,
    is_base64: bool = False,
    language: Optional[str] = None,
    prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transcribe audio data to text using the configured provider
    
    Args:
        audio_data: The audio data as bytes or base64-encoded string
        provider: The provider to use
        is_base64: Whether the audio_data is base64-encoded
        language: Optional language code
        prompt: Optional prompt to guide transcription
        
    Returns:
        dict: The transcription result
    """
    # Use configured provider if not specified
    if not provider:
        provider = settings.STT_PROVIDER.lower()
    
    # Decode base64 if needed
    if is_base64 and isinstance(audio_data, str):
        audio_data = base64.b64decode(audio_data)
    
    # Transcribe based on provider
    if provider == "openai":
        result = await stt_openai(audio_data, language=language, prompt=prompt)
        return result
    else:
        raise ValueError(f"Unsupported STT provider: {provider}") 