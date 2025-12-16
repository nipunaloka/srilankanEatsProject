from motor.motor_asyncio import AsyncIOMotorClient
from decouple import config
import logging
from fastapi import HTTPException, status

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
MONGO_URI = config("MONGO_URI")
DB_NAME = config("DB_NAME")

# Connection state
is_connected = False

# Create database client placeholder
client = None
db = None

async def connect_to_mongo():
    """Connect to MongoDB database"""
    global client, db, is_connected
    
    try:
        logger.info(f"Connecting to MongoDB database: {DB_NAME}")
        client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        
        # Test connection with ping
        await client.admin.command('ping')
        logger.info("MongoDB connection successful!")
        is_connected = True
        return True
    except Exception as e:
        logger.error(f"MongoDB connection failed with primary URI: {e}")
        
        try:
            # Try alternative connection string
            alternate_uri = MONGO_URI.replace("mongodb+srv://", "mongodb://")
            logger.info("Trying alternate connection string...")
            client = AsyncIOMotorClient(alternate_uri, serverSelectionTimeoutMS=5000)
            db = client[DB_NAME]
            
            # Test the alternate connection
            await client.admin.command('ping')
            logger.info("MongoDB connection successful with alternate URI!")
            is_connected = True
            return True
        except Exception as e:
            logger.error(f"MongoDB connection failed with alternate URI: {e}")
            db = None
            client = None
            is_connected = False
            return False

async def close_mongo_connection():
    """Close MongoDB connection"""
    global client, is_connected
    if client:
        client.close()
        is_connected = False
        logger.info("MongoDB connection closed")

# Database dependency to check DB connection in routes
async def get_db():
    if not is_connected or db is None:
        # Try reconnecting
        await connect_to_mongo()
        if not is_connected or db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection is not available"
            )
    return db