from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from bson import ObjectId
from app.database import get_db
from app.models.food import FoodResponse
from app.schemas.food import food_response_schema
from app.api.routes.auth import get_current_user
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.utils.jwt import SECRET_KEY, ALGORITHM

# Add the generate_unique_id_str function if it doesn't exist
def generate_unique_id_str():
    return str(ObjectId())

# Updated router configuration with CORS options
router = APIRouter(
    prefix="/foods",
    tags=["Foods"],
)

# Function to get optional current user
async def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if not authorization:
        return None
    
    try:
        # Your existing code for token validation
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
            
        # Return user from database
        user = await db.users.find_one({"username": username})
        if user:
            return user
        return None
    except (JWTError, Exception):
        return None

@router.get("/", response_model=List[FoodResponse])
async def get_foods(
    skip: int = 0,
    limit: int = 10,
    category: Optional[str] = None,
    sort_by: str = "name",
    sort_desc: bool = False,
    current_user: dict = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get a list of foods with optional pagination, filtering and sorting.
    """
    filter_query = {}
    if category:
        filter_query["category"] = category
    
    sort_direction = -1 if sort_desc else 1
    
    cursor = db.foods.find(filter_query).skip(skip).limit(limit).sort(sort_by, sort_direction)
    foods = await cursor.to_list(length=limit)
    
    # Transform the foods data to include favorite status
    if current_user:
        user_id = current_user["_id"]
        favorites = await db.favorites.find({"user_id": user_id}).to_list(length=None)
        favorite_food_ids = [str(fav["food_id"]) for fav in favorites]
        
        for food in foods:
            food["is_favorite"] = str(food["_id"]) in favorite_food_ids
    
    return [food_response_schema(food) for food in foods]

@router.get("/{food_id}", response_model=FoodResponse)
async def get_food(
    food_id: str,
    current_user: dict = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get a specific food by ID.
    """
    try:
        food = await db.foods.find_one({"_id": ObjectId(food_id)})
        if not food:
            raise HTTPException(status_code=404, detail="Food not found")
            
        # Include favorite status if user is authenticated
        if current_user:
            favorite = await db.favorites.find_one({
                "user_id": current_user["_id"],
                "food_id": ObjectId(food_id)
            })
            food["is_favorite"] = favorite is not None
        
        return food_response_schema(food)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Food not found")

@router.get("/search/", response_model=List[FoodResponse])
async def search_foods(
    q: str,
    limit: int = 10,
    current_user: dict = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Search for foods by name or description.
    """
    query = {"$or": [
        {"name": {"$regex": q, "$options": "i"}},
        {"description": {"$regex": q, "$options": "i"}},
        {"nameSinhala": {"$regex": q, "$options": "i"}},
        {"nameTamil": {"$regex": q, "$options": "i"}},
    ]}
    
    foods = await db.foods.find(query).limit(limit).to_list(length=limit)
    
    # Include favorite status if user is authenticated
    if current_user:
        user_id = current_user["_id"]
        favorites = await db.favorites.find({"user_id": user_id}).to_list(length=None)
        favorite_food_ids = [str(fav["food_id"]) for fav in favorites]
        
        for food in foods:
            food["is_favorite"] = str(food["_id"]) in favorite_food_ids
    
    return [food_response_schema(food) for food in foods]