from typing import Dict, List, Any, Optional, Tuple, Union
import os
from pathlib import Path
import tempfile
import base64
from loguru import logger

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader, UnstructuredMarkdownLoader
from langchain.schema import Document

class DocumentProcessor:
    """Document processor for extracting and chunking documents"""
    
    @staticmethod
    def get_document_loader(file_path: str):
        """
        Get the appropriate document loader based on file extension
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Document loader instance
        """
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension == '.pdf':
            return PyPDFLoader(file_path)
        elif file_extension == '.txt':
            return TextLoader(file_path)
        elif file_extension in ['.docx', '.doc']:
            return Docx2txtLoader(file_path)
        elif file_extension in ['.md', '.markdown']:
            return UnstructuredMarkdownLoader(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {file_extension}")
    
    @staticmethod
    def get_text_splitter(
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None
    ):
        """
        Get a text splitter for chunking documents
        
        Args:
            chunk_size: Maximum size of chunks
            chunk_overlap: Overlap between chunks
            separators: Custom separators for chunking
            
        Returns:
            Text splitter instance
        """
        default_separators = ["\n\n", "\n", ". ", " ", ""]
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators or default_separators,
        )
    
    @staticmethod
    async def process_document(
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> List[Document]:
        """
        Process a document file and return chunked documents
        
        Args:
            file_path: Path to the document file
            metadata: Additional metadata to add to documents
            chunk_size: Maximum size of chunks
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of chunked documents
        """
        try:
            # Get appropriate loader
            loader = DocumentProcessor.get_document_loader(file_path)
            
            # Load documents
            docs = loader.load()
            
            # Add metadata if provided
            if metadata:
                for doc in docs:
                    doc.metadata.update(metadata)
            
            # Get text splitter
            text_splitter = DocumentProcessor.get_text_splitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            # Split documents
            split_docs = text_splitter.split_documents(docs)
            
            return split_docs
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            raise
    
    @staticmethod
    async def process_base64_document(
        base64_data: str,
        file_name: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> List[Document]:
        """
        Process a base64-encoded document and return chunked documents
        
        Args:
            base64_data: Base64-encoded document data
            file_name: Original filename with extension
            metadata: Additional metadata to add to documents
            chunk_size: Maximum size of chunks
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of chunked documents
        """
        try:
            # Decode base64 data
            file_data = base64.b64decode(base64_data)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_name).suffix) as temp_file:
                temp_file.write(file_data)
                temp_file_path = temp_file.name
            
            try:
                # Process the temporary file
                return await DocumentProcessor.process_document(
                    file_path=temp_file_path,
                    metadata=metadata,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
        except Exception as e:
            logger.error(f"Error processing base64 document: {str(e)}")
            raise
    
    @staticmethod
    async def process_text(
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> List[Document]:
        """
        Process text and return chunked documents
        
        Args:
            text: Text content to process
            metadata: Additional metadata to add to documents
            chunk_size: Maximum size of chunks
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of chunked documents
        """
        try:
            # Create document from text
            docs = [Document(page_content=text, metadata=metadata or {})]
            
            # Get text splitter
            text_splitter = DocumentProcessor.get_text_splitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            # Split documents
            split_docs = text_splitter.split_documents(docs)
            
            return split_docs
        except Exception as e:
            logger.error(f"Error processing text: {str(e)}")
            raise

async def process_document_file(
    file_path: str,
    metadata: Optional[Dict[str, Any]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Document]:
    """
    Process a document file and return chunked documents
    
    Args:
        file_path: Path to the document file
        metadata: Additional metadata to add to documents
        chunk_size: Maximum size of chunks
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of chunked documents
    """
    return await DocumentProcessor.process_document(
        file_path=file_path,
        metadata=metadata,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

async def process_base64_document(
    base64_data: str,
    file_name: str,
    metadata: Optional[Dict[str, Any]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Document]:
    """
    Process a base64-encoded document and return chunked documents
    
    Args:
        base64_data: Base64-encoded document data
        file_name: Original filename with extension
        metadata: Additional metadata to add to documents
        chunk_size: Maximum size of chunks
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of chunked documents
    """
    return await DocumentProcessor.process_base64_document(
        base64_data=base64_data,
        file_name=file_name,
        metadata=metadata,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

async def process_text(
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Document]:
    """
    Process text and return chunked documents
    
    Args:
        text: Text content to process
        metadata: Additional metadata to add to documents
        chunk_size: Maximum size of chunks
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of chunked documents
    """
    return await DocumentProcessor.process_text(
        text=text,
        metadata=metadata,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    ) 