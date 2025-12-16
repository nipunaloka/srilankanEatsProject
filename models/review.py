from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class ReviewCreate(BaseModel):
    food_id: str  # ADD THIS - Required for creating review
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = Field(None, max_length=1000)

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('rating', 'comment')
    @classmethod
    def check_at_least_one_field(cls, v, info):
        # At least one field should be provided
        if v is None and not info.data:
            raise ValueError("At least one field must be provided for update")
        return v

class ReviewResponse(BaseModel):
    id: str
    food_id: str
    user_id: str
    user_name: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True
    }