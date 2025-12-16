import os
import numpy as np
from tensorflow.keras.models import load_model, Sequential
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.applications import MobileNetV2
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the absolute path to the model file
base_dir = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(base_dir, "model", "SriLankanFoods_MobileNetV2_New.h5")

def create_model_with_original_architecture():
    """
    Create a model with the exact same architecture as the original training code.
    This matches the architecture from your training notebook.
    """
    logger.info("Creating model with original architecture...")
    
    # Create the base model - exactly as in your training code
    base_model = MobileNetV2(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
    base_model.trainable = False  # freeze base layers
    
    # Create the model with the same architecture as your training code
    model = Sequential([
        base_model,
        GlobalAveragePooling2D(),
        Dropout(0.3),
        Dense(128, activation='relu'),
        Dropout(0.3),
        Dense(5, activation='softmax')  # 5 classes: asmi, egg_hoppers, kokis, kottu, pol_roti
    ])
    
    logger.info("Original architecture model created successfully")
    return model

def get_model():
    """
    Load the trained Keras model for inference.
    If loading fails, create a model with the original architecture.
    """
    try:
        logger.info(f"Attempting to load model from {MODEL_PATH}")
        
        # Try loading with compile=False
        model = load_model(MODEL_PATH, compile=False)
        logger.info("Model loaded successfully!")
        return model
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        logger.warning("Creating a model with the original architecture for inference")
        
        # Create model with original architecture
        model = create_model_with_original_architecture()
        
        # Try to load weights if model exists
        try:
            if os.path.exists(MODEL_PATH):
                logger.info("Attempting to load weights into the new model...")
                model.load_weights(MODEL_PATH)
                logger.info("Model weights loaded successfully!")
            else:
                logger.warning(f"Model file {MODEL_PATH} not found. Using default ImageNet weights.")
        except Exception as weight_error:
            logger.error(f"Failed to load weights: {weight_error}")
            logger.warning("Using model with ImageNet weights only.")
        
        return model