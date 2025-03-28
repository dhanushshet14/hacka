import os
from typing import Dict, List, Any, Optional, Tuple, Union
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredMarkdownLoader
)
import chromadb
from chromadb.config import Settings as ChromaSettings
from loguru import logger
import uuid
import json

from app.core.config import settings

# Embedding model
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def get_chroma_client():
    """Get the ChromaDB client"""
    try:
        client = chromadb.HttpClient(
            host=settings.CHROMADB_HOST,
            port=settings.CHROMADB_PORT
        )
        # Check if client is working
        client.heartbeat()
        return client
    except Exception:
        # Fallback to persistent client
        logger.info("ChromaDB HTTP client not available, falling back to persistent client")
        client = chromadb.PersistentClient(
            path=settings.CHROMADB_PERSIST_DIR
        )
        return client

def get_embeddings_model():
    """Get the embedding model for document processing"""
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

def get_vectorstore(collection_name: Optional[str] = None):
    """Get a Chroma vectorstore"""
    embeddings = get_embeddings_model()
    collection = collection_name or settings.CHROMADB_COLLECTION_NAME
    
    return Chroma(
        collection_name=collection,
        embedding_function=embeddings,
        client=get_chroma_client(),
    )

def get_text_splitter(chunk_size: int = 1000, chunk_overlap: int = 100):
    """Get a text splitter for documents"""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )

def get_document_loader(file_path: str):
    """Get the appropriate document loader based on file extension"""
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.pdf':
        return PyPDFLoader(file_path)
    elif file_extension in ['.docx', '.doc']:
        return Docx2txtLoader(file_path)
    elif file_extension in ['.md', '.markdown']:
        return UnstructuredMarkdownLoader(file_path)
    else:  # Default to text loader
        return TextLoader(file_path)

async def ingest_documents(
    file_paths: List[str],
    collection_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 100
) -> Tuple[int, str]:
    """
    Ingest documents into ChromaDB for RAG
    
    Args:
        file_paths: List of file paths to process
        collection_name: Optional custom collection name
        metadata: Optional metadata to attach to documents
        chunk_size: Size of document chunks
        chunk_overlap: Overlap between chunks
        
    Returns:
        Tuple of (number of chunks ingested, collection name)
    """
    try:
        # Get components
        text_splitter = get_text_splitter(chunk_size, chunk_overlap)
        embeddings = get_embeddings_model()
        collection = collection_name or settings.CHROMADB_COLLECTION_NAME
        
        # Process documents
        all_chunks = []
        for file_path in file_paths:
            try:
                loader = get_document_loader(file_path)
                documents = loader.load()
                
                # Add file metadata
                file_metadata = {
                    "source": os.path.basename(file_path),
                    "file_path": file_path,
                    "doc_type": "textbook",
                    "ingestion_id": str(uuid.uuid4())
                }
                
                # Add custom metadata if provided
                if metadata:
                    file_metadata.update(metadata)
                
                # Apply metadata to documents
                for doc in documents:
                    doc.metadata.update(file_metadata)
                
                # Split into chunks
                chunks = text_splitter.split_documents(documents)
                all_chunks.extend(chunks)
                
                logger.info(f"Processed {file_path} into {len(chunks)} chunks")
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
        
        # Store in ChromaDB
        vectorstore = Chroma.from_documents(
            documents=all_chunks,
            embedding=embeddings,
            collection_name=collection,
            client=get_chroma_client(),
        )
        
        logger.info(f"Ingested {len(all_chunks)} chunks into collection {collection}")
        return len(all_chunks), collection
    except Exception as e:
        logger.error(f"Error in document ingestion: {e}")
        raise

async def ingest_textbook(
    file_path: str,
    title: str,
    author: Optional[str] = None,
    subject: Optional[str] = None,
    collection_name: Optional[str] = None,
    chunk_size: int = 800,
    chunk_overlap: int = 150
) -> Tuple[int, str]:
    """
    Specifically ingest a textbook with enriched metadata
    
    Args:
        file_path: Path to the textbook file
        title: Textbook title
        author: Textbook author(s)
        subject: Subject area
        collection_name: Optional custom collection name
        chunk_size: Size of document chunks
        chunk_overlap: Overlap between chunks
        
    Returns:
        Tuple of (number of chunks ingested, collection name)
    """
    textbook_metadata = {
        "doc_type": "textbook",
        "title": title,
        "author": author,
        "subject": subject,
        "textbook_id": str(uuid.uuid4())
    }
    
    return await ingest_documents(
        file_paths=[file_path],
        collection_name=collection_name,
        metadata=textbook_metadata,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

async def ingest_content_string(
    content: str,
    title: str,
    metadata: Optional[Dict[str, Any]] = None,
    collection_name: Optional[str] = None,
    chunk_size: int = 800,
    chunk_overlap: int = 150
) -> Tuple[int, str]:
    """
    Ingest content directly from a string
    
    Args:
        content: Text content to ingest
        title: Title for the content
        metadata: Optional metadata
        collection_name: Optional custom collection name
        chunk_size: Size of document chunks
        chunk_overlap: Overlap between chunks
        
    Returns:
        Tuple of (number of chunks ingested, collection name)
    """
    try:
        # Get components
        text_splitter = get_text_splitter(chunk_size, chunk_overlap)
        embeddings = get_embeddings_model()
        collection = collection_name or settings.CHROMADB_COLLECTION_NAME
        
        # Create document
        doc = Document(
            page_content=content,
            metadata={
                "source": "string_content",
                "title": title,
                "doc_type": "text_content",
                "content_id": str(uuid.uuid4())
            }
        )
        
        # Add custom metadata if provided
        if metadata:
            doc.metadata.update(metadata)
        
        # Split into chunks
        chunks = text_splitter.split_documents([doc])
        
        # Store in ChromaDB
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection_name=collection,
            client=get_chroma_client(),
        )
        
        logger.info(f"Ingested content '{title}' as {len(chunks)} chunks into collection {collection}")
        return len(chunks), collection
    except Exception as e:
        logger.error(f"Error in string content ingestion: {e}")
        raise

async def search_documents(
    query: str,
    collection_name: Optional[str] = None,
    n_results: int = 5,
    filter_metadata: Optional[Dict[str, Any]] = None
) -> List[Document]:
    """
    Search for documents in ChromaDB
    
    Args:
        query: Search query string
        collection_name: Optional collection name
        n_results: Number of results to return
        filter_metadata: Optional filter on document metadata
        
    Returns:
        List of matching documents
    """
    try:
        vectorstore = get_vectorstore(collection_name)
        
        # Perform similarity search
        documents = vectorstore.similarity_search(
            query=query,
            k=n_results,
            filter=filter_metadata
        )
        
        return documents
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return []

async def search_textbooks(
    query: str,
    subject: Optional[str] = None,
    n_results: int = 5
) -> List[Document]:
    """
    Search specifically for textbook content
    
    Args:
        query: Search query
        subject: Optional subject filter
        n_results: Number of results
        
    Returns:
        List of relevant textbook chunks
    """
    filter_dict = {"doc_type": "textbook"}
    if subject:
        filter_dict["subject"] = subject
        
    return await search_documents(
        query=query,
        filter_metadata=filter_dict,
        n_results=n_results
    )

async def get_retriever(
    collection_name: Optional[str] = None,
    search_type: str = "similarity",
    search_kwargs: Optional[Dict[str, Any]] = None,
    filter_metadata: Optional[Dict[str, Any]] = None
):
    """
    Get a retriever for RAG applications
    
    Args:
        collection_name: Optional collection name
        search_type: Type of search (similarity, mmr, etc.)
        search_kwargs: Arguments for the search
        filter_metadata: Filter for document metadata
        
    Returns:
        A LangChain retriever
    """
    vectorstore = get_vectorstore(collection_name)
    kwargs = search_kwargs or {"k": 4}
    
    # Add filter if provided
    if filter_metadata:
        kwargs["filter"] = filter_metadata
    
    return vectorstore.as_retriever(
        search_type=search_type,
        search_kwargs=kwargs
    )

async def get_textbook_retriever(
    subject: Optional[str] = None,
    search_type: str = "mmr",
    k: int = 5
):
    """
    Get a retriever specifically configured for textbooks
    
    Args:
        subject: Optional subject filter
        search_type: Type of search
        k: Number of results
        
    Returns:
        A LangChain retriever configured for textbooks
    """
    filter_dict = {"doc_type": "textbook"}
    if subject:
        filter_dict["subject"] = subject
        
    return await get_retriever(
        search_type=search_type,
        search_kwargs={"k": k, "fetch_k": k*3},
        filter_metadata=filter_dict
    )

async def get_collection_info(collection_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get information about a ChromaDB collection
    
    Args:
        collection_name: Collection name
        
    Returns:
        Dictionary with collection information
    """
    try:
        collection = collection_name or settings.CHROMADB_COLLECTION_NAME
        client = get_chroma_client()
        
        # Get collection
        chroma_collection = client.get_collection(collection)
        count = chroma_collection.count()
        
        # Get metadata stats
        metadata_query = chroma_collection.get(
            limit=min(count, 1000),
            include=["metadatas"]
        )
        
        metadatas = metadata_query.get("metadatas", [])
        doc_types = {}
        subjects = {}
        sources = {}
        
        for meta in metadatas:
            if not meta:
                continue
                
            # Count document types
            doc_type = meta.get("doc_type", "unknown")
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
            # Count subjects
            subject = meta.get("subject")
            if subject:
                subjects[subject] = subjects.get(subject, 0) + 1
                
            # Count sources
            source = meta.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
        
        return {
            "collection_name": collection,
            "document_count": count,
            "document_types": doc_types,
            "subjects": subjects,
            "sources": sources
        }
    except Exception as e:
        logger.error(f"Error getting collection info: {e}")
        return {
            "collection_name": collection_name,
            "error": str(e)
        }

async def delete_by_metadata(
    metadata_key: str,
    metadata_value: Any,
    collection_name: Optional[str] = None
) -> int:
    """
    Delete documents matching a metadata filter
    
    Args:
        metadata_key: Metadata key to match
        metadata_value: Value to match
        collection_name: Optional collection name
        
    Returns:
        Number of documents deleted
    """
    try:
        collection = collection_name or settings.CHROMADB_COLLECTION_NAME
        client = get_chroma_client()
        
        # Get collection
        chroma_collection = client.get_collection(collection)
        
        # Query for matching documents
        query_result = chroma_collection.get(
            where={metadata_key: metadata_value},
            include=["documents", "metadatas", "embeddings"]
        )
        
        # Get IDs to delete
        ids = query_result.get("ids", [])
        
        if ids:
            # Delete documents
            chroma_collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents with {metadata_key}={metadata_value}")
            return len(ids)
        
        return 0
    except Exception as e:
        logger.error(f"Error deleting documents: {e}")
        return 0

async def hybrid_search(
    query: str,
    collection_name: Optional[str] = None,
    n_results: int = 5,
    filter_metadata: Optional[Dict[str, Any]] = None
) -> List[Document]:
    """
    Perform hybrid search using both vector similarity and keywords
    
    Args:
        query: Search query
        collection_name: Optional collection name
        n_results: Number of results
        filter_metadata: Optional metadata filter
        
    Returns:
        List of relevant documents
    """
    try:
        # Get the vector store
        vectorstore = get_vectorstore(collection_name)
        
        # Get both keyword and vector results
        documents = vectorstore.similarity_search_with_relevance_scores(
            query=query,
            k=n_results,
            filter=filter_metadata
        )
        
        # Sort by relevance
        results = [doc for doc, score in sorted(documents, key=lambda x: x[1], reverse=True)]
        
        return results[:n_results]
    except Exception as e:
        logger.error(f"Error in hybrid search: {e}")
        return []
