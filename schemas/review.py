from datetime import datetime

def review_schema(review, user_name=None) -> dict:
    """Convert review MongoDB document to API response format"""
    return {
        "id": str(review["_id"]),
        "food_id": str(review["food_id"]),
        "user_id": str(review["user_id"]),
        "user_name": user_name or review.get("user_name", "Unknown User"),
        "rating": review["rating"],
        "comment": review.get("comment"),
        "created_at": review["created_at"],
        "updated_at": review.get("updated_at")
    }