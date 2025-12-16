from datetime import datetime

def favorite_schema(favorite) -> dict:
    """Convert favorite MongoDB document to API response format"""
    return {
        "id": str(favorite["_id"]),
        "user_id": str(favorite["user_id"]),
        "food_id": str(favorite["food_id"]),
        "created_at": favorite["created_at"]
    }