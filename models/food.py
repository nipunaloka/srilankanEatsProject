from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
        
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
        
    @classmethod
    def __get_pydantic_json_schema__(cls, _):
        return {"type": "string"}

class FoodResponse(BaseModel):
    id: str
    name: str
    name_sinhala: Optional[str] = None
    name_tamil: Optional[str] = None
    description: str
    ingredients: List[str]
    preparation_method: Optional[str] = None
    cultural_significance: Optional[str] = None
    category: str
    is_favorite: bool = False
    avg_rating: float = 0
    rating_count: int = 0
    image_url: Optional[str] = None
    
    model_config = {
        "from_attributes": True,
        "json_encoders": {ObjectId: str}
    }