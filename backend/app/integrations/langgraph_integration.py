from typing import Dict, List, Any, Optional, TypedDict, Annotated, Literal
from enum import Enum
import operator
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolExecutor
from langgraph.prebuilt.tool_node import ToolNode
from langchain.tools import Tool
from langchain.schema import Document
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain.schema.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.messages import ChatMessage, FunctionMessage
import json
from loguru import logger

from app.core.config import settings
from app.db.chromadb import get_retriever
from app.integrations.ollama_interface import get_ollama_llm
from app.integrations.groq_ai_interface import get_groq_llm

# State definition for the graph
class GraphState(TypedDict):
    """State for the LangGraph flow"""
    messages: List[BaseMessage]
    tools: List[Tool]
    tool_results: List[Dict[str, Any]]
    documents: List[Document]
    next: str

def get_llm(provider: str = "ollama"):
    """Get LLM based on provider"""
    if provider == "groq":
        return get_groq_llm()
    else:
        return get_ollama_llm()

async def create_retrieve_analyze_graph(
    collection_name: Optional[str] = None,
    system_prompt: Optional[str] = None,
    provider: str = "ollama"
):
    """
    Create a graph for retrieving and analyzing information
    
    This graph implements the following flow:
    1. Retrieve documents based on the query
    2. Analyze documents to extract relevant information
    3. Decide if more information is needed
    4. Return the final answer
    """
    # Default system prompt
    default_system_prompt = """
    You are an AI assistant that helps users find and analyze information.
    Based on the provided documents, answer the user's question.
    If you need more information, you can ask for it. If you have enough information, provide a complete answer.
    """
    
    # Get LLM
    llm = get_llm(provider)
    
    # Get retriever
    retriever = await get_retriever(collection_name)
    
    # Tools setup
    tools = []
    tool_executor = ToolExecutor(tools)
    
    # Define states
    class AgentState(TypedDict):
        """State for the agent"""
        messages: List[BaseMessage]
        documents: List[Document]
        intermediate_steps: List[Dict[str, Any]]
        next: Optional[str]
    
    # Define node functions
    async def retrieve_documents(state: AgentState) -> AgentState:
        """Retrieve relevant documents"""
        # Get the last user message
        last_message = None
        for message in reversed(state["messages"]):
            if isinstance(message, HumanMessage):
                last_message = message
                break
        
        if not last_message:
            return state
        
        # Use the retriever to get documents
        query = last_message.content
        documents = retriever.get_relevant_documents(query)
        
        # Update state
        new_state = state.copy()
        new_state["documents"] = documents
        
        # Add system message with context
        context = "\n\n".join([doc.page_content for doc in documents])
        new_state["messages"].append(
            SystemMessage(content=f"Here are some relevant documents:\n\n{context}")
        )
        
        return new_state
    
    async def analyze_documents(state: AgentState) -> AgentState:
        """Analyze documents and generate response"""
        # Create messages for LLM with system prompt
        messages = [SystemMessage(content=system_prompt or default_system_prompt)]
        messages.extend(state["messages"])
        
        # Get response from LLM
        response = await llm.ainvoke(messages)
        
        # Update state
        new_state = state.copy()
        new_state["messages"].append(AIMessage(content=response.content))
        
        # Decide next step
        if "need more information" in response.content.lower():
            new_state["next"] = "ask_followup"
        else:
            new_state["next"] = "end"
        
        return new_state
    
    async def ask_followup(state: AgentState) -> AgentState:
        """Ask follow-up question if needed"""
        # Update state to continue
        return {**state, "next": "retrieve_documents"}
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("retrieve_documents", retrieve_documents)
    workflow.add_node("analyze_documents", analyze_documents)
    workflow.add_node("ask_followup", ask_followup)
    
    # Add edges
    workflow.add_edge("retrieve_documents", "analyze_documents")
    workflow.add_conditional_edges(
        "analyze_documents",
        lambda x: x["next"],
        {
            "ask_followup": "ask_followup",
            "end": "end"
        }
    )
    workflow.add_edge("ask_followup", "retrieve_documents")
    
    # Set entry point
    workflow.set_entry_point("retrieve_documents")
    
    # Compile
    app = workflow.compile()
    
    return app

async def create_agent_workflow(
    system_prompt: str,
    tools: List[Tool],
    provider: str = "ollama"
):
    """
    Create an agent workflow for task execution
    
    Args:
        system_prompt: System prompt for the agent
        tools: List of tools available to the agent
        provider: LLM provider
    
    Returns:
        Compiled LangGraph workflow
    """
    # Get LLM
    llm = get_llm(provider)
    
    # Set up tool execution
    tool_executor = ToolExecutor(tools)
    tool_node = ToolNode(tools)
    
    # Define state
    class AgentState(TypedDict):
        """State for the agent workflow"""
        messages: List[BaseMessage]
        intermediate_steps: List[Dict[str, Any]]
    
    # Agent nodes
    def agent(state: AgentState) -> Dict:
        """Agent node that decides what to do next"""
        messages = state["messages"]
        
        # If there are intermediate steps, add them to the messages
        for step in state.get("intermediate_steps", []):
            tool_name = step["tool"]
            observation = step["tool_output"]
            messages.append(FunctionMessage(content=str(observation), name=tool_name))
        
        # Add system prompt if not present
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=system_prompt)] + messages
        
        # Generate response
        response = llm.invoke(messages)
        
        # Decide whether to use a tool or return final answer
        if hasattr(response, "tool_calls") and response.tool_calls:
            # Use tool
            return {"next": "action", "messages": messages + [response]}
        else:
            # Return answer
            return {"next": "end", "messages": messages + [response]}
    
    def action(state: AgentState) -> Dict:
        """Execute tools"""
        # Get the last message
        last_message = state["messages"][-1]
        
        # Process tool calls
        action_input = last_message.tool_calls[0].get("args", {})
        action_name = last_message.tool_calls[0].get("name", "")
        
        # Execute the tool
        observation = tool_executor.invoke({"name": action_name, "input": action_input})
        
        # Add to intermediate steps
        intermediate_steps = state.get("intermediate_steps", [])
        intermediate_steps.append({
            "tool": action_name,
            "tool_input": action_input,
            "tool_output": observation
        })
        
        return {
            "intermediate_steps": intermediate_steps,
            "messages": state["messages"],
            "next": "agent"
        }
    
    # Create graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("agent", agent)
    workflow.add_node("action", action)
    
    # Add edges
    workflow.add_conditional_edges(
        "agent",
        lambda x: x["next"],
        {
            "action": "action",
            "end": "end"
        }
    )
    workflow.add_edge("action", "agent")
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Compile
    return workflow.compile()

async def process_with_graph(
    app,
    query: str,
    chat_history: Optional[List[Dict[str, str]]] = None
):
    """
    Process a query with a LangGraph workflow
    
    Args:
        app: Compiled LangGraph workflow
        query: User query
        chat_history: Optional chat history
        
    Returns:
        Final state of the workflow
    """
    # Convert chat history to messages
    messages = []
    if chat_history:
        for message in chat_history:
            if message["role"] == "user":
                messages.append(HumanMessage(content=message["content"]))
            elif message["role"] == "assistant":
                messages.append(AIMessage(content=message["content"]))
            elif message["role"] == "system":
                messages.append(SystemMessage(content=message["content"]))
    
    # Add current query
    messages.append(HumanMessage(content=query))
    
    # Initialize state
    initial_state = {
        "messages": messages,
        "documents": [],
        "intermediate_steps": []
    }
    
    # Run the workflow
    result = await app.ainvoke(initial_state)
    
    return result
