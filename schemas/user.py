def user_schema(user) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user["name"],
        "password": user["password"],
        "created_at": user["created_at"]
    }

def user_response_schema(user) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user["name"],
        "created_at": user["created_at"]
    }