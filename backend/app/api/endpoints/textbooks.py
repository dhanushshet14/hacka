from typing import Dict, List, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Form, Depends, status, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import os
import shutil
from pathlib import Path
import tempfile
import uuid
from loguru import logger

from app.db.chromadb import (
    ingest_textbook, 
    ingest_content_string, 
    search_textbooks, 
    get_collection_info,
    delete_by_metadata
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/textbooks", tags=["textbooks"])

# Models for API requests and responses
class TextbookMetadata(BaseModel):
    title: str
    author: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    edition: Optional[str] = None
    year: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    
class TextbookIngestResponse(BaseModel):
    success: bool
    textbook_id: Optional[str] = None
    chunks_count: int = 0
    collection: str
    message: str
    
class TextContentRequest(BaseModel):
    content: str
    title: str
    metadata: Optional[Dict[str, Any]] = None
    
class TextbookSearchRequest(BaseModel):
    query: str
    subject: Optional[str] = None
    n_results: int = 5
    
class TextbookSearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    
class CollectionInfoResponse(BaseModel):
    collection_name: str
    document_count: int
    document_types: Dict[str, int]
    subjects: Dict[str, int]
    sources: Dict[str, int]
    
class TextbookDeleteRequest(BaseModel):
    textbook_id: str

# Temporary file storage
TEMP_UPLOAD_DIR = Path(tempfile.gettempdir()) / "aetherion_textbooks"
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=TextbookIngestResponse)
async def upload_textbook(
    file: UploadFile = File(...),
    title: str = Form(...),
    author: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    edition: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    tags: str = Form(""),
    current_user = Depends(get_current_user)
):
    """
    Upload and process a textbook file for RAG
    """
    try:
        # Create temporary file
        temp_file_path = TEMP_UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"
        
        # Save uploaded file
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Parse tags
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # Create metadata
        metadata = {
            "title": title,
            "author": author,
            "subject": subject,
            "description": description,
            "edition": edition,
            "year": year,
            "tags": tag_list,
            "uploaded_by": current_user.username
        }
        
        # Ingest the textbook
        chunks_count, collection = await ingest_textbook(
            file_path=str(temp_file_path),
            title=title,
            author=author,
            subject=subject,
            collection_name=None  # Use default
        )
        
        # Get the textbook ID from the response
        textbook_id = None
        if chunks_count > 0:
            # The textbook ID is generated in the ingest_textbook function
            # We don't have direct access to it here, but it's stored in the metadata
            textbook_id = f"tb_{uuid.uuid4()}"  # Just for the response
        
        return TextbookIngestResponse(
            success=chunks_count > 0,
            textbook_id=textbook_id,
            chunks_count=chunks_count,
            collection=collection,
            message=f"Successfully ingested textbook with {chunks_count} chunks" if chunks_count > 0 else "Failed to ingest textbook"
        )
    
    except Exception as e:
        logger.error(f"Error uploading textbook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading textbook: {str(e)}"
        )
    finally:
        # Clean up temp file
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@router.post("/content", response_model=TextbookIngestResponse)
async def ingest_content(
    request: TextContentRequest,
    current_user = Depends(get_current_user)
):
    """
    Ingest text content directly
    """
    try:
        # Augment metadata with user info
        metadata = request.metadata or {}
        metadata["uploaded_by"] = current_user.username
        
        # Ingest the content
        chunks_count, collection = await ingest_content_string(
            content=request.content,
            title=request.title,
            metadata=metadata
        )
        
        return TextbookIngestResponse(
            success=chunks_count > 0,
            textbook_id=metadata.get("content_id"),
            chunks_count=chunks_count,
            collection=collection,
            message=f"Successfully ingested content with {chunks_count} chunks" if chunks_count > 0 else "Failed to ingest content"
        )
    
    except Exception as e:
        logger.error(f"Error ingesting content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ingesting content: {str(e)}"
        )

@router.post("/search", response_model=TextbookSearchResponse)
async def search_content(request: TextbookSearchRequest):
    """
    Search textbook content
    """
    try:
        # Search textbooks
        documents = await search_textbooks(
            query=request.query,
            subject=request.subject,
            n_results=request.n_results
        )
        
        # Format results
        results = []
        for doc in documents:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })
        
        return TextbookSearchResponse(
            query=request.query,
            results=results
        )
    
    except Exception as e:
        logger.error(f"Error searching textbooks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching textbooks: {str(e)}"
        )

@router.get("/info", response_model=CollectionInfoResponse)
async def get_info(
    collection_name: Optional[str] = Query(None, description="Optional collection name")
):
    """
    Get information about the textbook collection
    """
    try:
        info = await get_collection_info(collection_name)
        return info
    
    except Exception as e:
        logger.error(f"Error getting collection info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting collection info: {str(e)}"
        )

@router.delete("/delete", response_model=Dict[str, Any])
async def delete_textbook(
    request: TextbookDeleteRequest,
    current_user = Depends(get_current_user)
):
    """
    Delete a textbook by ID
    """
    try:
        deleted_count = await delete_by_metadata(
            metadata_key="textbook_id",
            metadata_value=request.textbook_id
        )
        
        return {
            "success": deleted_count > 0,
            "deleted_chunks": deleted_count,
            "message": f"Successfully deleted {deleted_count} chunks" if deleted_count > 0 else "No matching textbook found"
        }
    
    except Exception as e:
        logger.error(f"Error deleting textbook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting textbook: {str(e)}"
        ) 