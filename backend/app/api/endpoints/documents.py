from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Body, File, UploadFile, Form, Query
from pydantic import BaseModel, Field
import base64
from loguru import logger

from app.core.config import settings
from app.api.deps import get_current_user
from app.schemas.users import User
from app.integrations.document_processing import process_document_file, process_base64_document, process_text
from app.db.chromadb import ingest_documents, search_documents, get_chroma_client

router = APIRouter()

class DocumentIngestionRequest(BaseModel):
    """Request model for document ingestion via base64"""
    base64_data: str
    file_name: str
    collection_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    chunk_size: int = 1000
    chunk_overlap: int = 200

class TextIngestionRequest(BaseModel):
    """Request model for text ingestion"""
    text: str
    collection_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    chunk_size: int = 1000
    chunk_overlap: int = 200

class DocumentResponse(BaseModel):
    """Response model for document operations"""
    success: bool
    message: str
    document_ids: Optional[List[str]] = None
    count: Optional[int] = None

@router.post("/ingest", response_model=DocumentResponse)
async def ingest_document(
    file: UploadFile = File(...),
    collection_name: Optional[str] = Form(None),
    metadata_json: Optional[str] = Form(None),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    current_user: User = Depends(get_current_user)
):
    """
    Ingest a document file into ChromaDB
    
    This endpoint accepts a document file and ingests it into the specified ChromaDB collection.
    The document is processed, chunked, and stored for retrieval.
    """
    try:
        # Read file contents
        file_contents = await file.read()
        
        # Create temporary file
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            temp_file.write(file_contents)
            temp_file_path = temp_file.name
        
        try:
            # Parse metadata if provided
            metadata = {}
            if metadata_json:
                import json
                metadata = json.loads(metadata_json)
            
            # Add user ID to metadata
            metadata["user_id"] = str(current_user.id)
            metadata["file_name"] = file.filename
            
            # Process document
            documents = await process_document_file(
                file_path=temp_file_path,
                metadata=metadata,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            # Ingest documents
            result = await ingest_documents(
                documents=documents,
                collection_name=collection_name or settings.CHROMADB_COLLECTION_NAME
            )
            
            return DocumentResponse(
                success=True,
                message=f"Successfully ingested {len(documents)} document chunks",
                document_ids=result.get("ids"),
                count=len(documents)
            )
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    except Exception as e:
        logger.error(f"Error ingesting document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Document ingestion failed: {str(e)}"
        )

@router.post("/ingest/base64", response_model=DocumentResponse)
async def ingest_base64_document(
    request: DocumentIngestionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Ingest a base64-encoded document into ChromaDB
    
    This endpoint accepts a base64-encoded document and ingests it into the specified ChromaDB collection.
    The document is processed, chunked, and stored for retrieval.
    """
    try:
        # Add user ID to metadata
        metadata = request.metadata or {}
        metadata["user_id"] = str(current_user.id)
        metadata["file_name"] = request.file_name
        
        # Process document
        documents = await process_base64_document(
            base64_data=request.base64_data,
            file_name=request.file_name,
            metadata=metadata,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )
        
        # Ingest documents
        result = await ingest_documents(
            documents=documents,
            collection_name=request.collection_name or settings.CHROMADB_COLLECTION_NAME
        )
        
        return DocumentResponse(
            success=True,
            message=f"Successfully ingested {len(documents)} document chunks",
            document_ids=result.get("ids"),
            count=len(documents)
        )
    except Exception as e:
        logger.error(f"Error ingesting base64 document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Document ingestion failed: {str(e)}"
        )

@router.post("/ingest/text", response_model=DocumentResponse)
async def ingest_text(
    request: TextIngestionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Ingest text content into ChromaDB
    
    This endpoint accepts text content and ingests it into the specified ChromaDB collection.
    The text is processed, chunked, and stored for retrieval.
    """
    try:
        # Add user ID to metadata
        metadata = request.metadata or {}
        metadata["user_id"] = str(current_user.id)
        metadata["source"] = "text"
        
        # Process text
        documents = await process_text(
            text=request.text,
            metadata=metadata,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )
        
        # Ingest documents
        result = await ingest_documents(
            documents=documents,
            collection_name=request.collection_name or settings.CHROMADB_COLLECTION_NAME
        )
        
        return DocumentResponse(
            success=True,
            message=f"Successfully ingested {len(documents)} text chunks",
            document_ids=result.get("ids"),
            count=len(documents)
        )
    except Exception as e:
        logger.error(f"Error ingesting text: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Text ingestion failed: {str(e)}"
        )

class DocumentSearchRequest(BaseModel):
    """Request model for document search"""
    query: str
    collection_name: Optional[str] = None
    filter: Optional[Dict[str, Any]] = None
    n_results: int = 5
    include_metadata: bool = True

class DocumentSearchResponse(BaseModel):
    """Response model for document search"""
    success: bool
    documents: List[Dict[str, Any]]
    count: int

@router.post("/search", response_model=DocumentSearchResponse)
async def search_document_store(
    request: DocumentSearchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Search for documents in ChromaDB
    
    This endpoint allows searching for documents based on a query string.
    Returns the most relevant documents with their content and metadata.
    """
    try:
        # Add user filter if not explicitly provided
        if not request.filter:
            request.filter = {"user_id": str(current_user.id)}
        else:
            # Ensure user can only access their own documents
            request.filter["user_id"] = str(current_user.id)
        
        # Search documents
        results = await search_documents(
            query=request.query,
            collection_name=request.collection_name or settings.CHROMADB_COLLECTION_NAME,
            filter=request.filter,
            n_results=request.n_results,
            include_metadata=request.include_metadata
        )
        
        # Format results
        documents = []
        for i, (doc_id, doc_content, doc_metadata, doc_distance) in enumerate(zip(
            results.get("ids", []),
            results.get("documents", []),
            results.get("metadatas", []),
            results.get("distances", [])
        )):
            documents.append({
                "id": doc_id,
                "content": doc_content,
                "metadata": doc_metadata,
                "score": 1.0 - doc_distance,  # Convert distance to score
                "rank": i + 1
            })
        
        return DocumentSearchResponse(
            success=True,
            documents=documents,
            count=len(documents)
        )
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Document search failed: {str(e)}"
        ) 