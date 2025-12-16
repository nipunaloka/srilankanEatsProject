from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
from typing import List

from app.database import get_db
from app.models.review import ReviewCreate, ReviewUpdate, ReviewResponse
from app.schemas.review import review_schema
from app.api.routes.auth import get_current_user

router = APIRouter(
    tags=["Reviews"]
)

# NEW ROUTES - Match Flutter expectations

@router.get("/reviews/food/{food_id}", response_model=List[ReviewResponse])
async def get_reviews_by_food(
    food_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50)
):
    """Get all reviews for a specific food item"""
    try:
        # Check if food exists
        food = await db["foods"].find_one({"_id": ObjectId(food_id)})
        if not food:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Food not found"
            )
            
        # Get reviews
        cursor = db["reviews"].find({"food_id": ObjectId(food_id)}).sort([("created_at", -1)]).skip(skip).limit(limit)
        reviews = await cursor.to_list(length=limit)
        
        result = []
        for review in reviews:
            review_dict = review_schema(review)
            result.append(review_dict)
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        if "Invalid" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid food ID format"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/reviews/user", response_model=List[ReviewResponse])
async def get_user_reviews(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all reviews by the current user"""
    try:
        cursor = db["reviews"].find({"user_id": ObjectId(current_user["_id"])}).sort([("created_at", -1)])
        reviews = await cursor.to_list(length=None)
        
        result = []
        for review in reviews:
            review_dict = review_schema(review)
            result.append(review_dict)
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    review_data: ReviewCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new review"""
    try:
        # Check if food exists
        food = await db["foods"].find_one({"_id": ObjectId(review_data.food_id)})
        if not food:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Food not found"
            )
        
        # Check if user already reviewed this food
        existing_review = await db["reviews"].find_one({
            "user_id": ObjectId(current_user["_id"]),
            "food_id": ObjectId(review_data.food_id)
        })
        
        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this food item"
            )
        
        # Create new review
        review = {
            "food_id": ObjectId(review_data.food_id),
            "user_id": ObjectId(current_user["_id"]),
            "user_name": current_user.get("name", "Anonymous"),
            "rating": review_data.rating,
            "comment": review_data.comment or "",
            "created_at": datetime.utcnow()
        }
        
        result = await db["reviews"].insert_one(review)
        created_review = await db["reviews"].find_one({"_id": result.inserted_id})
        
        # Update food's average rating
        await update_food_rating(db, review_data.food_id)
        
        return review_schema(created_review)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: str,
    review_data: ReviewUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update an existing review"""
    try:
        # Check if review exists and belongs to current user
        review = await db["reviews"].find_one({
            "_id": ObjectId(review_id),
            "user_id": ObjectId(current_user["_id"])
        })
        
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found or you are not the author"
            )
            
        # Update review
        update_data = {}
        if review_data.rating is not None:
            update_data["rating"] = review_data.rating
        if review_data.comment is not None:
            update_data["comment"] = review_data.comment
            
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
            
        update_data["updated_at"] = datetime.utcnow()
        
        await db["reviews"].update_one(
            {"_id": ObjectId(review_id)},
            {"$set": update_data}
        )
        
        # Get updated review
        updated_review = await db["reviews"].find_one({"_id": ObjectId(review_id)})
        
        # Update food's average rating
        await update_food_rating(db, str(review["food_id"]))
        
        return review_schema(updated_review)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/reviews/{review_id}", status_code=status.HTTP_200_OK)
async def delete_review(
    review_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a review"""
    try:
        # Check if review exists and belongs to current user
        review = await db["reviews"].find_one({
            "_id": ObjectId(review_id),
            "user_id": ObjectId(current_user["_id"])
        })
        
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found or you are not the author"
            )
        
        food_id = str(review["food_id"])
            
        # Delete review
        await db["reviews"].delete_one({"_id": ObjectId(review_id)})
        
        # Update food's average rating
        await update_food_rating(db, food_id)
        
        return {"message": "Review deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# KEEP OLD ROUTES for backward compatibility
@router.post("/foods/{food_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review_legacy(
    food_id: str,
    review_data: ReviewCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Legacy endpoint - create review"""
    # Override food_id from URL parameter
    review_data.food_id = food_id
    return await create_review(review_data, db, current_user)

@router.get("/foods/{food_id}/reviews", response_model=List[ReviewResponse])
async def get_food_reviews_legacy(
    food_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50)
):
    """Legacy endpoint - get food reviews"""
    return await get_reviews_by_food(food_id, db, skip, limit)

@router.put("/foods/{food_id}/reviews/{review_id}", response_model=ReviewResponse)
async def update_review_legacy(
    food_id: str,
    review_id: str,
    review_data: ReviewUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Legacy endpoint - update review"""
    return await update_review(review_id, review_data, db, current_user)

@router.delete("/foods/{food_id}/reviews/{review_id}", status_code=status.HTTP_200_OK)
async def delete_review_legacy(
    food_id: str,
    review_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Legacy endpoint - delete review"""
    return await delete_review(review_id, db, current_user)

async def update_food_rating(db: AsyncIOMotorDatabase, food_id: str):
    """Update the average rating for a food item"""
    try:
        pipeline = [
            {"$match": {"food_id": ObjectId(food_id)}},
            {"$group": {
                "_id": None,
                "avg_rating": {"$avg": "$rating"},
                "count": {"$sum": 1}
            }}
        ]
        
        result = await db["reviews"].aggregate(pipeline).to_list(length=1)
        
        if not result:
            update_data = {
                "rating": 0.0,
                "rating_count": 0
            }
        else:
            update_data = {
                "rating": round(result[0]["avg_rating"], 1),
                "rating_count": result[0]["count"]
            }
        
        await db["foods"].update_one(
            {"_id": ObjectId(food_id)},
            {"$set": update_data}
        )
    except Exception as e:
        # Log error but don't fail the review operation
        print(f"Error updating food rating: {e}")