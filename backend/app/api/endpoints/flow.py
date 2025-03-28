from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Body, Query
from pydantic import BaseModel, Field

from app.core.config import settings
from app.api.deps import get_current_user
from app.integrations.langgraph_integration import (
    create_retrieve_analyze_graph,
    create_agent_workflow,
    process_with_graph
)
from app.schemas.users import User

router = APIRouter()

class GraphFlowRequest(BaseModel):
    """Request model for graph flow processing"""
    query: str
    chat_history: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    collection_name: Optional[str] = None
    system_prompt: Optional[str] = None
    provider: Optional[str] = "ollama"

class GraphFlowResponse(BaseModel):
    """Response model for graph flow processing"""
    result: Dict[str, Any]
    messages: List[Dict[str, str]]

@router.post("/retrieve-analyze", response_model=GraphFlowResponse)
async def retrieve_analyze_flow(
    request: GraphFlowRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Process a query through the retrieve-analyze flow
    
    This endpoint:
    1. Creates a retrieve-analyze graph
    2. Processes the query through the graph
    3. Returns the result and updated messages
    """
    try:
        # Create the graph
        graph = await create_retrieve_analyze_graph(
            collection_name=request.collection_name,
            system_prompt=request.system_prompt,
            provider=request.provider
        )
        
        # Process the query
        result = await process_with_graph(
            app=graph,
            query=request.query,
            chat_history=request.chat_history
        )
        
        # Extract messages for response
        messages = []
        for msg in result["messages"]:
            if hasattr(msg, "content") and hasattr(msg, "type"):
                role = "system"
                if msg.type == "human":
                    role = "user"
                elif msg.type == "ai":
                    role = "assistant"
                
                messages.append({
                    "role": role,
                    "content": msg.content
                })
        
        return GraphFlowResponse(
            result=result,
            messages=messages
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing retrieve-analyze flow: {str(e)}"
        )

class AgentToolSpec(BaseModel):
    """Specification for an agent tool"""
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

class AgentFlowRequest(BaseModel):
    """Request model for agent flow processing"""
    query: str
    system_prompt: str
    tools: List[AgentToolSpec] = Field(default_factory=list)
    chat_history: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    provider: Optional[str] = "ollama"

@router.post("/agent", response_model=GraphFlowResponse)
async def agent_flow(
    request: AgentFlowRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Process a query through the agent workflow
    
    This endpoint:
    1. Creates tools based on the provided specifications
    2. Creates an agent workflow with the tools
    3. Processes the query through the workflow
    4. Returns the result and updated messages
    """
    try:
        # Create tools from specifications
        from langchain.tools import Tool
        
        tools = []
        for tool_spec in request.tools:
            # This is a simplified implementation
            # In a real application, you would create actual tool functions
            tools.append(
                Tool(
                    name=tool_spec.name,
                    description=tool_spec.description,
                    func=lambda x: f"Simulated result for {tool_spec.name} with input {x}"
                )
            )
        
        # Create the workflow
        workflow = await create_agent_workflow(
            system_prompt=request.system_prompt,
            tools=tools,
            provider=request.provider
        )
        
        # Process the query
        result = await process_with_graph(
            app=workflow,
            query=request.query,
            chat_history=request.chat_history
        )
        
        # Extract messages for response
        messages = []
        for msg in result["messages"]:
            if hasattr(msg, "content") and hasattr(msg, "type"):
                role = "system"
                if msg.type == "human":
                    role = "user"
                elif msg.type == "ai":
                    role = "assistant"
                elif msg.type == "function":
                    role = "function"
                
                messages.append({
                    "role": role,
                    "content": msg.content,
                    **({"name": msg.name} if hasattr(msg, "name") else {})
                })
        
        return GraphFlowResponse(
            result=result,
            messages=messages
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing agent flow: {str(e)}"
        ) 