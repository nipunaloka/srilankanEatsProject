import sys
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(current_dir))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Import database first
try:
    from app.database import connect_to_mongo, close_mongo_connection, is_connected
    logger.info("✅ Database module loaded")
except ImportError:
    logger.error("❌ Database import failed")
    async def connect_to_mongo():
        return False
    async def close_mongo_connection():
        pass
    def is_connected():
        return False

# Import routers
ROUTERS_LOADED = False
PREDICT_ROUTER_LOADED = False
import_errors = []
predict_router = None

try:
    from app.api.routes import auth, health, food, favorite, review
    logger.info("✅ Core routers loaded")
    ROUTERS_LOADED = True
except ImportError as e:
    logger.error(f"❌ Core routers failed: {e}")
    import_errors.append(str(e))

if ROUTERS_LOADED:
    try:
        from app.api.routes.predict_router import router as predict_router
        logger.info("✅ Predict router loaded")
        PREDICT_ROUTER_LOADED = True
    except ImportError as e:
        logger.warning(f"⚠️ Predict router disabled: {e}")
        import_errors.append(f"Predict: {e}")

# Create FastAPI app
app = FastAPI(
    title="Sri Lanka Eats API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# HTTPS Redirect Middleware (Azure specific)
@app.middleware("http")
async def https_redirect_middleware(request: Request, call_next):
    # Force HTTPS for Azure
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    
    # Log headers for debugging
    logger.info(f"Protocol: {forwarded_proto}, Host: {forwarded_host}")
    
    # Don't redirect OPTIONS (preflight) requests
    if request.method == "OPTIONS":
        response = await call_next(request)
        return response
    
    response = await call_next(request)
    return response

# CORS Configuration - MUST be after middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],
    max_age=3600,
)

@app.on_event("startup")
async def startup_db_client():
    try:
        result = await connect_to_mongo()
        if result:
            logger.info("✅ Database connected")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        await close_mongo_connection()
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")

# Register routers
if ROUTERS_LOADED:
    try:
        app.include_router(auth.router, prefix="/api")
        app.include_router(health.router, prefix="/api")
        app.include_router(food.router, prefix="/api")
        app.include_router(favorite.router, prefix="/api")
        app.include_router(review.router, prefix="/api")
        logger.info("✅ Core routers registered")
        
        if PREDICT_ROUTER_LOADED and predict_router:
            app.include_router(predict_router, prefix="/api")
            logger.info("✅ Predict router registered")
    except Exception as e:
        logger.error(f"❌ Router registration error: {e}")
        ROUTERS_LOADED = False

if not ROUTERS_LOADED:
    from fastapi import APIRouter
    test_router = APIRouter(prefix="/api/test", tags=["test"])
    
    @test_router.get("/")
    def test_endpoint():
        return {"message": "Fallback mode", "check": "/debug"}
    
    app.include_router(test_router)

@app.get("/")
def root():
    return {
        "message": "Sri Lanka Eats API 🚀",
        "status": "healthy",
        "routers_loaded": ROUTERS_LOADED,
        "predict_available": PREDICT_ROUTER_LOADED,
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected" if is_connected() else "disconnected",
        "routers_loaded": ROUTERS_LOADED,
    }

@app.get("/debug")
def debug_info():
    return {
        "routers_loaded": ROUTERS_LOADED,
        "predict_loaded": PREDICT_ROUTER_LOADED,
        "import_errors": import_errors,
        "cors_enabled": True,
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)