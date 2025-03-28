from typing import Dict, List, Any, Optional, Union, Callable
from langchain.schema import Document
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

from app.core.config import settings
from app.db.chromadb import get_retriever
from app.integrations.ollama_interface import get_ollama_llm
from app.integrations.groq_ai_interface import get_groq_llm

def get_llm(provider: str = "ollama"):
    """Get the appropriate LLM based on the provider"""
    if provider == "ollama":
        return get_ollama_llm()
    elif provider == "groq":
        return get_groq_llm()
    else:
        # Default to Ollama
        return get_ollama_llm()

async def create_chain_of_thought_chain(
    system_prompt: str,
    provider: str = "ollama"
):
    """Create a chain for Chain-of-Thought reasoning"""
    llm = get_llm(provider)
    
    # Template that encourages step-by-step thinking
    cot_template = """
    {system_prompt}
    
    I want you to solve this step-by-step, explaining your reasoning.
    
    User: {question}
    
    Assistant: Let me think through this step-by-step:
    """
    
    cot_prompt = PromptTemplate(
        input_variables=["system_prompt", "question"],
        template=cot_template
    )
    
    chain = LLMChain(
        llm=llm,
        prompt=cot_prompt,
        verbose=settings.LANGCHAIN_TRACING
    )
    
    return chain

async def create_rag_chain(
    collection_name: Optional[str] = None,
    system_prompt: Optional[str] = None,
    provider: str = "ollama"
):
    """Create a RAG chain for retrieval-augmented generation"""
    llm = get_llm(provider)
    retriever = await get_retriever(collection_name)
    
    # Default system prompt for RAG
    default_system_prompt = """
    You are an AI assistant that helps with answering questions.
    Use the following retrieved context to answer the user's question.
    If you don't know the answer based on the context, just say so.
    Don't make up information that's not in the context.
    """
    
    # Set up the RAG prompt
    rag_prompt_template = """
    {system_prompt}
    
    Context:
    {context}
    
    User question: {question}
    
    Answer:
    """
    
    rag_prompt = PromptTemplate(
        input_variables=["system_prompt", "context", "question"],
        template=rag_prompt_template
    )
    
    # Format the context from retrieved documents
    def format_docs(docs):
        return "\n\n".join([d.page_content for d in docs])
    
    # Build the RAG chain
    rag_chain = (
        {"context": retriever | format_docs, 
         "question": RunnablePassthrough(), 
         "system_prompt": lambda _: system_prompt or default_system_prompt}
        | rag_prompt
        | llm
    )
    
    return rag_chain

async def create_conversational_rag_chain(
    collection_name: Optional[str] = None,
    provider: str = "ollama"
):
    """Create a conversational RAG chain with memory"""
    llm = get_llm(provider)
    retriever = await get_retriever(collection_name)
    
    # Set up memory
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
    
    # Create the conversational chain
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        verbose=settings.LANGCHAIN_TRACING
    )
    
    return chain

async def process_with_cot(question: str, system_prompt: str, provider: str = "ollama"):
    """Process a question using Chain-of-Thought reasoning"""
    chain = await create_chain_of_thought_chain(
        system_prompt=system_prompt,
        provider=provider
    )
    
    result = await chain.invoke({"question": question})
    return result

async def process_with_rag(
    question: str,
    collection_name: Optional[str] = None,
    system_prompt: Optional[str] = None,
    provider: str = "ollama"
):
    """Process a question using RAG"""
    chain = await create_rag_chain(
        collection_name=collection_name,
        system_prompt=system_prompt,
        provider=provider
    )
    
    result = await chain.invoke(question)
    return result

async def process_conversational_rag(
    question: str,
    chat_history: List[Dict[str, str]],
    collection_name: Optional[str] = None,
    provider: str = "ollama"
):
    """Process a question using conversational RAG with history"""
    chain = await create_conversational_rag_chain(
        collection_name=collection_name,
        provider=provider
    )
    
    result = await chain.invoke({
        "question": question,
        "chat_history": chat_history
    })
    
    return result
