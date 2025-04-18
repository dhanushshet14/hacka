import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import httpx
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import settings
from app.mcp.agent_registry import AgentCapability
from app.utils.helpers import get_kafka_consumer, get_kafka_producer

# Constants
AGENT_NAME = "ar_rendering_agent"
AGENT_DESCRIPTION = "Processes AR scene parameters and prepares scenes for rendering"
TOPIC_AR_RENDERING = "ar-rendering"
TOPIC_ASSET_GENERATION = "asset-generation-results"

# Models
class RenderingOptions(BaseModel):
    """Options for AR rendering"""
    quality: str = "medium"  # low, medium, high, ultra
    shadows_enabled: bool = True
    antialiasing: bool = True
    post_processing: bool = True
    occlusion: bool = True
    lighting_model: str = "standard"  # standard, pbr, mobile
    frame_rate_target: int = 60
    max_concurrent_objects: Optional[int] = None
    lod_bias: float = 1.0
    texture_quality: str = "medium"  # low, medium, high
    render_scale: float = 1.0

class DeviceInfo(BaseModel):
    """Information about the client device"""
    type: str  # mobile, tablet, hmd, desktop
    os: str
    model: Optional[str] = None
    browser: Optional[str] = None
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    gpu: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)  # ar, vr, webgl2, etc.

class ARScene(BaseModel):
    """AR scene data, simplified version matching the text_to_scene_agent output"""
    id: str
    name: str
    description: Optional[str] = None
    elements: List[Dict[str, Any]] = Field(default_factory=list)
    lights: List[Dict[str, Any]] = Field(default_factory=list)
    environment: Dict[str, Any] = Field(default_factory=dict)
    anchoring: Optional[str] = None
    scale: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RenderableARScene(BaseModel):
    """AR scene with rendering-specific properties"""
    id: str
    original_scene_id: str
    scene_url: str
    preview_image_url: Optional[str] = None
    scene_data: Dict[str, Any]
    scene_format: str  # gltf, usdz, reality, webxr
    file_size: Optional[int] = None
    creation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    rendering_options: Dict[str, Any] = Field(default_factory=dict)
    compatible_devices: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ARRenderingAgent:
    """Agent that processes AR scene parameters and prepares scenes for rendering"""
    
    def __init__(self):
        self.agent_id = None
        self.kafka_producer = get_kafka_producer()
        self.kafka_consumer = None
        self.asset_consumer = None
        self.consumer_task = None
        self.asset_consumer_task = None
        self.is_running = False
        self.asset_cache = {}  # Store asset information by ID
        
        # Define capabilities
        self.capabilities = [
            AgentCapability(
                name="ar_scene_rendering",
                description="Processes AR scene parameters and prepares scenes for rendering",
                parameters={
                    "scene_params": "The AR scene parameters to process",
                    "device_info": "Information about the client device",
                    "options": "Optional rendering options"
                },
                example={
                    "scene_params": {"id": "scene_12345", "name": "My AR Scene", "elements": []},
                    "device_info": {"type": "mobile", "os": "iOS", "model": "iPhone 13"},
                    "options": {"quality": "high", "shadows_enabled": True}
                }
            )
        ]
    
    async def start(self):
        """Start the agent, register with MCP, and begin consuming messages"""
        # Register with MCP server
        await self.register_with_mcp()
        
        # Start Kafka consumers
        self.is_running = True
        self.consumer_task = asyncio.create_task(self.consume_messages())
        self.asset_consumer_task = asyncio.create_task(self.consume_asset_messages())
        
        logger.info(f"{AGENT_NAME} started with agent_id: {self.agent_id}")
    
    async def stop(self):
        """Stop the agent and clean up resources"""
        self.is_running = False
        
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass
        
        if self.asset_consumer_task:
            self.asset_consumer_task.cancel()
            try:
                await self.asset_consumer_task
            except asyncio.CancelledError:
                pass
        
        if self.kafka_consumer:
            self.kafka_consumer.close()
        
        if self.asset_consumer:
            self.asset_consumer.close()
        
        # Unregister from MCP
        await self.unregister_from_mcp()
        
        logger.info(f"{AGENT_NAME} stopped")
    
    async def register_with_mcp(self):
        """Register the agent with the MCP server"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://{settings.MCP_HOST}:{settings.MCP_PORT}/api/v1/agent/register",
                    headers={"X-MCP-API-Key": settings.MCP_SECRET},
                    json={
                        "name": AGENT_NAME,
                        "description": AGENT_DESCRIPTION,
                        "capabilities": [capability.dict() for capability in self.capabilities],
                        "metadata": {
                            "version": "1.0.0",
                            "supported_formats": ["gltf", "usdz", "webxr"]
                        }
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.agent_id = data.get("agent_id")
                    logger.info(f"Registered with MCP server, agent_id: {self.agent_id}")
                else:
                    logger.error(f"Failed to register with MCP server: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error registering with MCP server: {e}")
    
    async def unregister_from_mcp(self):
        """Unregister the agent from the MCP server"""
        if not self.agent_id:
            return
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://{settings.MCP_HOST}:{settings.MCP_PORT}/api/v1/agent/unregister",
                    headers={"X-MCP-API-Key": settings.MCP_SECRET},
                    json={"agent_id": self.agent_id},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Unregistered from MCP server, agent_id: {self.agent_id}")
                else:
                    logger.error(f"Failed to unregister from MCP server: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error unregistering from MCP server: {e}")
    
    async def consume_messages(self):
        """Consume messages from AR rendering Kafka topic"""
        self.kafka_consumer = get_kafka_consumer([TOPIC_AR_RENDERING])
        
        try:
            while self.is_running:
                msg = self.kafka_consumer.poll(1.0)
                
                if msg is None:
                    await asyncio.sleep(0.1)
                    continue
                
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    continue
                
                try:
                    # Process the message
                    value = msg.value().decode("utf-8")
                    message = json.loads(value)
                    logger.info(f"Received AR rendering request: {message.get('request_id')}")
                    
                    # Process in a separate task to not block the consumer
                    asyncio.create_task(self.process_message(message))
                    
                except Exception as e:
                    logger.error(f"Error processing AR rendering message: {e}")
        finally:
            self.kafka_consumer.close()
    
    async def consume_asset_messages(self):
        """Consume messages from asset generation results Kafka topic"""
        self.asset_consumer = get_kafka_consumer([TOPIC_ASSET_GENERATION])
        
        try:
            while self.is_running:
                msg = self.asset_consumer.poll(1.0)
                
                if msg is None:
                    await asyncio.sleep(0.1)
                    continue
                
                if msg.error():
                    logger.error(f"Asset consumer error: {msg.error()}")
                    continue
                
                try:
                    # Process the asset message
                    value = msg.value().decode("utf-8")
                    message = json.loads(value)
                    logger.info(f"Received asset generation result: {message.get('request_id')}")
                    
                    # Update asset cache
                    assets = message.get("assets", [])
                    for asset in assets:
                        asset_id = asset.get("id")
                        if asset_id:
                            self.asset_cache[asset_id] = asset
                    
                except Exception as e:
                    logger.error(f"Error processing asset message: {e}")
        finally:
            self.asset_consumer.close()
    
    async def process_message(self, message: Dict[str, Any]):
        """Process an AR rendering message"""
        request_id = message.get("request_id")
        user_id = message.get("user_id")
        assets = message.get("assets", [])
        scene_config = message.get("scene_config", {})
        device_info_data = message.get("device_info", {})
        
        try:
            # Parse device info
            device_info = DeviceInfo(**device_info_data)
            
            # Validate the scene configuration
            if not scene_config:
                logger.warning(f"Received empty scene configuration for request {request_id}")
                await self.send_result(request_id, user_id, {
                    "error": "No scene configuration provided for rendering"
                })
                return
            
            # Convert scene config to ARScene
            scene = ARScene(**scene_config)
            
            # Resolve assets if needed
            scene = await self.resolve_assets(scene, assets)
            
            # Optimize scene for device
            optimized_scene, rendering_options = self.optimize_scene_for_device(scene, device_info)
            
            # Generate scene URL (in a real implementation, this would create the actual scene files)
            scene_url = await self.generate_scene_url(optimized_scene, device_info)
            
            # Generate preview image
            preview_image_url = await self.generate_preview_image(optimized_scene)
            
            # Create renderable scene
            renderable_scene = RenderableARScene(
                id=f"renderable_{uuid.uuid4().hex}",
                original_scene_id=scene.id,
                scene_url=scene_url,
                preview_image_url=preview_image_url,
                scene_data=optimized_scene.dict(),
                scene_format=self.determine_scene_format(device_info),
                rendering_options=rendering_options,
                compatible_devices=self.determine_compatible_devices(device_info),
                metadata={
                    "render_time": datetime.utcnow().isoformat(),
                    "origin_request_id": request_id
                }
            )
            
            # Send the result
            await self.send_result(request_id, user_id, {
                "scene_url": scene_url,
                "render_options": rendering_options,
                "preview_image": preview_image_url,
                "scene_format": renderable_scene.scene_format,
                "compatible_devices": renderable_scene.compatible_devices,
                "original_scene_id": scene.id
            })
            
            logger.info(f"Processed AR rendering for request {request_id}")
            
        except Exception as e:
            logger.error(f"Error processing AR rendering: {e}")
            await self.send_result(request_id, user_id, {
                "error": f"Error processing AR rendering: {str(e)}"
            })
    
    async def resolve_assets(self, scene: ARScene, requested_assets: List[Dict[str, Any]]) -> ARScene:
        """Resolve and attach assets to the scene elements"""
        # Create a copy of the scene to modify
        scene_dict = scene.dict()
        
        # Create a lookup of requested assets by ID
        asset_lookup = {asset.get("id"): asset for asset in requested_assets}
        
        # Update elements with asset information
        for element in scene_dict.get("elements", []):
            # Check if element references an asset
            asset_id = element.get("asset_id")
            if asset_id:
                # Look in requested assets first
                asset = asset_lookup.get(asset_id)
                
                # Fall back to cached assets
                if not asset and asset_id in self.asset_cache:
                    asset = self.asset_cache[asset_id]
                
                if asset:
                    # Update element with asset properties
                    element["model_url"] = asset.get("model_url") or element.get("model_url")
                    element["texture_url"] = asset.get("texture_url") or element.get("texture_url")
                    if "metadata" not in element:
                        element["metadata"] = {}
                    element["metadata"]["asset_source"] = asset.get("source")
                    element["metadata"]["asset_license"] = asset.get("license")
        
        # Create a new ARScene with the updated data
        return ARScene(**scene_dict)
    
    def optimize_scene_for_device(self, scene: ARScene, device_info: DeviceInfo) -> tuple[ARScene, Dict[str, Any]]:
        """Optimize the scene for the target device"""
        scene_dict = scene.dict()
        
        # Determine rendering options based on device
        rendering_options = RenderingOptions()
        
        # Adjust quality based on device type
        if device_info.type == "mobile":
            rendering_options.quality = "medium"
            rendering_options.post_processing = False
            rendering_options.texture_quality = "low"
            rendering_options.render_scale = 0.75
        elif device_info.type == "tablet":
            rendering_options.quality = "medium"
            rendering_options.texture_quality = "medium"
        elif device_info.type == "hmd":
            rendering_options.quality = "high"
            rendering_options.frame_rate_target = 72
        elif device_info.type == "desktop":
            rendering_options.quality = "ultra"
            rendering_options.texture_quality = "high"
        
        # Check for specific device capabilities
        if "webgl2" not in device_info.capabilities:
            rendering_options.lighting_model = "mobile"
            rendering_options.shadows_enabled = False
        
        # Optimize scene based on rendering options
        if rendering_options.quality == "low" or rendering_options.quality == "medium":
            # Simplify lighting
            scene_dict["lights"] = [light for light in scene_dict.get("lights", []) 
                                    if light.get("type") != "spot" and light.get("intensity", 0) > 0.5]
            
            # Reduce maximum concurrent objects
            rendering_options.max_concurrent_objects = 20
        
        # Return optimized scene and rendering options
        return ARScene(**scene_dict), rendering_options.dict()
    
    async def generate_scene_url(self, scene: ARScene, device_info: DeviceInfo) -> str:
        """Generate a URL for the rendered scene"""
        # In a real implementation, this would create actual scene files
        scene_format = self.determine_scene_format(device_info)
        base_url = settings.STATIC_ASSETS_URL or "https://ar-assets.example.com"
        
        return f"{base_url}/scenes/{scene.id}.{scene_format}"
    
    async def generate_preview_image(self, scene: ARScene) -> Optional[str]:
        """Generate a preview image for the scene"""
        # In a real implementation, this would render a preview image
        base_url = settings.STATIC_ASSETS_URL or "https://ar-assets.example.com"
        
        return f"{base_url}/previews/{scene.id}.jpg"
    
    def determine_scene_format(self, device_info: DeviceInfo) -> str:
        """Determine the best scene format for the device"""
        if device_info.os == "iOS":
            return "usdz"
        elif device_info.type == "hmd":
            return "gltf"
        else:
            return "gltf"
    
    def determine_compatible_devices(self, device_info: DeviceInfo) -> List[str]:
        """Determine which devices are compatible with the rendered scene"""
        scene_format = self.determine_scene_format(device_info)
        
        if scene_format == "usdz":
            return ["iOS"]
        elif scene_format == "gltf":
            return ["Android", "Windows", "macOS", "Linux", "Web"]
        else:
            return ["Web"]
    
    async def send_result(self, request_id: str, user_id: str, result: Dict[str, Any]):
        """Send the rendering result back through Kafka"""
        # Prepare result message
        message = {
            "request_id": request_id,
            "user_id": user_id,
            "result_type": "ar_rendering",
            "timestamp": datetime.utcnow().isoformat(),
            **result
        }
        
        # Send to Kafka
        self.kafka_producer.produce(
            f"{settings.KAFKA_TOPIC_PREFIX}{TOPIC_AR_RENDERING}-results",
            json.dumps(message).encode("utf-8")
        )
        self.kafka_producer.flush()
        
        logger.debug(f"Sent AR rendering result for request {request_id}")

# Create singleton instance
ar_rendering_agent = ARRenderingAgent()

# Function to start the agent
async def start_agent():
    await ar_rendering_agent.start()

# Function to stop the agent
async def stop_agent():
    await ar_rendering_agent.stop()

# For direct script execution
if __name__ == "__main__":
    import uvloop
    uvloop.install()
    
    async def main():
        await start_agent()
        
        try:
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            await stop_agent()
    
    asyncio.run(main())
