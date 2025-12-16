import os
import logging
from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel
import json
import random

router = APIRouter(tags=["prediction"])
logger = logging.getLogger(__name__)

# Try to load ML dependencies
ML_AVAILABLE = False
model = None
preprocess_image = None

try:
    import numpy as np
    from app.utils.utils import preprocess_image as _preprocess_image
    from app.model_loader import get_model
    
    preprocess_image = _preprocess_image
    model = get_model()
    ML_AVAILABLE = True
    logger.info("✅ ML model loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ ML dependencies not available: {e}")
except Exception as e:
    logger.warning(f"⚠️ Could not load ML model: {e}")

# IMPORTANT: These are the ONLY foods the ML model is trained on
TRAINED_FOODS = ["asmi", "egg_hoppers", "kokis", "kottu", "pol_roti"]

class PredictionResponse(BaseModel):
    prediction: str
    confidence: float
    food_info: dict
    ml_available: bool
    method: str
    message: str = ""

def is_valid_image(content_type: str, file_content: bytes) -> bool:
    """Check if file is a valid image"""
    valid_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif']
    if content_type and any(t in content_type.lower() for t in valid_types):
        return True
    
    if len(file_content) < 12:
        return False
    
    # Check file signatures
    if file_content[:2] == b'\xff\xd8':  # JPEG
        return True
    if file_content[:8] == b'\x89PNG\r\n\x1a\n':  # PNG
        return True
    if file_content[:6] in (b'GIF87a', b'GIF89a'):  # GIF
        return True
    if file_content[8:12] == b'WEBP':  # WebP
        return True
    
    return False

def normalize_food_name(name: str) -> str:
    """Normalize food name for matching"""
    return name.lower().replace(" ", "_").replace("-", "_")

async def get_food_info_from_db(food_name: str):
    """Get food info from MongoDB database"""
    try:
        from app.database import get_database
        db = await get_database()
        
        # Try exact match first
        food = await db.foods.find_one({"name": {"$regex": f"^{food_name}$", "$options": "i"}})
        
        if food:
            food["_id"] = str(food["_id"])
            return food
        
        # Try normalized match
        normalized_search = normalize_food_name(food_name)
        all_foods = await db.foods.find().to_list(length=100)
        
        for item in all_foods:
            normalized_item = normalize_food_name(item.get("name", ""))
            if normalized_item == normalized_search:
                item["_id"] = str(item["_id"])
                return item
        
        return None
    except Exception as e:
        logger.error(f"Error fetching food from database: {e}")
        return None

@router.post("/predict", response_model=PredictionResponse)
async def predict_food(file: UploadFile = File(...)):
    """
    Predict food from image using ML model.
    Only works for trained foods: asmi, egg_hoppers, kokis, kottu, pol_roti
    """
    try:
        img_bytes = await file.read()
        
        if len(img_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        content_type = file.content_type or ""
        if not is_valid_image(content_type, img_bytes):
            logger.warning(f"Invalid image: content_type={content_type}, size={len(img_bytes)}")
            raise HTTPException(
                status_code=400, 
                detail=f"File must be a valid image (JPEG, PNG, GIF, WebP). Received: {content_type}"
            )
        
        logger.info(f"Processing image: {file.filename}, type: {content_type}, size: {len(img_bytes)} bytes")
        
        # Check if ML model is available
        if not ML_AVAILABLE or model is None:
            raise HTTPException(
                status_code=503,
                detail="⚠️ ML model not available. Please install TensorFlow: pip install tensorflow==2.17.0"
            )
        
        # ML Prediction
        try:
            import numpy as np
            img_array = preprocess_image(img_bytes)
            predictions = model.predict(img_array, verbose=0)
            
            # Get prediction
            class_idx = int(np.argmax(predictions[0]))
            confidence = float(np.max(predictions[0]))
            food_label = TRAINED_FOODS[class_idx]
            
            logger.info(f"ML prediction: {food_label} ({confidence:.2%})")
            
            # Log all probabilities for debugging
            all_probs = {food: float(prob) for food, prob in zip(TRAINED_FOODS, predictions[0])}
            logger.info(f"All probabilities: {all_probs}")
            
            # Get food info from MongoDB database
            food_info = await get_food_info_from_db(food_label)
            
            if not food_info:
                # Fallback info
                food_info = {
                    "name": food_label.replace("_", " ").title(),
                    "category": "Sri Lankan",
                    "description": f"A traditional Sri Lankan dish - {food_label.replace('_', ' ')}",
                    "ingredients": ["Traditional Sri Lankan ingredients"],
                    "avg_rating": 4.5,
                    "rating_count": 0,
                    "image_url": None
                }
            
            # Generate confidence message
            if confidence < 0.5:
                message = "⚠️ Very low confidence. The image might not be one of the trained foods."
            elif confidence < 0.7:
                message = "⚠️ Low confidence prediction. Please try a clearer image."
            elif confidence < 0.85:
                message = "✓ Moderate confidence prediction."
            else:
                message = "✓ High confidence prediction!"

            return PredictionResponse(
                prediction=food_label,
                confidence=round(confidence, 3),
                food_info=food_info,
                ml_available=True,
                method="ml_model",
                message=message
            )
            
        except Exception as e:
            logger.error(f"ML prediction failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Prediction failed: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
    
@router.get("/predict/status")
async def prediction_status():
    """Check prediction service status"""
    try:
        from app.database import get_database
        db = await get_database()
        total_foods = await db.foods.count_documents({})
    except:
        total_foods = 0
    
    return {
        "ml_available": ML_AVAILABLE,
        "model_loaded": model is not None,
        "trained_foods": TRAINED_FOODS,
        "trained_count": len(TRAINED_FOODS),
        "total_foods_in_db": total_foods,
        "message": f"✅ ML model ready for {len(TRAINED_FOODS)} foods" if ML_AVAILABLE else "⚠️ ML model not available - Install TensorFlow",
        "installation_command": "pip install tensorflow==2.17.0 numpy==1.26.4",
        "note": "Model can ONLY predict: " + ", ".join([f.replace('_', ' ').title() for f in TRAINED_FOODS])
    }

@router.get("/predict/supported-foods")
async def get_supported_foods():
    """Get list of foods that can be predicted by the ML model"""
    foods_info = []
    
    for food in TRAINED_FOODS:
        food_data = await get_food_info_from_db(food)
        if food_data:
            foods_info.append(food_data)
        else:
            foods_info.append({
                "name": food.replace("_", " ").title(),
                "description": "No detailed information available"
            })
    
    return {
        "trained_foods": TRAINED_FOODS,
        "count": len(TRAINED_FOODS),
        "foods_with_info": foods_info,
        "note": "These are the only foods the ML model can predict accurately"
    }