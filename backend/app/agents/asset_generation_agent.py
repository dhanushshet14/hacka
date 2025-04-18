from typing import Dict, List, Any, Optional, Union, Tuple
import os
import json
import uuid
import tempfile
from pathlib import Path
import asyncio
import httpx
import base64
from pydantic import BaseModel, Field
from loguru import logger

from app.integrations.groq_ai_interface import generate_structured_output, generate_text
from app.integrations.ollama_interface import generate_text as ollama_generate_text
from app.core.config import settings

# Define models for the agent
class AssetRequest(BaseModel):
    """Request model for asset generation"""
    element_id: str
    element_type: str = Field(..., description="Type of element (object, character, environment)")
    name: str = Field(..., description="Name of the element")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Visual attributes")
    description: Optional[str] = None
    style: Optional[str] = None
    format: str = "glb"  # Output format (glb, usdz, etc.)

class AssetResponse(BaseModel):
    """Response model with asset information"""
    element_id: str
    asset_id: str
    name: str
    element_type: str
    url: Optional[str] = None
    local_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    format: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # pending, completed, failed
    error: Optional[str] = None

class SceneAssetMap(BaseModel):
    """Mapping between scene elements and generated assets"""
    scene_id: str
    assets: List[AssetResponse] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Asset storage configuration
ASSET_STORAGE_DIR = Path(settings.ASSET_STORAGE_DIR if hasattr(settings, 'ASSET_STORAGE_DIR') else 'assets')
os.makedirs(ASSET_STORAGE_DIR, exist_ok=True)

# Asset generation prompts
ASSET_PROMPT_TEMPLATE = """
Generate a detailed description for a 3D asset that would represent the following element in an AR scene:

Element Type: {element_type}
Name: {name}
Description: {description}

Attributes:
{attributes}

Style: {style}

Your task is to create a detailed description that could be used to:
1. Search for existing 3D assets in a database
2. Generate a new 3D asset using AI tools
3. Provide guidance for a 3D artist

Include specific details about:
- Visual appearance (color, texture, materials)
- Scale and proportions
- Key identifying features
- Style and artistic direction
- Technical considerations for AR (level of detail, polycount considerations)

Output a detailed, professional description that focuses on visual and technical aspects.
"""

ASSET_SEARCH_QUERY_TEMPLATE = """
Create a search query for finding a 3D {element_type} model that matches this description:

{description}

The search query should:
1. Include the most distinctive visual attributes
2. Specify the style ({style})
3. Be optimized for 3D model repositories 
4. Include technical requirements for AR (low poly, mobile-ready, etc.)

Create a search query with 5-10 keywords separated by spaces:
"""

# Asset databases and APIs
ASSET_REPOSITORIES = {
    "local": {
        "name": "Local Asset Repository",
        "base_url": f"file://{ASSET_STORAGE_DIR.absolute()}/",
        "description": "Local storage for generated and cached assets"
    },
    "polyhaven": {
        "name": "Poly Haven",
        "base_url": "https://polyhaven.com/api/",
        "search_url": "https://polyhaven.com/api/search?q={query}&t={type}",
        "description": "Free 3D assets and HDRIs"
    },
    "sketchfab": {
        "name": "Sketchfab",
        "base_url": "https://sketchfab.com/api/v3/",
        "search_url": "https://sketchfab.com/api/v3/search?q={query}&type=models",
        "description": "Popular 3D model repository"
    }
}

# Helper functions
def create_asset_id(element_id: str, format: str) -> str:
    """Create a unique asset ID based on element ID and format"""
    unique_id = str(uuid.uuid4())[:8]
    return f"{element_id}_{unique_id}.{format}"

async def search_3d_repositories(query: str, element_type: str) -> List[Dict[str, Any]]:
    """
    Search online repositories for 3D assets
    
    Args:
        query: Search query
        element_type: Type of element to search for
        
    Returns:
        List of matching assets with metadata
    """
    results = []
    
    # Mock implementation - in production, this would call actual APIs
    try:
        # Simulate API call delay
        await asyncio.sleep(0.5)
        
        # Create a mock result based on the query
        asset_type_map = {
            "object": "model",
            "character": "character",
            "environment": "scene"
        }
        
        asset_type = asset_type_map.get(element_type.lower(), "model")
        
        # Mock asset result
        mock_result = {
            "name": f"{query.split()[-1].title()} {asset_type.title()}",
            "thumbnail_url": f"https://example.com/thumbnails/{asset_type}/{uuid.uuid4()}.jpg",
            "url": f"https://example.com/assets/{asset_type}/{uuid.uuid4()}.glb",
            "source": "sketchfab",
            "license": "Standard",
            "score": 0.85
        }
        
        results.append(mock_result)
        
        logger.info(f"Found {len(results)} assets for query: {query}")
        
    except Exception as e:
        logger.error(f"Error searching 3D repositories: {e}")
    
    return results

async def generate_prompt_for_asset(asset_request: AssetRequest) -> str:
    """
    Generate a detailed prompt for asset generation
    
    Args:
        asset_request: Asset request with element details
        
    Returns:
        Detailed prompt for asset generation
    """
    # Format attributes as a string
    attributes_str = ""
    for key, value in asset_request.attributes.items():
        attributes_str += f"- {key.replace('_', ' ').title()}: {value}\n"
    
    # Use the template to create the prompt
    prompt = ASSET_PROMPT_TEMPLATE.format(
        element_type=asset_request.element_type,
        name=asset_request.name,
        description=asset_request.description or f"A {asset_request.name}",
        attributes=attributes_str,
        style=asset_request.style or "Realistic"
    )
    
    return prompt

async def generate_search_query(asset_request: AssetRequest, detailed_description: str) -> str:
    """
    Generate a search query for finding assets
    
    Args:
        asset_request: Asset request
        detailed_description: Detailed asset description
        
    Returns:
        Search query
    """
    prompt = ASSET_SEARCH_QUERY_TEMPLATE.format(
        element_type=asset_request.element_type,
        description=detailed_description,
        style=asset_request.style or "Realistic"
    )
    
    # Use Ollama for query generation to keep it simple
    query = await ollama_generate_text(
        prompt=prompt,
        max_tokens=100
    )
    
    # Clean up query
    query = query.strip().replace("\n", " ")
    
    return query

class AssetGenerationAgent:
    """Agent for generating and retrieving 3D assets for AR scenes"""
    
    def __init__(self):
        self.asset_cache = {}  # Cache asset responses
    
    async def process_element(self, element: Dict[str, Any], scene_id: str) -> AssetResponse:
        """
        Process a single scene element and generate/retrieve an appropriate asset
        
        Args:
            element: Scene element from text-to-scene agent
            scene_id: Identifier for the scene
            
        Returns:
            Asset response with URL or local path
        """
        try:
            # Create asset request from element
            element_id = element.get("id", str(uuid.uuid4()))
            
            asset_request = AssetRequest(
                element_id=element_id,
                element_type=element.get("type", "object"),
                name=element.get("name", "Unknown"),
                attributes=element.get("attributes", {}),
                description=element.get("description", None),
                style=element.get("style", "Realistic"),
                format="glb"  # Default format
            )
            
            # Generate asset ID
            asset_id = create_asset_id(element_id, asset_request.format)
            
            # Initialize response
            asset_response = AssetResponse(
                element_id=element_id,
                asset_id=asset_id,
                name=asset_request.name,
                element_type=asset_request.element_type,
                format=asset_request.format,
                status="processing"
            )
            
            # Generate detailed description using Groq AI
            detailed_description = await generate_text(
                prompt=await generate_prompt_for_asset(asset_request),
                temperature=0.7
            )
            
            # Generate search query based on description
            search_query = await generate_search_query(asset_request, detailed_description)
            
            # Search for matching assets
            search_results = await search_3d_repositories(
                query=search_query, 
                element_type=asset_request.element_type
            )
            
            if search_results:
                # Use the best match
                best_match = search_results[0]
                
                # Update asset response
                asset_response.url = best_match.get("url")
                asset_response.thumbnail_url = best_match.get("thumbnail_url")
                asset_response.metadata = {
                    "source": best_match.get("source", "unknown"),
                    "license": best_match.get("license", "unknown"),
                    "match_score": best_match.get("score", 0.0),
                    "search_query": search_query,
                    "description": detailed_description
                }
                asset_response.status = "completed"
                
                # Store in local cache if it's an external URL
                if asset_response.url and not asset_response.url.startswith("file://"):
                    # In production, this would download the asset
                    local_path = ASSET_STORAGE_DIR / asset_id
                    asset_response.local_path = str(local_path)
            else:
                # No matching assets found, provide fallback
                asset_response.local_path = str(ASSET_STORAGE_DIR / "fallback" / f"{asset_request.element_type.lower()}_default.glb")
                asset_response.status = "fallback"
                asset_response.metadata = {
                    "source": "fallback",
                    "description": detailed_description,
                    "search_query": search_query
                }
            
            # Cache the response
            self.asset_cache[asset_id] = asset_response
            
            return asset_response
            
        except Exception as e:
            logger.error(f"Error processing element {element.get('name', 'Unknown')}: {e}")
            
            # Return error response
            return AssetResponse(
                element_id=element.get("id", str(uuid.uuid4())),
                asset_id=f"error_{uuid.uuid4()}",
                name=element.get("name", "Unknown"),
                element_type=element.get("type", "object"),
                format="glb",
                status="failed",
                error=str(e)
            )
    
    async def process_scene(self, scene_data: Dict[str, Any]) -> SceneAssetMap:
        """
        Process an entire scene and generate/retrieve assets for all elements
        
        Args:
            scene_data: Scene data from text-to-scene agent
            
        Returns:
            Scene asset map with all generated assets
        """
        scene_id = scene_data.get("scene_id", str(uuid.uuid4()))
        elements = scene_data.get("elements", [])
        
        # Create scene asset map
        scene_asset_map = SceneAssetMap(
            scene_id=scene_id,
            metadata={
                "scene_name": scene_data.get("scene_name", "Untitled Scene"),
                "timestamp": scene_data.get("timestamp", None),
                "total_elements": len(elements)
            }
        )
        
        # Process each element in parallel
        asset_tasks = [self.process_element(element, scene_id) for element in elements]
        asset_responses = await asyncio.gather(*asset_tasks)
        
        # Add to scene asset map
        scene_asset_map.assets = asset_responses
        
        return scene_asset_map
    
    async def get_asset(self, asset_id: str) -> Optional[AssetResponse]:
        """
        Get an asset by ID from the cache
        
        Args:
            asset_id: Asset identifier
            
        Returns:
            Asset response if found, None otherwise
        """
        return self.asset_cache.get(asset_id)
    
    async def update_asset_metadata(self, asset_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update metadata for an asset
        
        Args:
            asset_id: Asset identifier
            metadata: New metadata
            
        Returns:
            Success status
        """
        if asset_id in self.asset_cache:
            self.asset_cache[asset_id].metadata.update(metadata)
            return True
        return False

# Singleton instance
asset_generation_agent = AssetGenerationAgent()

# Main functions for the API
async def generate_assets_for_scene(scene_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate assets for a scene
    
    Args:
        scene_data: Scene data from text-to-scene agent
        
    Returns:
        Scene asset map as a dictionary
    """
    result = await asset_generation_agent.process_scene(scene_data)
    return result.dict()

async def get_asset_by_id(asset_id: str) -> Dict[str, Any]:
    """
    Get asset details by ID
    
    Args:
        asset_id: Asset identifier
        
    Returns:
        Asset details or error
    """
    asset = await asset_generation_agent.get_asset(asset_id)
    if asset:
        return asset.dict()
    return {"error": "Asset not found", "asset_id": asset_id}
