from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
from typing import List

from app.database import get_db
from app.models.food import FoodResponse
from app.schemas.food import food_response_schema
from app.api.routes.auth import get_current_user
from app.schemas.favorite import favorite_schema

router = APIRouter(
    prefix="/favorites",
    tags=["Favorites"],
)

@router.post("/{food_id}", dependencies=[Depends(get_current_user)])
async def add_favorite(
    food_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add a food to user's favorites"""
    try:
        # Check if food exists
        food = await db["foods"].find_one({"_id": ObjectId(food_id)})
        if not food:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Food not found"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid food ID format"
        )
    
    # Check if already favorited
    existing_favorite = await db["favorites"].find_one({
        "user_id": ObjectId(current_user["_id"]),
        "food_id": ObjectId(food_id)
    })
    
    if existing_favorite:
        return {"message": "Food already in favorites", "id": str(existing_favorite["_id"])}
    
    # Create new favorite
    favorite = {
        "user_id": ObjectId(current_user["_id"]),
        "food_id": ObjectId(food_id),
        "created_at": datetime.utcnow()
    }
    
    result = await db["favorites"].insert_one(favorite)
    
    return {
        "message": "Food added to favorites",
        "id": str(result.inserted_id)
    }

@router.delete("/{food_id}", dependencies=[Depends(get_current_user)])
async def remove_favorite(
    food_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove a food from user's favorites"""
    try:
        result = await db["favorites"].delete_one({
            "user_id": ObjectId(current_user["_id"]),
            "food_id": ObjectId(food_id)
        })
        
        if result.deleted_count:
            return {"message": "Food removed from favorites"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Food not found in favorites"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# Main endpoint - NO trailing slash, but handle both
@router.get("", response_model=List[FoodResponse], dependencies=[Depends(get_current_user)])
@router.get("/", response_model=List[FoodResponse], dependencies=[Depends(get_current_user)])
async def get_favorites(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all favorite foods for the current user"""
    try:
        # Get all favorites for user
        favorites = await db["favorites"].find({
            "user_id": ObjectId(current_user["_id"])
        }).to_list(length=100)
        
        if not favorites:
            return []
        
        # Extract food IDs
        food_ids = [fav["food_id"] for fav in favorites]
        
        # Fetch all favorited foods
        foods = await db["foods"].find({"_id": {"$in": food_ids}}).to_list(length=100)
        
        # Return formatted foods
        return [food_response_schema(food) for food in foods]
    except Exception as e:
        logger.error(f"Error getting favorites: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get favorites: {str(e)}"
        )