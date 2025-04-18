from typing import Dict, Any, Optional, List, Union
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
import json
import uuid
import os
import aiofiles
from datetime import datetime, timedelta
import jwt
from pathlib import Path
import base64

from app.core.config import settings
from app.api.auth import get_current_user
from app.models.user import User
from app.integrations.tts import convert_text_to_speech
from app.mcp.mcp_server import mcp_server

router = APIRouter(prefix=f"{settings.API_V1_STR}/ar", tags=["ar"])

# AR Framework Selection
class ARFramework(str):
    WEBXR = "webxr"
    THREEJS = "threejs"
    BABYLONJS = "babylonjs"

# Models
class ARSceneRequest(BaseModel):
    scene_id: str
    user_id: Optional[str] = None
    audio_enabled: bool = True
    framework: ARFramework = ARFramework.WEBXR
    device_info: Dict[str, Any] = Field(default_factory=dict)
    options: Dict[str, Any] = Field(default_factory=dict)
    narration_text: Optional[str] = None

class ARSceneResponse(BaseModel):
    session_id: str
    scene_url: str
    audio_url: Optional[str] = None
    expires_at: datetime
    token: str
    framework: str
    config: Dict[str, Any] = Field(default_factory=dict)

# Static files directory for AR scenes
STATIC_DIR = Path(settings.STATIC_FILES_DIR) / "ar_scenes"
os.makedirs(STATIC_DIR, exist_ok=True)

# Functions to generate AR scene files
async def generate_webxr_scene(scene_data: Dict[str, Any], scene_id: str) -> str:
    """Generate WebXR scene HTML file from scene data"""
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Aetherion AR Scene</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
        <script src="https://aframe.io/releases/1.4.0/aframe.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/mind-ar@1.2.2/dist/mindar-image-aframe.prod.js"></script>
        <style>
          body {
            margin: 0;
            overflow: hidden;
          }
          .ar-container {
            position: absolute;
            width: 100%;
            height: 100%;
            overflow: hidden;
          }
        </style>
    </head>
    <body>
        <div class="ar-container">
            <a-scene 
                embedded
                webxr="requiredFeatures: hit-test,local-floor,hand-tracking;"
                renderer="colorManagement: true; physicallyCorrectLights: true;"
                xr-mode-ui="enabled: true;">
                
                <!-- Assets -->
                <a-assets>
                    <!-- Audio source for narration -->
                    <audio id="narration" src="AUDIO_URL" preload="auto"></audio>
                    <!-- Scene-specific assets -->
                    SCENE_ASSETS
                </a-assets>
                
                <!-- Environment -->
                <a-entity environment="ENVIRONMENT_SETTINGS"></a-entity>
                
                <!-- Scene elements -->
                SCENE_ELEMENTS
                
                <!-- Scene lights -->
                SCENE_LIGHTS
                
                <!-- Camera with cursor for interaction -->
                <a-entity camera look-controls wasd-controls position="0 1.6 0">
                    <a-entity cursor="fuse: false; rayOrigin: mouse;"
                        position="0 0 -1"
                        geometry="primitive: ring; radiusInner: 0.02; radiusOuter: 0.03;"
                        material="color: white; shader: flat">
                    </a-entity>
                </a-entity>
                
                <!-- Sound entity for narration -->
                <a-entity sound="src: #narration; autoplay: true; loop: false; volume: 1.0;"></a-entity>
            </a-scene>
        </div>
        <script>
            // Scene configuration and runtime logic
            const sceneConfig = SCENE_CONFIG;
            
            // Initialize AR session
            document.addEventListener('DOMContentLoaded', function() {
                // Setup scene based on configuration
                console.log('AR Scene initialized with config:', sceneConfig);
                
                // Handle AR session events
                const scene = document.querySelector('a-scene');
                scene.addEventListener('enter-vr', function() {
                    console.log('Entered AR mode');
                    // Play narration when AR mode is entered
                    const narration = document.querySelector('#narration');
                    if (narration) {
                        narration.play();
                    }
                });
            });
        </script>
    </body>
    </html>
    """
    
    # Process scene elements
    scene_assets = ""
    scene_elements = ""
    scene_lights = ""
    
    # Process environment settings
    env_settings = ""
    if "environment" in scene_data:
        env = scene_data["environment"]
        env_params = []
        
        if "skybox" in env:
            env_params.append(f"preset: {env['skybox']}")
        
        if "fog_enabled" in env and env["fog_enabled"]:
            env_params.append("fog: true")
            if "fog_density" in env:
                env_params.append(f"fogDensity: {env['fog_density']}")
            if "fog_color" in env:
                env_params.append(f"fogColor: {env['fog_color']}")
        
        if "ambient_light_color" in env:
            env_params.append(f"lightPosition: {env.get('ambient_light_color', '#ffffff')}")
        
        env_settings = ";".join(env_params)
    
    # Process assets
    for i, element in enumerate(scene_data.get("elements", [])):
        if element.get("model_url"):
            asset_id = f"model-{i}"
            scene_assets += f'<a-asset-item id="{asset_id}" src="{element["model_url"]}"></a-asset-item>\n'
    
    # Process elements
    for i, element in enumerate(scene_data.get("elements", [])):
        el_id = element.get("id", f"element-{i}")
        el_type = element.get("type", "object")
        position = element.get("position", {"x": 0, "y": 0, "z": 0})
        rotation = element.get("rotation", {"x": 0, "y": 0, "z": 0, "w": 1})
        scale = element.get("scale", {"x": 1, "y": 1, "z": 1})
        
        # Convert position to string
        pos_str = f"{position['x']} {position['y']} {position['z']}"
        
        # Convert rotation from quaternion to euler (simplified)
        rot_str = f"{rotation['x']} {rotation['y']} {rotation['z']}"
        
        # Convert scale to string
        scale_str = f"{scale['x']} {scale['y']} {scale['z']}"
        
        if el_type == "object" and element.get("model_url"):
            # 3D model element
            asset_id = f"model-{i}"
            scene_elements += f'<a-entity id="{el_id}" gltf-model="#{asset_id}" position="{pos_str}" rotation="{rot_str}" scale="{scale_str}"></a-entity>\n'
        elif el_type == "object":
            # Primitive shape with material
            material = element.get("material", {})
            material_type = material.get("type", "basic")
            color = material.get("color", "#ffffff")
            
            primitive = "box"  # Default shape
            if "primitive" in element:
                primitive = element["primitive"]
                
            scene_elements += f'<a-{primitive} id="{el_id}" position="{pos_str}" rotation="{rot_str}" scale="{scale_str}" color="{color}"></a-{primitive}>\n'
    
    # Process lights
    for i, light in enumerate(scene_data.get("lights", [])):
        light_id = light.get("id", f"light-{i}")
        light_type = light.get("type", "directional")
        color = light.get("color", "#ffffff")
        intensity = light.get("intensity", 1.0)
        position = light.get("position", {"x": 0, "y": 3, "z": 0})
        
        # Convert position to string
        pos_str = f"{position['x']} {position['y']} {position['z']}" if position else "0 3 0"
        
        scene_lights += f'<a-{light_type}-light id="{light_id}" color="{color}" intensity="{intensity}" position="{pos_str}"></a-{light_type}-light>\n'
    
    # Create the scene HTML with placeholders replaced
    scene_html = template.replace("SCENE_ASSETS", scene_assets)
    scene_html = scene_html.replace("SCENE_ELEMENTS", scene_elements)
    scene_html = scene_html.replace("SCENE_LIGHTS", scene_lights)
    scene_html = scene_html.replace("ENVIRONMENT_SETTINGS", env_settings)
    scene_html = scene_html.replace("SCENE_CONFIG", json.dumps(scene_data))
    scene_html = scene_html.replace("AUDIO_URL", f"./audio_{scene_id}.mp3")
    
    # Save the HTML file
    file_path = STATIC_DIR / f"scene_{scene_id}.html"
    async with aiofiles.open(file_path, "w") as f:
        await f.write(scene_html)
    
    return f"/static/ar_scenes/scene_{scene_id}.html"

async def generate_threejs_scene(scene_data: Dict[str, Any], scene_id: str) -> str:
    """Generate Three.js scene HTML file from scene data"""
    # Similar implementation as WebXR but using Three.js
    # For brevity, returning the same as WebXR implementation
    return await generate_webxr_scene(scene_data, scene_id)

async def generate_babylonjs_scene(scene_data: Dict[str, Any], scene_id: str) -> str:
    """Generate Babylon.js scene HTML file from scene data"""
    # Similar implementation as WebXR but using Babylon.js
    # For brevity, returning the same as WebXR implementation
    return await generate_webxr_scene(scene_data, scene_id)

async def generate_scene_files(
    scene_data: Dict[str, Any], 
    session_id: str, 
    framework: str,
    narration_text: Optional[str] = None
) -> Dict[str, str]:
    """Generate scene files based on the selected framework and save to disk"""
    scene_id = scene_data.get("id", session_id)
    
    # Generate framework-specific scene file
    scene_url = ""
    if framework == ARFramework.WEBXR:
        scene_url = await generate_webxr_scene(scene_data, scene_id)
    elif framework == ARFramework.THREEJS:
        scene_url = await generate_threejs_scene(scene_data, scene_id)
    elif framework == ARFramework.BABYLONJS:
        scene_url = await generate_babylonjs_scene(scene_data, scene_id)
    
    # Generate audio file if narration is provided
    audio_url = None
    if narration_text:
        audio_data = await convert_text_to_speech(
            text=narration_text,
            provider="elevenlabs" if settings.ELEVENLABS_API_KEY else "openai",
            output_format="mp3"
        )
        
        # Save audio file
        audio_path = STATIC_DIR / f"audio_{scene_id}.mp3"
        async with aiofiles.open(audio_path, "wb") as f:
            await f.write(audio_data)
        
        audio_url = f"/static/ar_scenes/audio_{scene_id}.mp3"
    
    return {
        "scene_url": scene_url,
        "audio_url": audio_url
    }

# Endpoints
@router.post("/render", response_model=ARSceneResponse)
async def render_ar_scene(
    request: ARSceneRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Render an AR scene based on parameters from MCP server and
    return a session token or URL for clients to load the interactive AR experience
    with both visual and audio outputs.
    """
    try:
        # Prepare a request to the MCP server to get scene parameters
        mcp_request = {
            "action": "ar_rendering",
            "user_id": str(current_user.id) if current_user else (request.user_id or "anonymous"),
            "data": {
                "scene_id": request.scene_id,
                "device_info": request.device_info,
                "options": request.options
            }
        }
        
        # Request scene parameters from MCP server
        response = await mcp_server.handle_request(mcp_request)
        
        if not response.success or not response.data.get("scene_params"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.message or "Failed to get scene parameters from MCP server"
            )
        
        # Get scene parameters from the response
        scene_params = response.data.get("scene_params", {})
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Set expiration time for session (24 hours)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # Generate JWT token for authentication
        token_data = {
            "session_id": session_id,
            "user_id": str(current_user.id) if current_user else (request.user_id or "anonymous"),
            "scene_id": request.scene_id,
            "exp": expires_at.timestamp()
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")
        
        # Generate scene files based on framework
        files = await generate_scene_files(
            scene_data=scene_params,
            session_id=session_id,
            framework=request.framework,
            narration_text=request.narration_text if request.audio_enabled else None
        )
        
        scene_url = files["scene_url"]
        audio_url = files["audio_url"]
        
        # Construct the response
        ar_session = ARSceneResponse(
            session_id=session_id,
            scene_url=f"{settings.BASE_URL}{scene_url}",
            audio_url=f"{settings.BASE_URL}{audio_url}" if audio_url else None,
            expires_at=expires_at,
            token=token,
            framework=request.framework,
            config={
                "scene_id": request.scene_id,
                "audio_enabled": request.audio_enabled and audio_url is not None,
                "device_info": request.device_info,
                "options": request.options
            }
        )
        
        # Schedule cleanup of temporary files after expiration
        background_tasks.add_task(
            cleanup_session_files, 
            session_id=session_id, 
            scene_id=scene_params.get("id", request.scene_id), 
            delay=86400  # 24 hours
        )
        
        return ar_session
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rendering AR scene: {str(e)}"
        )

@router.get("/session/{session_id}")
async def get_ar_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get information about an existing AR session
    """
    try:
        # Validate the session token
        # In a real implementation, this would query a database for session data
        # For now, we'll reconstruct the session URL based on the ID
        
        scene_file = STATIC_DIR / f"scene_{session_id}.html"
        audio_file = STATIC_DIR / f"audio_{session_id}.mp3"
        
        if not os.path.exists(scene_file):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"AR session {session_id} not found"
            )
        
        # Return session information
        return {
            "session_id": session_id,
            "scene_url": f"{settings.BASE_URL}/static/ar_scenes/scene_{session_id}.html",
            "audio_url": f"{settings.BASE_URL}/static/ar_scenes/audio_{session_id}.mp3" if os.path.exists(audio_file) else None,
            "status": "active"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving AR session: {str(e)}"
        )

async def cleanup_session_files(session_id: str, scene_id: str, delay: int = 86400):
    """
    Cleanup session files after they expire
    """
    await asyncio.sleep(delay)
    
    try:
        # Remove scene file
        scene_file = STATIC_DIR / f"scene_{scene_id}.html"
        if os.path.exists(scene_file):
            os.unlink(scene_file)
        
        # Remove audio file
        audio_file = STATIC_DIR / f"audio_{scene_id}.mp3"
        if os.path.exists(audio_file):
            os.unlink(audio_file)
            
        logger.info(f"Cleaned up files for expired AR session {session_id}")
    except Exception as e:
        logger.error(f"Error cleaning up session files for {session_id}: {str(e)}")
