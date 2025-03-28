from typing import Dict, Any, Optional, Union
from app.integrations.speech_processing import (
    transcribe_audio,
    stt_openai
)

__all__ = ["process_audio", "transcribe_audio", "stt_openai"]

async def process_audio(
    audio_file=None,
    audio_data: Optional[Union[bytes, str]] = None,
    provider: Optional[str] = None,
    language: Optional[str] = None,
    is_base64: bool = False,
    prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process audio data to extract text using the configured STT provider
    
    Args:
        audio_file: FastAPI UploadFile object, if provided through file upload
        audio_data: The audio data as bytes or base64-encoded string, if provided directly
        provider: The STT provider to use (openai)
        language: Optional language code
        is_base64: Whether the audio_data is base64-encoded
        prompt: Optional prompt to guide transcription
        
    Returns:
        dict: The transcription result with text, confidence and optional segments
    """
    # If audio_file is provided, read its content
    if audio_file and not audio_data:
        content = await audio_file.read()
        audio_data = content
    
    if not audio_data:
        raise ValueError("Either audio_file or audio_data must be provided")
    
    # Transcribe the audio
    result = await transcribe_audio(
        audio_data=audio_data,
        provider=provider,
        is_base64=is_base64,
        language=language,
        prompt=prompt
    )
    
    # Format the result
    return {
        "text": result.get("text", ""),
        "confidence": result.get("confidence", 0.0) if "confidence" in result else 0.8,
        "segments": result.get("segments", []) if "segments" in result else []
    }
