from typing import Dict, List, Any, Optional, Union, Tuple
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, status, Body, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import base64
import json
import re
from loguru import logger

from app.integrations.langchain_integration import process_with_cot, process_with_rag
from app.integrations.langgraph_integration import create_agent_workflow, process_with_graph
from app.integrations.speech_processing import transcribe_audio
from app.db.chromadb import get_textbook_retriever, search_textbooks, hybrid_search

router = APIRouter(prefix="/text-understanding", tags=["text-understanding"])

# Models for API requests and responses
class TextUnderstandingRequest(BaseModel):
    text: str
    context_id: Optional[str] = None
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, 
        description="Options for processing like reasoning_type (cot, rag, agent), provider, etc.")

class AudioUnderstandingRequest(BaseModel):
    audio_data: str = Field(..., description="Base64 encoded audio file")
    audio_format: str = Field("mp3", description="Format of the audio file")
    context_id: Optional[str] = None
    options: Optional[Dict[str, Any]] = Field(default_factory=dict,
        description="Options for processing")

class ARSceneElement(BaseModel):
    type: str = Field(..., description="Type of element (object, character, environment)")
    name: str = Field(..., description="Name of the element")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Visual and behavioral attributes")
    position: Optional[Dict[str, float]] = None
    rotation: Optional[Dict[str, float]] = None
    scale: Optional[Dict[str, float]] = None
    relationships: Optional[List[Dict[str, Any]]] = None

class TextUnderstandingResponse(BaseModel):
    request_id: str
    text: str
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    ar_scene_elements: List[ARSceneElement] = Field(default_factory=list)
    context: Optional[Dict[str, Any]] = None
    sources: Optional[List[Dict[str, Any]]] = Field(default_factory=list, 
        description="Sources of information used for augmentation")

# LLM Prompt Templates
SCENE_EXTRACTION_PROMPT = """
You are an expert at analyzing text and extracting structured information for augmented reality scene generation.
Given the following text, identify:

1. Key entities (objects, people, locations)
2. Their visual attributes (color, size, shape, etc.)
3. Spatial relationships between entities
4. Environment features
5. Actions and movements

Format your response as structured JSON that can be directly used for AR scene generation.
Each entity should include:
- type (object, character, environment)
- name
- attributes (dictionary of visual and behavioral features)
- position (if specified or can be inferred)
- relationships (connections to other entities)

TEXT: {text}

Respond only with valid JSON containing the extracted scene elements.
"""

RAG_SCENE_EXTRACTION_PROMPT = """
You are an expert at analyzing text and extracting structured information for augmented reality scene generation.
Given the following text and relevant context from textbooks, identify:

1. Key entities (objects, people, locations)
2. Their visual attributes (color, size, shape, etc.)
3. Spatial relationships between entities
4. Environment features
5. Actions and movements

Use the retrieved context to enrich your understanding and provide more accurate and detailed descriptions.

Format your response as structured JSON that can be directly used for AR scene generation.
Each entity should include:
- type (object, character, environment)
- name
- attributes (dictionary of visual and behavioral features including detailed information from context)
- position (if specified or can be inferred)
- relationships (connections to other entities)

USER INPUT: {text}

CONTEXT FROM TEXTBOOKS:
{context}

Respond only with valid JSON containing the extracted scene elements.
"""

# Helper function to extract JSON from LLM response
def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Extract JSON from text that might contain Markdown and other content"""
    # Try to extract JSON from code blocks first
    json_match = re.search(r'```(?:json)?\n([\s\S]*?)\n```|```([\s\S]*?)```|(\{[\s\S]*\})', text)
    
    if json_match:
        json_str = json_match.group(1) or json_match.group(2) or json_match.group(3)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # Try to extract any JSON-like structure as a fallback
    try:
        # Find anything that looks like a JSON object
        potential_json = re.search(r'(\{[\s\S]*\})', text)
        if potential_json:
            return json.loads(potential_json.group(1))
    except:
        pass
    
    # Return empty structure if extraction failed
    return {
        "entities": [],
        "relationships": [],
        "ar_scene_elements": []
    }

async def retrieve_textbook_context(query: str, subject: Optional[str] = None) -> Tuple[List[Document], List[Dict[str, Any]]]:
    """
    Retrieve relevant context from textbooks
    
    Args:
        query: Search query
        subject: Optional subject filter
        
    Returns:
        Tuple of (retrieved documents, source information)
    """
    # Retrieve documents
    docs = await search_textbooks(query=query, subject=subject, n_results=5)
    
    # Format sources for citation
    sources = []
    for doc in docs:
        metadata = doc.metadata
        sources.append({
            "title": metadata.get("title", "Unknown"),
            "author": metadata.get("author", "Unknown"),
            "subject": metadata.get("subject"),
            "source": metadata.get("source", "Unknown"),
            "snippet": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
        })
    
    return docs, sources

@router.post("/process-text", response_model=TextUnderstandingResponse)
async def process_text(request: TextUnderstandingRequest):
    """
    Process text to extract structured information for AR scene generation
    """
    try:
        # Get options
        reasoning_type = request.options.get("reasoning_type", "rag")  # Default to RAG
        provider = request.options.get("provider", "ollama")
        subject = request.options.get("subject", None)
        use_rag = reasoning_type == "rag"
        
        # Initialize sources
        sources = []
        processed_text = ""
        
        # Process with appropriate reasoning approach
        if use_rag:
            # First, retrieve relevant context from textbooks
            try:
                # Get retriever for textbooks
                retriever = await get_textbook_retriever(subject=subject)
                
                # Process with RAG
                collection_name = request.options.get("collection_name", None)
                result = await process_with_rag(
                    question=request.text,
                    collection_name=collection_name,
                    system_prompt=RAG_SCENE_EXTRACTION_PROMPT,
                    provider=provider
                )
                processed_text = result
                
                # Get sources for citation
                docs, sources = await retrieve_textbook_context(request.text, subject)
                
                logger.info(f"RAG processing found {len(sources)} relevant sources")
                
            except Exception as rag_error:
                # Fallback to CoT if RAG fails
                logger.warning(f"RAG processing failed, falling back to CoT: {rag_error}")
                use_rag = False
                reasoning_type = "cot"
        
        # Fallback to non-RAG approaches if needed
        if not use_rag:
            if reasoning_type == "cot":
                result = await process_with_cot(
                    question=request.text,
                    system_prompt=SCENE_EXTRACTION_PROMPT,
                    provider=provider
                )
                processed_text = result["text"]
            elif reasoning_type == "agent":
                # Create agent workflow
                agent_flow = await create_agent_workflow(
                    system_prompt=SCENE_EXTRACTION_PROMPT,
                    tools=[],  # No specific tools needed for scene extraction
                    provider=provider
                )
                
                # Process with agent
                result = await process_with_graph(
                    app=agent_flow,
                    query=request.text
                )
                
                # Extract response
                for message in reversed(result["messages"]):
                    if message.get("role") == "assistant":
                        processed_text = message.get("content", "")
                        break
            else:
                # Default to chain of thought
                result = await process_with_cot(
                    question=request.text,
                    system_prompt=SCENE_EXTRACTION_PROMPT,
                    provider=provider
                )
                processed_text = result["text"]
        
        # Parse the JSON response
        scene_data = extract_json_from_text(processed_text)
        
        # Assemble the response
        response = TextUnderstandingResponse(
            request_id=f"req_{hash(request.text) % 10000}",
            text=request.text,
            entities=scene_data.get("entities", []),
            relationships=scene_data.get("relationships", []),
            ar_scene_elements=scene_data.get("ar_scene_elements", []),
            context={"context_id": request.context_id} if request.context_id else None,
            sources=sources
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error processing text: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error processing text: {str(e)}"
        )

@router.post("/process-audio", response_model=TextUnderstandingResponse)
async def process_audio(request: AudioUnderstandingRequest):
    """
    Process audio input to extract structured information for AR scene generation
    """
    try:
        # Transcribe audio to text
        audio_bytes = base64.b64decode(request.audio_data)
        
        # Get transcription options
        language = request.options.get("language", None)
        prompt = request.options.get("transcription_prompt", None)
        
        # Transcribe audio
        transcription_result = await transcribe_audio(
            audio_data=audio_bytes,
            provider=request.options.get("stt_provider", "openai"),
            language=language,
            prompt=prompt
        )
        
        # Extract text from transcription
        transcribed_text = transcription_result.get("text", "")
        
        if not transcribed_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not transcribe audio or empty transcription returned"
            )
        
        # Now process the transcribed text
        text_request = TextUnderstandingRequest(
            text=transcribed_text,
            context_id=request.context_id,
            options=request.options
        )
        
        # Reuse the text processing endpoint
        return await process_text(text_request)
    
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing audio: {str(e)}"
        )

@router.post("/upload-audio", response_model=TextUnderstandingResponse)
async def upload_audio(
    file: UploadFile = File(...),
    context_id: Optional[str] = None,
    reasoning_type: Optional[str] = Query("rag", description="Reasoning type: cot, rag, agent"),
    provider: Optional[str] = Query("openai", description="LLM provider"),
    language: Optional[str] = Query(None, description="Language code"),
    subject: Optional[str] = Query(None, description="Subject area for textbook retrieval")
):
    """
    Upload and process audio file for AR scene generation
    """
    try:
        # Read file contents
        audio_bytes = await file.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        
        # Create request object
        request = AudioUnderstandingRequest(
            audio_data=audio_b64,
            audio_format=file.filename.split(".")[-1] if "." in file.filename else "mp3",
            context_id=context_id,
            options={
                "reasoning_type": reasoning_type,
                "provider": provider,
                "language": language,
                "subject": subject
            }
        )
        
        # Process using the audio endpoint
        return await process_audio(request)
    
    except Exception as e:
        logger.error(f"Error processing audio file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing audio file: {str(e)}"
        ) 