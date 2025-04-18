import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional, Callable, Awaitable, Set
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query, Header
from fastapi.security import APIKeyHeader
from jose import JWTError, jwt
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import settings
from app.utils.helpers import get_kafka_producer, get_kafka_consumer, SessionManager, ContextManager
from app.mcp.agent_registry import agent_registry, AgentCapability, RegisteredAgent

# Models for MCP requests and responses
class MCPRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    action: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class MCPResponse(BaseModel):
    request_id: str
    success: bool
    message: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AgentRegistrationRequest(BaseModel):
    name: str
    description: str
    capabilities: List[AgentCapability]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class InterAgentMessage(BaseModel):
    source_agent_id: str
    target_agent_id: Optional[str] = None
    target_capability: Optional[str] = None
    message_type: str
    content: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Kafka topic names
TOPIC_TEXT_TO_SCENE = "text-to-scene"
TOPIC_ASSET_GENERATION = "asset-generation"
TOPIC_AR_RENDERING = "ar-rendering"
TOPIC_CONTEXT_UPDATE = "context-update"
TOPIC_SENTIMENT_ANALYSIS = "sentiment-analysis"
TOPIC_INTER_AGENT = "inter-agent"
TOPIC_AGENT_REGISTRY = "agent-registry"

# MCP Server Authentication
mcp_api_key_header = APIKeyHeader(name="X-MCP-API-Key")

async def validate_api_key(api_key: str = Depends(mcp_api_key_header)):
    if api_key != settings.MCP_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return api_key

# JWT Token verification for WebSockets
async def verify_token(token: str) -> Dict[str, Any]:
    """Verify a JWT token and return the payload"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        user_id = payload.get("user_id")
        
        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
            
        return {"username": username, "user_id": user_id}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

class MCPServer:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agent_connections: Dict[str, WebSocket] = {}
        self.session_manager = SessionManager()
        self.context_manager = ContextManager()
        self.kafka_producer = get_kafka_producer()
        
        # Mapping of actions to handler functions
        self.action_handlers = {
            "text_to_scene": self.handle_text_to_scene,
            "asset_generation": self.handle_asset_generation,
            "ar_rendering": self.handle_ar_rendering,
            "update_context": self.handle_context_update,
            "analyze_sentiment": self.handle_sentiment_analysis,
            "register_agent": self.handle_agent_registration,
            "unregister_agent": self.handle_agent_unregistration,
            "agent_heartbeat": self.handle_agent_heartbeat,
            "get_agents": self.handle_get_agents,
            "get_capabilities": self.handle_get_capabilities,
            "inter_agent_message": self.handle_inter_agent_message,
        }
        
        # Start Kafka consumer tasks for each topic
        self.kafka_tasks = []
        
    async def start(self):
        """Start the MCP server and Kafka consumers"""
        self.kafka_tasks = [
            asyncio.create_task(self.consume_kafka_topic(TOPIC_TEXT_TO_SCENE, self.on_text_to_scene_result)),
            asyncio.create_task(self.consume_kafka_topic(TOPIC_ASSET_GENERATION, self.on_asset_generation_result)),
            asyncio.create_task(self.consume_kafka_topic(TOPIC_AR_RENDERING, self.on_ar_rendering_result)),
            asyncio.create_task(self.consume_kafka_topic(TOPIC_CONTEXT_UPDATE, self.on_context_update_result)),
            asyncio.create_task(self.consume_kafka_topic(TOPIC_SENTIMENT_ANALYSIS, self.on_sentiment_analysis_result)),
            asyncio.create_task(self.consume_kafka_topic(TOPIC_INTER_AGENT, self.on_inter_agent_message)),
            asyncio.create_task(self.consume_kafka_topic(TOPIC_AGENT_REGISTRY, self.on_agent_registry_update)),
        ]
        logger.info("MCP Server started")
        
    async def stop(self):
        """Stop the MCP server and Kafka consumers"""
        for task in self.kafka_tasks:
            task.cancel()
        logger.info("MCP Server stopped")
    
    async def connect(self, websocket: WebSocket, client_id: str, user_id: Optional[str] = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        # Create or update session if user_id is provided
        if user_id:
            self.session_manager.save_session(user_id, {
                "client_id": client_id,
                "connected_at": datetime.utcnow().isoformat()
            })
            logger.info(f"Authenticated user {user_id} connected as client {client_id}")
        else:
            logger.info(f"Anonymous client {client_id} connected")
    
    async def connect_agent(self, websocket: WebSocket, agent_id: str):
        """Accept a new agent WebSocket connection"""
        await websocket.accept()
        self.agent_connections[agent_id] = websocket
        
        # Update agent status in registry
        agent_registry.update_agent_status(agent_id, "online")
        logger.info(f"Agent {agent_id} connected via WebSocket")
    
    def disconnect(self, client_id: str):
        """Handle WebSocket disconnection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")
    
    def disconnect_agent(self, agent_id: str):
        """Handle agent WebSocket disconnection"""
        if agent_id in self.agent_connections:
            del self.agent_connections[agent_id]
            
            # Update agent status in registry
            agent_registry.update_agent_status(agent_id, "offline")
            logger.info(f"Agent {agent_id} disconnected")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients"""
        disconnected = []
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(client_id)
            except Exception as e:
                logger.error(f"Error broadcasting to client {client_id}: {e}")
                disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)
    
    async def broadcast_to_agents(self, message: Dict[str, Any]):
        """Broadcast a message to all connected agents"""
        disconnected = []
        for agent_id, connection in self.agent_connections.items():
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(agent_id)
            except Exception as e:
                logger.error(f"Error broadcasting to agent {agent_id}: {e}")
                disconnected.append(agent_id)
        
        # Clean up disconnected agents
        for agent_id in disconnected:
            self.disconnect_agent(agent_id)
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except WebSocketDisconnect:
                self.disconnect(client_id)
            except Exception as e:
                logger.error(f"Error sending to client {client_id}: {e}")
                self.disconnect(client_id)
    
    async def send_to_agent(self, agent_id: str, message: Dict[str, Any]):
        """Send a message to a specific agent"""
        if agent_id in self.agent_connections:
            try:
                await self.agent_connections[agent_id].send_json(message)
                return True
            except WebSocketDisconnect:
                self.disconnect_agent(agent_id)
            except Exception as e:
                logger.error(f"Error sending to agent {agent_id}: {e}")
                self.disconnect_agent(agent_id)
        return False
    
    async def receive_and_process(self, websocket: WebSocket, client_id: str, user_id: Optional[str] = None):
        """Receive and process messages from a WebSocket client"""
        try:
            while True:
                data = await websocket.receive_json()
                try:
                    request = MCPRequest(**data)
                    logger.info(f"Received request: {request.action} from client {client_id}")
                    
                    # Add authenticated user_id to the request if provided
                    if user_id and not request.user_id:
                        request.user_id = user_id
                    # Otherwise use client_id if user_id not provided in request
                    elif not request.user_id:
                        request.user_id = client_id
                    
                    # Process the request
                    if request.action in self.action_handlers:
                        response = await self.action_handlers[request.action](request)
                    else:
                        response = MCPResponse(
                            request_id=request.request_id,
                            success=False,
                            message=f"Unknown action: {request.action}"
                        )
                    
                    # Send response
                    await self.send_to_client(client_id, response.dict())
                    
                except Exception as e:
                    logger.error(f"Error processing request from {client_id}: {e}")
                    error_response = MCPResponse(
                        request_id=data.get("request_id", str(uuid.uuid4())),
                        success=False,
                        message=f"Error processing request: {str(e)}"
                    )
                    await self.send_to_client(client_id, error_response.dict())
        except WebSocketDisconnect:
            self.disconnect(client_id)
        except Exception as e:
            logger.error(f"Unexpected error in WebSocket connection {client_id}: {e}")
            self.disconnect(client_id)
    
    async def receive_and_process_agent(self, websocket: WebSocket, agent_id: str):
        """Receive and process messages from an agent WebSocket"""
        try:
            while True:
                data = await websocket.receive_json()
                try:
                    # Check for inter-agent messages
                    if "message_type" in data:
                        message = InterAgentMessage(**data)
                        await self.route_inter_agent_message(message)
                    else:
                        # Handle as regular request
                        request = MCPRequest(**data)
                        logger.info(f"Received request: {request.action} from agent {agent_id}")
                        
                        # Process the request
                        if request.action in self.action_handlers:
                            response = await self.action_handlers[request.action](request)
                        else:
                            response = MCPResponse(
                                request_id=request.request_id,
                                success=False,
                                message=f"Unknown action: {request.action}"
                            )
                        
                        # Send response
                        await self.send_to_agent(agent_id, response.dict())
                    
                except Exception as e:
                    logger.error(f"Error processing request from agent {agent_id}: {e}")
                    error_response = MCPResponse(
                        request_id=data.get("request_id", str(uuid.uuid4())),
                        success=False,
                        message=f"Error processing request: {str(e)}"
                    )
                    await self.send_to_agent(agent_id, error_response.dict())
        except WebSocketDisconnect:
            self.disconnect_agent(agent_id)
        except Exception as e:
            logger.error(f"Unexpected error in agent WebSocket connection {agent_id}: {e}")
            self.disconnect_agent(agent_id)
    
    # Agent registration handlers
    async def handle_agent_registration(self, request: MCPRequest) -> MCPResponse:
        """Handle agent registration requests"""
        try:
            registration_data = AgentRegistrationRequest(**request.data)
            
            # Register the agent
            agent_id = agent_registry.register_agent(
                name=registration_data.name,
                description=registration_data.description,
                capabilities=registration_data.capabilities,
                metadata=registration_data.metadata
            )
            
            # Notify other components about new agent
            self.kafka_producer.produce(
                f"{settings.KAFKA_TOPIC_PREFIX}{TOPIC_AGENT_REGISTRY}",
                json.dumps({
                    "event": "agent_registered",
                    "agent_id": agent_id,
                    "agent_info": registration_data.dict()
                }).encode('utf-8'),
                callback=self.kafka_delivery_report
            )
            self.kafka_producer.flush()
            
            return MCPResponse(
                request_id=request.request_id,
                success=True,
                message=f"Agent successfully registered",
                data={"agent_id": agent_id}
            )
        except Exception as e:
            logger.error(f"Error registering agent: {e}")
            return MCPResponse(
                request_id=request.request_id,
                success=False,
                message=f"Error registering agent: {str(e)}"
            )
    
    async def handle_agent_unregistration(self, request: MCPRequest) -> MCPResponse:
        """Handle agent unregistration requests"""
        try:
            agent_id = request.data.get("agent_id")
            if not agent_id:
                return MCPResponse(
                    request_id=request.request_id,
                    success=False,
                    message="Missing agent_id in request"
                )
            
            # Unregister the agent
            success = agent_registry.unregister_agent(agent_id)
            
            if success:
                # Notify other components about agent removal
                self.kafka_producer.produce(
                    f"{settings.KAFKA_TOPIC_PREFIX}{TOPIC_AGENT_REGISTRY}",
                    json.dumps({
                        "event": "agent_unregistered",
                        "agent_id": agent_id
                    }).encode('utf-8'),
                    callback=self.kafka_delivery_report
                )
                self.kafka_producer.flush()
            
            return MCPResponse(
                request_id=request.request_id,
                success=success,
                message=f"Agent successfully unregistered" if success else "Agent not found"
            )
        except Exception as e:
            logger.error(f"Error unregistering agent: {e}")
            return MCPResponse(
                request_id=request.request_id,
                success=False,
                message=f"Error unregistering agent: {str(e)}"
            )
    
    async def handle_agent_heartbeat(self, request: MCPRequest) -> MCPResponse:
        """Handle agent heartbeat requests"""
        try:
            agent_id = request.data.get("agent_id")
            status = request.data.get("status", "online")
            
            if not agent_id:
                return MCPResponse(
                    request_id=request.request_id,
                    success=False,
                    message="Missing agent_id in request"
                )
            
            # Update the agent heartbeat
            success = agent_registry.update_agent_status(agent_id, status)
            
            return MCPResponse(
                request_id=request.request_id,
                success=success,
                message="Heartbeat received" if success else "Agent not found"
            )
        except Exception as e:
            logger.error(f"Error processing agent heartbeat: {e}")
            return MCPResponse(
                request_id=request.request_id,
                success=False,
                message=f"Error processing agent heartbeat: {str(e)}"
            )
    
    async def handle_get_agents(self, request: MCPRequest) -> MCPResponse:
        """Handle requests for agent information"""
        try:
            agents = agent_registry.get_all_agents()
            
            return MCPResponse(
                request_id=request.request_id,
                success=True,
                data={
                    "agents": [agent.dict() for agent in agents]
                }
            )
        except Exception as e:
            logger.error(f"Error getting agents: {e}")
            return MCPResponse(
                request_id=request.request_id,
                success=False,
                message=f"Error getting agents: {str(e)}"
            )
    
    async def handle_get_capabilities(self, request: MCPRequest) -> MCPResponse:
        """Handle requests for capability information"""
        try:
            capabilities = agent_registry.get_available_capabilities()
            
            # Get capability details by looking at the first agent that provides each capability
            capability_details = {}
            for cap_name in capabilities:
                agents = agent_registry.get_agents_by_capability(cap_name)
                if agents:
                    for capability in agents[0].capabilities:
                        if capability.name == cap_name:
                            capability_details[cap_name] = capability.dict()
                            break
            
            return MCPResponse(
                request_id=request.request_id,
                success=True,
                data={
                    "capabilities": capabilities,
                    "capability_details": capability_details
                }
            )
        except Exception as e:
            logger.error(f"Error getting capabilities: {e}")
            return MCPResponse(
                request_id=request.request_id,
                success=False,
                message=f"Error getting capabilities: {str(e)}"
            )
    
    async def handle_inter_agent_message(self, request: MCPRequest) -> MCPResponse:
        """Handle inter-agent message routing"""
        try:
            message_data = request.data
            source_agent_id = message_data.get("source_agent_id")
            target_agent_id = message_data.get("target_agent_id")
            target_capability = message_data.get("target_capability")
            
            if not source_agent_id:
                return MCPResponse(
                    request_id=request.request_id,
                    success=False,
                    message="Missing source_agent_id in request"
                )
            
            if not target_agent_id and not target_capability:
                return MCPResponse(
                    request_id=request.request_id,
                    success=False,
                    message="Must specify either target_agent_id or target_capability"
                )
            
            # Create inter-agent message
            message = InterAgentMessage(
                source_agent_id=source_agent_id,
                target_agent_id=target_agent_id,
                target_capability=target_capability,
                message_type=message_data.get("message_type", "request"),
                content=message_data.get("content", {})
            )
            
            # Route the message
            success = await self.route_inter_agent_message(message)
            
            return MCPResponse(
                request_id=request.request_id,
                success=success,
                message="Message routed successfully" if success else "Failed to route message"
            )
        except Exception as e:
            logger.error(f"Error routing inter-agent message: {e}")
            return MCPResponse(
                request_id=request.request_id,
                success=False,
                message=f"Error routing inter-agent message: {str(e)}"
            )
    
    async def route_inter_agent_message(self, message: InterAgentMessage) -> bool:
        """
        Route an inter-agent message to the appropriate target
        
        Args:
            message: The inter-agent message to route
            
        Returns:
            Success status
        """
        # If target agent is specified directly
        if message.target_agent_id:
            # Try WebSocket first
            if message.target_agent_id in self.agent_connections:
                return await self.send_to_agent(message.target_agent_id, message.dict())
            
            # Fall back to Kafka
            self.kafka_producer.produce(
                f"{settings.KAFKA_TOPIC_PREFIX}{TOPIC_INTER_AGENT}",
                json.dumps(message.dict()).encode('utf-8'),
                callback=self.kafka_delivery_report
            )
            self.kafka_producer.flush()
            return True
        
        # If target capability is specified
        elif message.target_capability:
            # Find an agent with the capability
            agent_id = agent_registry.find_agent_for_task(message.target_capability)
            
            if not agent_id:
                logger.warning(f"No agent found with capability: {message.target_capability}")
                return False
            
            # Update the message with the resolved target
            message_dict = message.dict()
            message_dict["target_agent_id"] = agent_id
            
            # Try WebSocket first
            if agent_id in self.agent_connections:
                return await self.send_to_agent(agent_id, message_dict)
            
            # Fall back to Kafka
            self.kafka_producer.produce(
                f"{settings.KAFKA_TOPIC_PREFIX}{TOPIC_INTER_AGENT}",
                json.dumps(message_dict).encode('utf-8'),
                callback=self.kafka_delivery_report
            )
            self.kafka_producer.flush()
            return True
        
        return False
    
    # Action handlers
    async def handle_text_to_scene(self, request: MCPRequest) -> MCPResponse:
        """Handle text to scene conversion requests"""
        try:
            # Get or create context for this user
            context_id = request.data.get("context_id", request.user_id)
            context = self.context_manager.get_context(context_id) or {}
            
            # Prepare Kafka message
            message = {
                "request_id": request.request_id,
                "user_id": request.user_id,
                "text": request.data.get("text", ""),
                "context": context,
                "options": request.data.get("options", {}),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to Kafka
            self.kafka_producer.produce(
                f"{settings.KAFKA_TOPIC_PREFIX}{TOPIC_TEXT_TO_SCENE}",
                json.dumps(message).encode('utf-8'),
                callback=self.kafka_delivery_report
            )
            self.kafka_producer.flush()
            
            return MCPResponse(
                request_id=request.request_id,
                success=True,
                message="Text to scene conversion request submitted",
                data={"status": "processing"}
            )
        except Exception as e:
            logger.error(f"Error in text_to_scene handler: {e}")
            return MCPResponse(
                request_id=request.request_id,
                success=False,
                message=f"Error processing text to scene request: {str(e)}"
            )
    
    async def handle_asset_generation(self, request: MCPRequest) -> MCPResponse:
        """Handle asset generation requests"""
        try:
            # Prepare Kafka message
            message = {
                "request_id": request.request_id,
                "user_id": request.user_id,
                "scene_params": request.data.get("scene_params", {}),
                "options": request.data.get("options", {}),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to Kafka
            self.kafka_producer.produce(
                f"{settings.KAFKA_TOPIC_PREFIX}{TOPIC_ASSET_GENERATION}",
                json.dumps(message).encode('utf-8'),
                callback=self.kafka_delivery_report
            )
            self.kafka_producer.flush()
            
            return MCPResponse(
                request_id=request.request_id,
                success=True,
                message="Asset generation request submitted",
                data={"status": "processing"}
            )
        except Exception as e:
            logger.error(f"Error in asset_generation handler: {e}")
            return MCPResponse(
                request_id=request.request_id,
                success=False,
                message=f"Error processing asset generation request: {str(e)}"
            )
    
    async def handle_ar_rendering(self, request: MCPRequest) -> MCPResponse:
        """Handle AR rendering requests"""
        try:
            # Prepare Kafka message
            message = {
                "request_id": request.request_id,
                "user_id": request.user_id,
                "assets": request.data.get("assets", []),
                "scene_config": request.data.get("scene_config", {}),
                "device_info": request.data.get("device_info", {}),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to Kafka
            self.kafka_producer.produce(
                f"{settings.KAFKA_TOPIC_PREFIX}{TOPIC_AR_RENDERING}",
                json.dumps(message).encode('utf-8'),
                callback=self.kafka_delivery_report
            )
            self.kafka_producer.flush()
            
            return MCPResponse(
                request_id=request.request_id,
                success=True,
                message="AR rendering request submitted",
                data={"status": "processing"}
            )
        except Exception as e:
            logger.error(f"Error in ar_rendering handler: {e}")
            return MCPResponse(
                request_id=request.request_id,
                success=False,
                message=f"Error processing AR rendering request: {str(e)}"
            )
    
    async def handle_context_update(self, request: MCPRequest) -> MCPResponse:
        """Handle context update requests"""
        try:
            context_id = request.data.get("context_id", request.user_id)
            context_data = request.data.get("context", {})
            expiry = request.data.get("expiry", 86400)  # Default 24 hours
            
            # Update context in Redis
            success = self.context_manager.update_context(context_id, context_data, expiry)
            
            # Also send to Kafka for other agents to be notified
            message = {
                "request_id": request.request_id,
                "user_id": request.user_id,
                "context_id": context_id,
                "context_data": context_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.kafka_producer.produce(
                f"{settings.KAFKA_TOPIC_PREFIX}{TOPIC_CONTEXT_UPDATE}",
                json.dumps(message).encode('utf-8'),
                callback=self.kafka_delivery_report
            )
            self.kafka_producer.flush()
            
            return MCPResponse(
                request_id=request.request_id,
                success=success,
                message="Context updated successfully" if success else "Failed to update context",
                data={"context_id": context_id}
            )
        except Exception as e:
            logger.error(f"Error in context_update handler: {e}")
            return MCPResponse(
                request_id=request.request_id,
                success=False,
                message=f"Error updating context: {str(e)}"
            )
    
    async def handle_sentiment_analysis(self, request: MCPRequest) -> MCPResponse:
        """Handle sentiment analysis requests"""
        try:
            # Prepare Kafka message
            message = {
                "request_id": request.request_id,
                "user_id": request.user_id,
                "text": request.data.get("text", ""),
                "context_id": request.data.get("context_id", request.user_id),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to Kafka
            self.kafka_producer.produce(
                f"{settings.KAFKA_TOPIC_PREFIX}{TOPIC_SENTIMENT_ANALYSIS}",
                json.dumps(message).encode('utf-8'),
                callback=self.kafka_delivery_report
            )
            self.kafka_producer.flush()
            
            return MCPResponse(
                request_id=request.request_id,
                success=True,
                message="Sentiment analysis request submitted",
                data={"status": "processing"}
            )
        except Exception as e:
            logger.error(f"Error in sentiment_analysis handler: {e}")
            return MCPResponse(
                request_id=request.request_id,
                success=False,
                message=f"Error processing sentiment analysis request: {str(e)}"
            )
    
    # Kafka callback for message delivery
    def kafka_delivery_report(self, err, msg):
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")
    
    # Kafka consumer functions
    async def consume_kafka_topic(self, topic: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Consume messages from a Kafka topic and call the callback function"""
        consumer = get_kafka_consumer([topic])
        try:
            while True:
                msg = consumer.poll(1.0)
                if msg is None:
                    await asyncio.sleep(0.1)
                    continue
                
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    continue
                
                try:
                    message = json.loads(msg.value().decode('utf-8'))
                    await callback(message)
                except Exception as e:
                    logger.error(f"Error processing Kafka message: {e}")
        finally:
            consumer.close()
    
    # Kafka message handlers
    async def on_text_to_scene_result(self, message: Dict[str, Any]):
        """Handle results from text-to-scene agent"""
        request_id = message.get("request_id")
        user_id = message.get("user_id")
        
        # Create response
        response = MCPResponse(
            request_id=request_id,
            success=True,
            message="Text to scene conversion completed",
            data={
                "scene_params": message.get("scene_params", {}),
                "recommendations": message.get("recommendations", [])
            }
        )
        
        # Send to client if connected
        if user_id in self.active_connections:
            await self.send_to_client(user_id, response.dict())
    
    async def on_asset_generation_result(self, message: Dict[str, Any]):
        """Handle results from asset generation agent"""
        request_id = message.get("request_id")
        user_id = message.get("user_id")
        
        # Create response
        response = MCPResponse(
            request_id=request_id,
            success=True,
            message="Asset generation completed",
            data={
                "assets": message.get("assets", []),
                "metadata": message.get("metadata", {})
            }
        )
        
        # Send to client if connected
        if user_id in self.active_connections:
            await self.send_to_client(user_id, response.dict())
    
    async def on_ar_rendering_result(self, message: Dict[str, Any]):
        """Handle results from AR rendering agent"""
        request_id = message.get("request_id")
        user_id = message.get("user_id")
        
        # Create response
        response = MCPResponse(
            request_id=request_id,
            success=True,
            message="AR rendering completed",
            data={
                "scene_url": message.get("scene_url", ""),
                "render_options": message.get("render_options", {}),
                "preview_image": message.get("preview_image", "")
            }
        )
        
        # Send to client if connected
        if user_id in self.active_connections:
            await self.send_to_client(user_id, response.dict())
    
    async def on_context_update_result(self, message: Dict[str, Any]):
        """Handle context update notifications"""
        user_id = message.get("user_id")
        context_id = message.get("context_id")
        
        # No need to notify clients for context updates
        logger.debug(f"Context updated for user {user_id}, context_id {context_id}")
    
    async def on_sentiment_analysis_result(self, message: Dict[str, Any]):
        """Handle results from sentiment analysis agent"""
        request_id = message.get("request_id")
        user_id = message.get("user_id")
        
        # Create response
        response = MCPResponse(
            request_id=request_id,
            success=True,
            message="Sentiment analysis completed",
            data={
                "sentiment": message.get("sentiment", {}),
                "engagement_metrics": message.get("engagement_metrics", {})
            }
        )
        
        # Send to client if connected
        if user_id in self.active_connections:
            await self.send_to_client(user_id, response.dict())
    
    async def on_inter_agent_message(self, message: Dict[str, Any]):
        """Handle inter-agent messages from Kafka"""
        try:
            inter_agent_msg = InterAgentMessage(**message)
            await self.route_inter_agent_message(inter_agent_msg)
        except Exception as e:
            logger.error(f"Error processing inter-agent message: {e}")
    
    async def on_agent_registry_update(self, message: Dict[str, Any]):
        """Handle agent registry updates from Kafka"""
        event = message.get("event")
        
        if event == "agent_registered":
            # Notify connected agents about new agent
            notification = {
                "notification_type": "agent_registered",
                "agent_id": message.get("agent_id"),
                "agent_info": message.get("agent_info", {})
            }
            await self.broadcast_to_agents(notification)
        
        elif event == "agent_unregistered":
            # Notify connected agents about removed agent
            notification = {
                "notification_type": "agent_unregistered",
                "agent_id": message.get("agent_id")
            }
            await self.broadcast_to_agents(notification)

# Create instance
mcp_server = MCPServer()

# FastAPI integration
def setup_mcp_websocket(app: FastAPI):
    """Set up MCP WebSocket route in a FastAPI app"""
    
    @app.on_event("startup")
    async def startup_event():
        await mcp_server.start()
    
    @app.on_event("shutdown")
    async def shutdown_event():
        await mcp_server.stop()
    
    @app.websocket(settings.MCP_WEBSOCKET_PATH + "/{client_id}")
    async def websocket_endpoint(
        websocket: WebSocket, 
        client_id: str, 
        token: Optional[str] = Query(None)
    ):
        # Verify JWT token if provided
        user_id = None
        if token:
            try:
                payload = await verify_token(token)
                user_id = payload.get("user_id")
            except HTTPException as e:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=e.detail)
                return
        
        # Connect WebSocket
        await mcp_server.connect(websocket, client_id, user_id)
        await mcp_server.receive_and_process(websocket, client_id, user_id)
    
    @app.websocket("/agent-ws/{agent_id}")
    async def agent_websocket_endpoint(
        websocket: WebSocket,
        agent_id: str,
        api_key: str = Query(...)
    ):
        # Verify API key
        if api_key != settings.MCP_SECRET:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid API key")
            return
        
        # Connect agent WebSocket
        await mcp_server.connect_agent(websocket, agent_id)
        await mcp_server.receive_and_process_agent(websocket, agent_id)
