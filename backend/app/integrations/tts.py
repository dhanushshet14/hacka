from typing import Union, Optional, Dict, Any
from app.integrations.speech_processing import (
    generate_speech,
    tts_elevenlabs,
    tts_openai
)

__all__ = ["convert_text_to_speech", "tts_elevenlabs", "tts_openai", "generate_speech"]

async def convert_text_to_speech(
    text: str,
    provider: Optional[str] = None,
    voice: Optional[str] = None,
    output_format: str = "mp3",
    return_base64: bool = False
) -> Union[bytes, str]:
    """
    Convert text to speech using the configured provider
    
    Args:
        text: The text to convert to speech
        provider: The provider to use (elevenlabs, openai)
        voice: The voice to use (provider-specific)
        output_format: The output format (mp3, wav, etc.)
        return_base64: Whether to return base64-encoded data
        
    Returns:
        bytes or str: The audio data or base64-encoded audio data
    """
    return await generate_speech(
        text=text,
        provider=provider,
        voice=voice,
        output_format=output_format,
        return_base64=return_base64
    )
