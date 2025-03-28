from typing import Dict, Any, Optional, List
from langchain_community.llms import Ollama
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.schema.output_parser import StrOutputParser
from pydantic import BaseModel
import httpx
from loguru import logger

from app.core.config import settings

class OllamaRequest(BaseModel):
    """Ollama API request model"""
    model: str
    prompt: str
    system: Optional[str] = None
    template: Optional[str] = None
    context: Optional[List[int]] = None
    options: Optional[Dict[str, Any]] = None
    stream: bool = False
    raw: bool = False

class OllamaResponse(BaseModel):
    """Ollama API response model"""
    model: str
    created_at: str
    response: str
    context: Optional[List[int]] = None
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None

def get_ollama_llm(
    model_name: Optional[str] = None,
    temperature: float = 0.7,
    streaming: bool = False
):
    """
    Get an Ollama LLM for use with LangChain
    
    Args:
        model_name: Model to use (default from config)
        temperature: Temperature for generation
        streaming: Whether to stream the output
        
    Returns:
        LangChain Ollama LLM
    """
    model = model_name or settings.OLLAMA_MODEL
    
    # Set up callbacks for streaming if needed
    callback_manager = None
    if streaming:
        callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
    
    ollama_llm = Ollama(
        base_url=settings.OLLAMA_BASE_URL,
        model=model,
        callback_manager=callback_manager,
        temperature=temperature
    )
    
    return ollama_llm

async def generate_text(
    prompt: str,
    system_prompt: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    stop_sequences: Optional[List[str]] = None
) -> str:
    """
    Generate text directly using the Ollama API
    
    Args:
        prompt: The prompt to generate text from
        system_prompt: Optional system prompt
        model_name: Model to use (default from config)
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        stop_sequences: Optional stop sequences
        
    Returns:
        Generated text
    """
    model = model_name or settings.OLLAMA_MODEL
    base_url = settings.OLLAMA_BASE_URL
    
    try:
        # Prepare the request
        request_data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        # Add system prompt if provided
        if system_prompt:
            request_data["system"] = system_prompt
            
        # Add stop sequences if provided
        if stop_sequences:
            request_data["options"]["stop"] = stop_sequences
            
        # Make the API call
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/api/generate",
                json=request_data,
                timeout=60.0
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return f"Error generating text: {response.status_code}"
                
            response_data = response.json()
            return response_data.get("response", "")
            
    except Exception as e:
        logger.error(f"Error in Ollama text generation: {e}")
        return f"Error: {str(e)}"

async def generate_embeddings(
    text: str,
    model_name: Optional[str] = None
) -> List[float]:
    """
    Generate embeddings using the Ollama API
    
    Args:
        text: The text to embed
        model_name: Model to use (default from config)
        
    Returns:
        List of embedding values
    """
    model = model_name or settings.OLLAMA_MODEL
    base_url = settings.OLLAMA_BASE_URL
    
    try:
        # Prepare the request
        request_data = {
            "model": model,
            "prompt": text
        }
        
        # Make the API call
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/api/embeddings",
                json=request_data,
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return []
                
            response_data = response.json()
            return response_data.get("embedding", [])
            
    except Exception as e:
        logger.error(f"Error in Ollama embedding generation: {e}")
        return []
