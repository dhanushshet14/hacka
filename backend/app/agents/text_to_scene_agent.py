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
from app.integrations.groq_ai_interface import generate_structured_output, generate_text
from app.integrations.langchain_integration import process_with_cot

# Constants
AGENT_NAME = "text_to_scene_agent"
AGENT_DESCRIPTION = "Converts natural language text into structured AR scene parameters"
TOPIC_TEXT_TO_SCENE = "text-to-scene"

# Models
class Vector3(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

class Rotation(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0

class Scale(BaseModel):
    x: float = 1.0
    y: float = 1.0
    z: float = 1.0

class Material(BaseModel):
    type: str  # basic, pbr, standard
    color: Optional[str] = None
    metallic: Optional[float] = None
    roughness: Optional[float] = None
    texture_url: Optional[str] = None
    opacity: Optional[float] = None
    emissive: Optional[bool] = False
    emissive_color: Optional[str] = None
    emissive_intensity: Optional[float] = None

class SceneElement(BaseModel):
    id: str = Field(default_factory=lambda: f"element_{uuid.uuid4().hex[:8]}")
    type: str  # object, character, environment, light, effect
    name: str
    description: Optional[str] = None
    position: Vector3 = Field(default_factory=Vector3)
    rotation: Rotation = Field(default_factory=Rotation)
    scale: Scale = Field(default_factory=Scale)
    material: Optional[Material] = None
    prefab_url: Optional[str] = None
    model_url: Optional[str] = None
    animation: Optional[str] = None
    interactions: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SceneLight(BaseModel):
    id: str = Field(default_factory=lambda: f"light_{uuid.uuid4().hex[:8]}")
    type: str  # directional, point, spot, ambient
    color: str
    intensity: float
    position: Optional[Vector3] = None
    rotation: Optional[Rotation] = None
    range: Optional[float] = None
    cast_shadows: bool = True

class SceneEnvironment(BaseModel):
    skybox: Optional[str] = None
    ambient_light_color: Optional[str] = None
    ambient_light_intensity: Optional[float] = None
    fog_enabled: bool = False
    fog_color: Optional[str] = None
    fog_density: Optional[float] = None
    gravity: Optional[Vector3] = None
    wind: Optional[Vector3] = None

class ARScene(BaseModel):
    id: str = Field(default_factory=lambda: f"scene_{uuid.uuid4().hex}")
    name: str
    description: Optional[str] = None
    elements: List[SceneElement] = Field(default_factory=list)
    lights: List[SceneLight] = Field(default_factory=list)
    environment: SceneEnvironment = Field(default_factory=SceneEnvironment)
    anchoring: Optional[str] = None  # world, surface, image, face, body
    scale: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

# System prompts for scene generation
SCENE_GENERATION_PROMPT = """
You are an AI expert at converting natural language descriptions into detailed 3D scene representations for augmented reality.
Analyze the following text and convert it into a structured scene with 3D elements, positions, and properties.

TEXT TO ANALYZE:
{text}

Your task is to:
1. Identify key objects, characters, and environmental elements
2. Define their 3D positions, rotations, and scales
3. Assign appropriate materials, colors, and textures
4. Set up lighting and environmental parameters
5. Define any interactions or animations

Create a realistic 3D scene representation that could be rendered in AR. Be specific about spatial relationships and visual properties.
Ensure elements have clear positions relative to each other and follow physical constraints of the real world.
"""

SCENE_PARAMS_SCHEMA = {
    "type": "object",
    "properties": {
        "scene": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the scene"},
                "description": {"type": "string", "description": "Description of the scene"},
                "anchoring": {"type": "string", "description": "How the scene should be anchored - world, surface, image, face, or body"},
                "scale": {"type": "number", "description": "Overall scale factor of the scene"}
            },
            "required": ["name"]
        },
        "elements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "description": "Type of element (object, character, environment, light, effect)"},
                    "name": {"type": "string", "description": "Name of the element"},
                    "description": {"type": "string", "description": "Description of the element"},
                    "position": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number"},
                            "y": {"type": "number"},
                            "z": {"type": "number"}
                        },
                        "required": ["x", "y", "z"]
                    },
                    "rotation": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number"},
                            "y": {"type": "number"},
                            "z": {"type": "number"},
                            "w": {"type": "number"}
                        }
                    },
                    "scale": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number"},
                            "y": {"type": "number"},
                            "z": {"type": "number"}
                        }
                    },
                    "material": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "color": {"type": "string"},
                            "metallic": {"type": "number"},
                            "roughness": {"type": "number"},
                            "texture_url": {"type": "string"}
                        },
                        "required": ["type"]
                    },
                    "prefab_url": {"type": "string", "description": "URL to a predefined prefab for this element"},
                    "model_url": {"type": "string", "description": "URL to a 3D model for this element"},
                    "animation": {"type": "string", "description": "Animation to play on this element"},
                    "interactions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "trigger": {"type": "string"},
                                "action": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["type", "name", "position"]
            }
        },
        "lights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "description": "Type of light (directional, point, spot, ambient)"},
                    "color": {"type": "string", "description": "Color of the light in hex format"},
                    "intensity": {"type": "number", "description": "Intensity of the light"},
                    "position": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number"},
                            "y": {"type": "number"},
                            "z": {"type": "number"}
                        }
                    },
                    "cast_shadows": {"type": "boolean", "description": "Whether this light casts shadows"}
                },
                "required": ["type", "color", "intensity"]
            }
        },
        "environment": {
            "type": "object",
            "properties": {
                "skybox": {"type": "string", "description": "URL to skybox texture or predefined skybox name"},
                "ambient_light_color": {"type": "string", "description": "Color of ambient light in hex format"},
                "ambient_light_intensity": {"type": "number", "description": "Intensity of ambient light"},
                "fog_enabled": {"type": "boolean", "description": "Whether fog is enabled"},
                "fog_color": {"type": "string", "description": "Color of fog in hex format"},
                "fog_density": {"type": "number", "description": "Density of fog"}
            }
        }
    },
    "required": ["scene", "elements"]
}

class TextToSceneAgent:
    """Agent that converts text to AR scene parameters"""
    
    def __init__(self):
        self.agent_id = None
        self.kafka_producer = get_kafka_producer()
        self.kafka_consumer = None
        self.consumer_task = None
        self.is_running = False
        
        # Define capabilities
        self.capabilities = [
            AgentCapability(
                name="text_to_scene_conversion",
                description="Converts natural language text into structured AR scene parameters",
                parameters={
                    "text": "The text to convert to scene parameters",
                    "context_id": "Optional context ID for multi-turn conversations",
                    "options": "Optional processing options"
                },
                example={
                    "text": "A red cube floating above a blue sphere on a wooden table",
                    "context_id": "user_12345",
                    "options": {"scene_type": "tabletop", "style": "minimalist"}
                }
            )
        ]
    
    async def start(self):
        """Start the agent, register with MCP, and begin consuming messages"""
        # Register with MCP server
        await self.register_with_mcp()
        
        # Start Kafka consumer
        self.is_running = True
        self.consumer_task = asyncio.create_task(self.consume_messages())
        
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
        
        if self.kafka_consumer:
            self.kafka_consumer.close()
        
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
                            "supported_formats": ["AR", "3D"]
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
        """Consume messages from Kafka topic"""
        self.kafka_consumer = get_kafka_consumer([TOPIC_TEXT_TO_SCENE])
        
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
                    logger.info(f"Received message: {message.get('request_id')}")
                    
                    # Process in a separate task to not block the consumer
                    asyncio.create_task(self.process_message(message))
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        finally:
            self.kafka_consumer.close()
    
    async def process_message(self, message: Dict[str, Any]):
        """Process a text-to-scene message"""
        request_id = message.get("request_id")
        user_id = message.get("user_id")
        text = message.get("text", "")
        context = message.get("context", {})
        options = message.get("options", {})
        
        if not text:
            logger.warning(f"Received empty text for request {request_id}")
            await self.send_result(request_id, user_id, {
                "error": "No text provided for conversion"
            })
            return
        
        try:
            # Use chain-of-thought reasoning to analyze the text
            cot_result = await process_with_cot(
                question=text,
                system_prompt=SCENE_GENERATION_PROMPT.format(text=text),
                provider=options.get("llm_provider", "groq")
            )
            
            # Generate structured scene parameters from the reasoning
            scene_params = await generate_structured_output(
                prompt=f"Based on this reasoning about the text '{text}', generate structured AR scene parameters:\n\n{cot_result['text']}",
                system_prompt="You are an expert at creating structured AR scene parameters from textual descriptions.",
                output_schema=SCENE_PARAMS_SCHEMA,
                temperature=0.2
            )
            
            # Create the AR scene
            scene = self.create_ar_scene(scene_params)
            
            # Send the result
            await self.send_result(request_id, user_id, {
                "scene_params": scene.dict(),
                "reasoning": cot_result["text"],
                "original_text": text
            })
            
            logger.info(f"Processed text-to-scene conversion for request {request_id}")
            
        except Exception as e:
            logger.error(f"Error converting text to scene: {e}")
            await self.send_result(request_id, user_id, {
                "error": f"Error converting text to scene: {str(e)}"
            })
    
    def create_ar_scene(self, scene_params: Dict[str, Any]) -> ARScene:
        """Create an ARScene object from the generated parameters"""
        scene_data = scene_params.get("scene", {})
        elements_data = scene_params.get("elements", [])
        lights_data = scene_params.get("lights", [])
        environment_data = scene_params.get("environment", {})
        
        # Create the scene
        scene = ARScene(
            name=scene_data.get("name", "Generated Scene"),
            description=scene_data.get("description"),
            anchoring=scene_data.get("anchoring", "surface"),
            scale=scene_data.get("scale", 1.0)
        )
        
        # Add elements
        for elem_data in elements_data:
            position_data = elem_data.get("position", {})
            rotation_data = elem_data.get("rotation", {})
            scale_data = elem_data.get("scale", {})
            material_data = elem_data.get("material")
            
            position = Vector3(
                x=position_data.get("x", 0.0),
                y=position_data.get("y", 0.0),
                z=position_data.get("z", 0.0)
            )
            
            rotation = Rotation(
                x=rotation_data.get("x", 0.0),
                y=rotation_data.get("y", 0.0),
                z=rotation_data.get("z", 0.0),
                w=rotation_data.get("w", 1.0)
            )
            
            scale = Scale(
                x=scale_data.get("x", 1.0),
                y=scale_data.get("y", 1.0),
                z=scale_data.get("z", 1.0)
            )
            
            material = None
            if material_data:
                material = Material(
                    type=material_data.get("type", "basic"),
                    color=material_data.get("color"),
                    metallic=material_data.get("metallic"),
                    roughness=material_data.get("roughness"),
                    texture_url=material_data.get("texture_url"),
                    opacity=material_data.get("opacity"),
                    emissive=material_data.get("emissive", False),
                    emissive_color=material_data.get("emissive_color"),
                    emissive_intensity=material_data.get("emissive_intensity")
                )
            
            element = SceneElement(
                type=elem_data.get("type", "object"),
                name=elem_data.get("name", f"Element {len(scene.elements) + 1}"),
                description=elem_data.get("description"),
                position=position,
                rotation=rotation,
                scale=scale,
                material=material,
                prefab_url=elem_data.get("prefab_url"),
                model_url=elem_data.get("model_url"),
                animation=elem_data.get("animation"),
                interactions=elem_data.get("interactions", []),
                metadata=elem_data.get("metadata", {})
            )
            
            scene.elements.append(element)
        
        # Add lights
        for light_data in lights_data:
            position_data = light_data.get("position", {})
            
            position = None
            if position_data:
                position = Vector3(
                    x=position_data.get("x", 0.0),
                    y=position_data.get("y", 0.0),
                    z=position_data.get("z", 0.0)
                )
            
            light = SceneLight(
                type=light_data.get("type", "directional"),
                color=light_data.get("color", "#FFFFFF"),
                intensity=light_data.get("intensity", 1.0),
                position=position,
                cast_shadows=light_data.get("cast_shadows", True)
            )
            
            scene.lights.append(light)
        
        # Set environment
        if environment_data:
            scene.environment = SceneEnvironment(
                skybox=environment_data.get("skybox"),
                ambient_light_color=environment_data.get("ambient_light_color"),
                ambient_light_intensity=environment_data.get("ambient_light_intensity"),
                fog_enabled=environment_data.get("fog_enabled", False),
                fog_color=environment_data.get("fog_color"),
                fog_density=environment_data.get("fog_density"),
                gravity=environment_data.get("gravity"),
                wind=environment_data.get("wind")
            )
        
        return scene
    
    async def send_result(self, request_id: str, user_id: str, result: Dict[str, Any]):
        """Send the processing result back through Kafka"""
        # Prepare result message
        message = {
            "request_id": request_id,
            "user_id": user_id,
            "result_type": "text_to_scene",
            "timestamp": datetime.utcnow().isoformat(),
            **result
        }
        
        # Send to Kafka
        self.kafka_producer.produce(
            f"{settings.KAFKA_TOPIC_PREFIX}{TOPIC_TEXT_TO_SCENE}-results",
            json.dumps(message).encode("utf-8")
        )
        self.kafka_producer.flush()
        
        logger.debug(f"Sent result for request {request_id}")

# Create singleton instance
text_to_scene_agent = TextToSceneAgent()

# Function to start the agent
async def start_agent():
    await text_to_scene_agent.start()

# Function to stop the agent
async def stop_agent():
    await text_to_scene_agent.stop()

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
