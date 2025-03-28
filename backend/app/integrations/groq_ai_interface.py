from typing import Dict, Any, Optional, List, Union
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from groq import Groq
from loguru import logger

from app.core.config import settings

# Default models
DEFAULT_CHAT_MODEL = "llama3-70b-8192"
DEFAULT_EMBEDDING_MODEL = "mixtral-8x7b-32768"

def get_groq_client():
    """Get the Groq client"""
    if not settings.GROQ_API_KEY:
        logger.error("GROQ_API_KEY is not set")
        raise ValueError("GROQ_API_KEY is not set. Please set it in your environment variables.")
    
    return Groq(api_key=settings.GROQ_API_KEY)

def get_groq_llm(
    model_name: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096
):
    """
    Get a Groq LLM for LangChain
    
    Args:
        model_name: Groq model to use
        temperature: Generation temperature
        max_tokens: Maximum tokens to generate
        
    Returns:
        LangChain Groq LLM
    """
    if not settings.GROQ_API_KEY:
        logger.error("GROQ_API_KEY is not set")
        raise ValueError("GROQ_API_KEY is not set. Please set it in your environment variables.")
    
    model = model_name or DEFAULT_CHAT_MODEL
    
    # Create the LangChain LLM
    groq_llm = ChatGroq(
        groq_api_key=settings.GROQ_API_KEY,
        model_name=model,
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    return groq_llm

async def generate_chat_completion(
    messages: List[Dict[str, str]],
    model_name: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    stream: bool = False
) -> Dict[str, Any]:
    """
    Generate chat completion using the Groq API
    
    Args:
        messages: List of messages in the format [{"role": "system|user|assistant", "content": "..."}]
        model_name: Model to use
        temperature: Generation temperature
        max_tokens: Maximum tokens to generate
        stream: Whether to stream the response
        
    Returns:
        Dictionary with the response
    """
    client = get_groq_client()
    model = model_name or DEFAULT_CHAT_MODEL
    
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )
        
        if stream:
            # Return a generator for streaming
            return {"type": "stream", "generator": completion}
        else:
            # Process the regular response
            return {
                "type": "complete",
                "content": completion.choices[0].message.content,
                "usage": {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens
                }
            }
    except Exception as e:
        logger.error(f"Error generating Groq completion: {e}")
        return {"type": "error", "error": str(e)}

async def generate_structured_output(
    prompt: str,
    output_schema: Dict[str, Any],
    system_prompt: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.2
) -> Dict[str, Any]:
    """
    Generate structured JSON output using function calling
    
    Args:
        prompt: User prompt
        output_schema: JSON schema for the output
        system_prompt: Optional system prompt
        model_name: Model to use
        temperature: Generation temperature
        
    Returns:
        Structured JSON output
    """
    client = get_groq_client()
    model = model_name or DEFAULT_CHAT_MODEL
    
    # Prepare messages
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    # Define the function for structured output
    functions = [
        {
            "name": "generate_structured_output",
            "description": "Generate structured data based on the input",
            "parameters": output_schema
        }
    ]
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            functions=functions,
            function_call={"name": "generate_structured_output"},
            temperature=temperature
        )
        
        # Extract the function call response
        function_call = response.choices[0].message.function_call
        if function_call and function_call.arguments:
            try:
                import json
                return json.loads(function_call.arguments)
            except json.JSONDecodeError:
                logger.error(f"Error parsing JSON response: {function_call.arguments}")
                return {"error": "Failed to parse JSON response"}
        else:
            return {"error": "No structured output generated"}
    except Exception as e:
        logger.error(f"Error generating structured output: {e}")
        return {"error": str(e)}

async def generate_text(
    prompt: str,
    system_prompt: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096
) -> str:
    """
    Generate text using the Groq API
    
    Args:
        prompt: The prompt to generate text from
        system_prompt: Optional system prompt
        model_name: Model to use (default from config)
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        
    Returns:
        Generated text
    """
    # Prepare messages
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    # Generate completion
    result = await generate_chat_completion(
        messages=messages,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    if result["type"] == "complete":
        return result["content"]
    else:
        return f"Error: {result.get('error', 'Unknown error')}"
