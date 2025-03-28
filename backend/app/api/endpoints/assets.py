from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, status, Depends
from pydantic import BaseModel, Field
from loguru import logger

from app.agents.asset_generation_agent import (
    generate_assets_for_scene,
    get_asset_by_id,
    AssetRequest,
    AssetResponse,
    SceneAssetMap,
    asset_generation_agent
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/assets", tags=["assets"])

# API Models
class SceneAssetsRequest(BaseModel):
    """Request model for scene assets generation"""
    scene_id: str = Field(..., description="Unique identifier for the scene")
    scene_name: Optional[str] = Field(None, description="Name of the scene")
    elements: List[Dict[str, Any]] = Field(..., description="Scene elements to generate assets for")
    timestamp: Optional[str] = None
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Asset generation options")

class ElementAssetRequest(BaseModel):
    """Request model for single element asset generation"""
    element: Dict[str, Any] = Field(..., description="Scene element to generate asset for")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Asset generation options")

class AssetTaskResponse(BaseModel):
    """Response model for asset generation task"""
    task_id: str
    status: str
    message: str

# Background tasks processing
async def process_scene_assets_task(scene_data: Dict[str, Any]):
    """Background task for scene assets processing"""
    try:
        await generate_assets_for_scene(scene_data)
        logger.info(f"Completed asset generation for scene: {scene_data.get('scene_id')}")
    except Exception as e:
        logger.error(f"Error in background asset generation: {e}")

@router.post("/generate", response_model=Dict[str, Any])
async def generate_scene_assets(
    request: SceneAssetsRequest,
    background_tasks: BackgroundTasks,
    run_async: bool = False,
    current_user = Depends(get_current_user)
):
    """
    Generate assets for all elements in a scene
    
    When run_async is True, the processing happens in the background and 
    the endpoint returns immediately with a task ID.
    """
    try:
        # Add user info to the request
        scene_data = request.dict()
        scene_data["user_id"] = current_user.id
        
        if run_async:
            # Add the task to background processing
            task_id = f"asset_gen_{request.scene_id}"
            background_tasks.add_task(process_scene_assets_task, scene_data)
            
            return {
                "task_id": task_id,
                "status": "processing",
                "message": f"Asset generation started for scene: {request.scene_id}"
            }
        else:
            # Process synchronously
            result = await generate_assets_for_scene(scene_data)
            return result
            
    except Exception as e:
        logger.error(f"Error generating assets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating assets: {str(e)}"
        )

@router.post("/generate-single", response_model=AssetResponse)
async def generate_single_asset(
    request: ElementAssetRequest,
    current_user = Depends(get_current_user)
):
    """Generate asset for a single scene element"""
    try:
        # Generate a fake scene ID for context
        scene_id = f"single_{request.element.get('id', 'unknown')}"
        
        # Process the element
        result = await asset_generation_agent.process_element(
            element=request.element,
            scene_id=scene_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating single asset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating asset: {str(e)}"
        )

@router.get("/{asset_id}", response_model=Dict[str, Any])
async def get_asset(asset_id: str):
    """Get asset by ID"""
    try:
        result = await get_asset_by_id(asset_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving asset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving asset: {str(e)}"
        )

@router.get("/scene/{scene_id}", response_model=Dict[str, Any])
async def get_scene_assets(scene_id: str):
    """Get all assets for a scene"""
    try:
        # In a real implementation, this would query a database
        # For now, we'll return an empty list since we don't persist scene-asset mappings
        return {
            "scene_id": scene_id,
            "assets": [],
            "message": "Scene asset retrieval not implemented in this version"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving scene assets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving scene assets: {str(e)}"
        ) 