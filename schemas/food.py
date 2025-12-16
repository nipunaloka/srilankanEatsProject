def food_schema(food) -> dict:
    return {
        "id": str(food["_id"]),
        "name": food["name"],
        "name_sinhala": food.get("name_sinhala"),
        "name_tamil": food.get("name_tamil"),
        "description": food["description"],
        "ingredients": food["ingredients"],
        "preparation_method": food.get("preparation_method"),
        "cultural_significance": food.get("cultural_significance"),
        "category": food["category"],
        "image_url": food.get("image_url")
    }

def food_response_schema(food, is_favorite=False) -> dict:
    return {
        "id": str(food["_id"]),
        "name": food["name"],
        "name_sinhala": food.get("name_sinhala"),
        "name_tamil": food.get("name_tamil"),
        "description": food["description"],
        "ingredients": food["ingredients"],
        "preparation_method": food.get("preparation_method"),
        "cultural_significance": food.get("cultural_significance"),
        "category": food["category"],
        "image_url": food.get("image_url"),
        "is_favorite": is_favorite,
        "avg_rating": food.get("avg_rating", 0),
        "rating_count": food.get("rating_count", 0)
    }